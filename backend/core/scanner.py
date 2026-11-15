"""
Library scanner — walks the music directory and keeps the SQLite DB in sync.

Strategy:
  - Collect all audio file paths upfront (enables progress reporting).
  - Compare each file's mtime against the DB; skip unchanged files.
  - Upsert changed/new tracks; delete DB rows for missing files.
  - Commits in batches to balance memory vs. write frequency.
"""
from __future__ import annotations

import fnmatch
import os
import sqlite3
import time
from pathlib import Path
from typing import Callable

from core.config import settings
from core.database import get_conn
from core import covers
from core.tagger import read_tags, is_audio_file, TAG_FIELDS, MB_FIELDS, RG_FIELDS

_BATCH_SIZE = 200


def _under(path: str, roots: list[str]) -> bool:
    norm = os.path.normpath(path)
    for r in roots:
        r = os.path.normpath(r)
        if norm == r or norm.startswith(r + os.sep):
            return True
    return False


def _excluded(path: str, patterns: list[str]) -> bool:
    """True if the path (or its basename) matches any exclude glob."""
    base = os.path.basename(path)
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(base, p) for p in patterns)


# Bump when read_tags() reads existing files differently, so the next full
# scan re-reads every file instead of skipping unchanged ones.
#   1: multi-value tags keep every value ("; "-joined), not just the first.
#   2: embedded cover art: has_cover, its size in px and bytes.
#   3: MusicBrainz IDs (they were written, never read back).
READER_VERSION = 3


_UPSERT = """
                        INSERT INTO tracks (
                            path, filename, directory, format, size, mtime, duration,
                            bitrate, sample_rate, channels,
                            title, artist, album, album_artist, year, genre,
                            track_number, disc_number, comment, composer, bpm,
                            lyrics, compilation, has_cover, cover_width, cover_height, cover_bytes,
                            mb_track_id, mb_artist_id, mb_album_id, mb_album_artist_id,
                            mb_release_group_id, mb_release_track_id,
                            rg_track_gain, rg_track_peak, rg_album_gain, rg_album_peak, scanned_at
                        ) VALUES (
                            :path, :filename, :directory, :format, :size, :mtime, :duration,
                            :bitrate, :sample_rate, :channels,
                            :title, :artist, :album, :album_artist, :year, :genre,
                            :track_number, :disc_number, :comment, :composer, :bpm,
                            :lyrics, :compilation, :has_cover, :cover_width, :cover_height, :cover_bytes,
                            :mb_track_id, :mb_artist_id, :mb_album_id, :mb_album_artist_id,
                            :mb_release_group_id, :mb_release_track_id,
                            :rg_track_gain, :rg_track_peak, :rg_album_gain, :rg_album_peak, :scanned_at
                        )
                        ON CONFLICT(path) DO UPDATE SET
                            filename     = excluded.filename,
                            directory    = excluded.directory,
                            format       = excluded.format,
                            size         = excluded.size,
                            mtime        = excluded.mtime,
                            duration     = excluded.duration,
                            bitrate      = excluded.bitrate,
                            sample_rate  = excluded.sample_rate,
                            channels     = excluded.channels,
                            title        = excluded.title,
                            artist       = excluded.artist,
                            album        = excluded.album,
                            album_artist = excluded.album_artist,
                            year         = excluded.year,
                            genre        = excluded.genre,
                            track_number = excluded.track_number,
                            disc_number  = excluded.disc_number,
                            comment      = excluded.comment,
                            composer     = excluded.composer,
                            bpm          = excluded.bpm,
                            lyrics       = excluded.lyrics,
                            compilation  = excluded.compilation,
                            has_cover    = excluded.has_cover,
                            cover_width  = excluded.cover_width,
                            cover_height = excluded.cover_height,
                            cover_bytes  = excluded.cover_bytes,
                            mb_track_id  = excluded.mb_track_id,
                            mb_artist_id = excluded.mb_artist_id,
                            mb_album_id  = excluded.mb_album_id,
                            mb_album_artist_id  = excluded.mb_album_artist_id,
                            mb_release_group_id = excluded.mb_release_group_id,
                            mb_release_track_id = excluded.mb_release_track_id,
                            rg_track_gain = excluded.rg_track_gain,
                            rg_track_peak = excluded.rg_track_peak,
                            rg_album_gain = excluded.rg_album_gain,
                            rg_album_peak = excluded.rg_album_peak,
                            scanned_at   = excluded.scanned_at
"""


class ScanCancelled(Exception):
    """Raised when should_stop() turns true. Files read so far are kept; nothing is pruned."""


def scan_library(
    progress_cb: Callable[[int, int], None] | None = None,
    scan_tags: list[str] | None = None,
    music_dirs: list[str] | None = None,
    prune_under: list[str] | None = None,
    exclude: list[str] | None = None,
    should_stop: Callable[[], bool] | None = None,
    phase_cb: Callable[[str], None] | None = None,
) -> tuple[int, int]:
    """
    Scan the music directories and upsert changed/new tracks into the DB.

    `prune_under` scopes deletion of vanished files: when set, only DB rows
    under those roots are removed for missing files (used by a targeted rescan
    so it doesn't wipe tracks outside the scanned folder). When None, every
    missing file is pruned (a full-library scan).

    Returns (total_found, upserted).
    """
    if music_dirs is None:
        music_dirs = [str(settings.music_dir)]

    patterns = exclude or []

    stop = should_stop or (lambda: False)
    if phase_cb:
        phase_cb("listing")

    # Collect all audio files first so we know the total
    all_files: list[str] = []
    folder_art: dict[str, str | None] = {}   # album folder -> its cover image's name
    for music_dir in music_dirs:
        if not os.path.isdir(music_dir):
            continue
        for root, dirs, files in os.walk(music_dir):
            # Prune excluded directories so we don't descend into them.
            dirs[:] = [d for d in dirs if not _excluded(os.path.join(root, d), patterns)]
            if stop():
                raise ScanCancelled()
            if any(is_audio_file(f) for f in files):
                folder_art[root] = covers.folder_image(files)
            for fname in sorted(files):
                fpath = os.path.join(root, fname)
                if is_audio_file(fpath) and not _excluded(fpath, patterns):
                    all_files.append(fpath)
                    if progress_cb and len(all_files) % 500 == 0:
                        progress_cb(0, len(all_files))   # still listing: a running count

    total = len(all_files)
    upserted = 0
    if phase_cb:
        phase_cb("reading")
    now = time.time()

    conn = get_conn()
    try:
        # Load existing mtimes for fast change detection
        existing: dict[str, float] = {
            row[0]: row[1]
            for row in conn.execute("SELECT path, mtime FROM tracks")
        }
        # A newer tag reader re-reads every file once, even unchanged ones.
        # (`existing` must stay intact: pruning vanished files below walks it.
        # Emptying it here made the 2026-11-02 re-read scan prune nothing.)
        reread = conn.execute("PRAGMA user_version").fetchone()[0] < READER_VERSION
        pending: list[dict] = []
        last_flush = time.monotonic()

        def flush() -> None:
            """Write the queued rows in one short transaction."""
            nonlocal last_flush
            if pending:
                try:
                    conn.executemany(_UPSERT, pending)
                except sqlite3.Error:
                    conn.rollback()
                    for row in pending:              # one bad row mustn't drop the batch
                        try:
                            conn.execute(_UPSERT, row)
                        except sqlite3.Error:
                            pass
                conn.commit()
                pending.clear()
            last_flush = time.monotonic()

        for i, fpath in enumerate(all_files):
            if stop():
                flush()                 # keep what was read; skip pruning
                raise ScanCancelled()
            try:
                stat = os.stat(fpath)
                mtime = stat.st_mtime

                if reread or existing.get(fpath) != mtime:
                    want_extended = scan_tags is None or "lyrics" in scan_tags or "compilation" in scan_tags
                    tags = read_tags(fpath, extended=want_extended)
                    if scan_tags is not None:
                        for tag in TAG_FIELDS:
                            if tag not in scan_tags:
                                tags.pop(tag, None)
                    p = Path(fpath)
                    # Queued, not written: a write here would hold the database lock while
                    # the next files are read (seconds on a NAS), and edits staged meanwhile
                    # failed with "database is locked". flush() writes the batch at once.
                    pending.append({
                            "path": fpath,
                            "filename": p.name,
                            "directory": str(p.parent),
                            "format": tags.get("format", "unknown"),
                            "size": stat.st_size,
                            "mtime": mtime,
                            "duration": tags.get("duration"),
                            "bitrate": tags.get("bitrate"),
                            "sample_rate": tags.get("sample_rate"),
                            "channels": tags.get("channels"),
                            "title": tags.get("title"),
                            "artist": tags.get("artist"),
                            "album": tags.get("album"),
                            "album_artist": tags.get("album_artist"),
                            "year": tags.get("year"),
                            "genre": tags.get("genre"),
                            "track_number": tags.get("track_number"),
                            "disc_number": tags.get("disc_number"),
                            "comment": tags.get("comment"),
                            "composer": tags.get("composer"),
                            "bpm": tags.get("bpm"),
                            "lyrics": tags.get("lyrics"),
                            "compilation": tags.get("compilation"),
                            "has_cover": tags.get("has_cover"),
                            "cover_width": tags.get("cover_width"),
                            "cover_height": tags.get("cover_height"),
                            "cover_bytes": tags.get("cover_bytes"),
                            **{f: tags.get(f) for f in MB_FIELDS},
                            **{f: tags.get(f) or "" for f in RG_FIELDS},   # "" = read, none (NULL = never read)
                            "scanned_at": now,
                        })
                    upserted += 1

            except Exception:
                pass  # skip unreadable / permission-denied files

            # Write in batches (or every second, so a slow read doesn't sit on
            # unsaved rows) and report progress.
            if len(pending) >= _BATCH_SIZE or time.monotonic() - last_flush > 1.0:
                flush()
            if progress_cb and (i + 1) % _BATCH_SIZE == 0:
                progress_cb(i + 1, total)
        flush()

        for d, name in folder_art.items():
            covers.record_folder(conn, d, name)
        conn.commit()
        if reread and prune_under is None:  # only a full scan covers every file
            conn.execute(f"PRAGMA user_version = {READER_VERSION}")
            conn.commit()

        if phase_cb:
            phase_cb("pruning")
        # Remove DB rows for files that no longer exist on disk. A targeted
        # rescan only prunes within the scanned roots.
        scanned = set(all_files)
        for db_path in list(existing):
            if db_path in scanned:
                continue
            if prune_under is not None and not _under(db_path, prune_under):
                continue
            conn.execute("DELETE FROM tracks WHERE path = ?", (db_path,))
        conn.commit()

    finally:
        conn.close()

    if progress_cb:
        progress_cb(total, total)

    return total, upserted
