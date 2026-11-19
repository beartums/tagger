"""
Clean up → Convert audio: files tggr can't read, turned into ones it can.
WAV/AIFF -> FLAC (lossless to lossless: nothing lost), WMA/MP2/MPA -> MP3 V0
(lossy to lossy: a little lost). Protected iTunes .m4p can't be converted --
it would mean removing the protection; they're listed with a note to download
them again (Apple offers DRM-free .m4a for most old purchases).

Each file: ffmpeg into a temp name beside it (tags carried over), checked
(ffprobe: audio, same length within a second), renamed into place, original
to the trash, folder rescanned. Logged as one "convert" change: undo removes
the new files and puts the originals back.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from core.config import settings
from core.database import db
from core.tasks import _CANCEL, _update_job

logger = logging.getLogger("tggr.convert")

TARGET = {".wav": ".flac", ".wave": ".flac", ".aif": ".flac", ".aiff": ".flac", ".aifc": ".flac",
          ".wma": ".mp3", ".mp2": ".mp3", ".mpa": ".mp3"}
PROTECTED = {".m4p"}
# Broadcast-WAV recording metadata (Pro Tools etc.): not music tags, so not carried over.
DROP = ["umid", "originator_reference", "originator", "time_reference", "coding_history", "creation_time",
        "origination_date", "origination_time", "encoded_by", "encoder"]
CODEC = {".flac": ["-c:a", "flac", "-compression_level", "5"],
         ".mp3": ["-c:a", "libmp3lame", "-q:a", "0", "-id3v2_version", "3"]}


def find(roots: list[str]) -> list[dict]:
    """Folders under roots with files to convert (or protected ones), per file."""
    out = []
    for root in roots:
        for d, _, names in os.walk(root):
            files = []
            for n in sorted(names):
                ext = os.path.splitext(n)[1].lower()
                if ext in TARGET or ext in PROTECTED:
                    p = os.path.join(d, n)
                    to = os.path.splitext(n)[0] + TARGET[ext] if ext in TARGET else None
                    taken = bool(to) and os.path.exists(os.path.join(d, to))
                    files.append({"path": p, "name": n, "ext": ext, "to": to,
                                  "size": _size(p), "protected": ext in PROTECTED, "taken": taken})
            if files:
                out.append({"dir": d, "root": root, "files": files})
    return sorted(out, key=lambda f: f["dir"])


def _size(p: str) -> int:
    try:
        return os.path.getsize(p)
    except OSError:
        return 0


def _duration(p: str) -> float | None:
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                            "format=duration", "-of", "json", p], capture_output=True, text=True, timeout=60)
        return float(json.loads(r.stdout)["format"]["duration"])
    except (subprocess.TimeoutExpired, ValueError, KeyError, OSError, TypeError):
        return None


class ConvertError(Exception):
    pass


def convert_one(src: str) -> tuple[str, str]:
    """Convert src beside itself; original to the trash. Returns (new path, trash path)."""
    s = Path(src)
    ext = s.suffix.lower()
    if ext in PROTECTED:
        raise ConvertError("protected iTunes file: download it again from your purchases")
    if ext not in TARGET:
        raise ConvertError("not a format tggr converts")
    out = s.with_suffix(TARGET[ext])
    if out.exists():
        raise ConvertError(f"{out.name} already exists")
    before = _duration(src)
    if before is None:
        raise ConvertError("ffprobe can't read it")
    tmp = s.with_name(f".tggr-{uuid.uuid4().hex}{out.suffix}")
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", src,
           "-map", "0:a:0", "-map_metadata", "0",
           *[x for k in DROP for x in ("-metadata", f"{k}=")], *CODEC[out.suffix], str(tmp)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            raise ConvertError(f"ffmpeg: {(r.stderr or '').strip().splitlines()[-1:] or ['failed']}")
        after = _duration(str(tmp))
        if after is None or abs(after - before) > 1.0:
            raise ConvertError(f"the result is {after or 0:.1f}s, the original {before:.1f}s")
        os.rename(tmp, out)
    finally:
        if tmp.exists():
            tmp.unlink()
    trash = settings.config_dir / "trash"
    trash.mkdir(parents=True, exist_ok=True)
    to_trash = trash / f"converted_{uuid.uuid4().hex[:8]}_{s.name}"
    try:
        shutil.move(src, str(to_trash))
    except OSError as exc:
        out.unlink(missing_ok=True)
        raise ConvertError(f"couldn't move the original to the trash: {exc}")
    return str(out), str(to_trash)


async def run(job_id: str, paths: list[str]) -> None:
    from api.config import _load as load_app_settings
    from core.history import log_change
    from core.scanner import scan_library

    _update_job(job_id, status="running", phase="converting", total=len(paths), scanned=0, changed=0)
    done, made, errors = 0, [], []
    try:
        for p in paths:
            if job_id in _CANCEL:
                break
            try:
                new, trashed = await asyncio.to_thread(convert_one, p)
                made.append({"src": p, "dst": trashed, "made": new})
            except ConvertError as exc:
                errors.append({"name": os.path.basename(p), "error": str(exc)})
                logger.warning("convert %s: %s", p, exc)
            done += 1
            _update_job(job_id, scanned=done, changed=len(made))
        if made:
            app = load_app_settings()
            folders = sorted({os.path.dirname(m["made"]) for m in made})
            await asyncio.to_thread(scan_library, None, app.scan_tags, folders, folders, app.scan_exclude)
            with db() as conn:
                n = len(made)
                log_change(conn, "convert", f"Converted {n} file{'s' if n != 1 else ''} (originals in the trash)",
                           [], files=made)
        status = "cancelled" if job_id in _CANCEL else "done"
        _update_job(job_id, status=status, phase=None, finished_at=time.time(), scanned=done, changed=len(made),
                    error=(f"{len(errors)} not converted: {errors[0]['name']}: {errors[0]['error']}" if errors else None))
        logger.info("convert %s %s: %d of %d", job_id, status, len(made), len(paths))
    except Exception as exc:
        _update_job(job_id, status="error", phase=None, finished_at=time.time(), error=str(exc))
        logger.exception("convert %s failed: %s", job_id, exc)
    finally:
        _CANCEL.discard(job_id)


def undo(files: list[dict], errors: list[dict]) -> int:
    """Remove each converted file and put its original back; rescan those folders."""
    from api.config import _load as load_app_settings
    from core.scanner import scan_library
    back = 0
    for f in files:
        src, made = Path(f["src"]), Path(f["made"])
        if src.exists():
            errors.append({"name": src.name, "error": "the original is already back"})
            continue
        if not Path(f["dst"]).exists():
            errors.append({"name": src.name, "error": "no copy of the original left in the trash"})
            continue
        shutil.move(f["dst"], str(src))
        made.unlink(missing_ok=True)
        back += 1
    if back:
        app = load_app_settings()
        folders = sorted({str(Path(f["made"]).parent) for f in files})
        scan_library(None, app.scan_tags, folders, folders, app.scan_exclude)
    return back


def available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
