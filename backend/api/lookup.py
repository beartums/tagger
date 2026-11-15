from __future__ import annotations

import asyncio
import dataclasses
import re
import shutil
import urllib.error
import urllib.request

from fastapi import APIRouter, HTTPException

from core.config import settings
from core.database import db
from core.inference import infer_tags_from_path
from core.providers.musicbrainz import MusicBrainzProvider
from core.tagger import write_cover
from api.config import _load as load_app_settings, get_music_dirs


def _acoustid_key() -> str:
    """AppSettings key takes precedence over env var."""
    app_key = load_app_settings().acoustid_api_key
    return app_key or settings.acoustid_api_key

router = APIRouter()
_mb = MusicBrainzProvider()


@router.get("/status")
def lookup_status():
    """Report which lookup methods are available."""
    acoustid_key = _acoustid_key()
    fpcalc_available = bool(acoustid_key) and shutil.which("fpcalc") is not None
    return {
        "fpcalc_installed": shutil.which("fpcalc") is not None,
        "acoustid_configured": bool(acoustid_key),
        "fpcalc_available": fpcalc_available,
        "method": "acoustid" if (acoustid_key and fpcalc_available) else "text",
    }


def _real(v: str | None) -> str | None:
    """A tag value, unless it's a ripper's placeholder ("Unknown Album")."""
    return None if albummatch.is_placeholder(v) else v


@router.post("/search/{track_id}")
async def search_track(track_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Track not found")

    acoustid_key = _acoustid_key()
    if acoustid_key:
        if not shutil.which("fpcalc"):
            raise HTTPException(400, "fpcalc not found — install libchromaprint-tools to use AcoustID")
        try:
            from core.providers.acoustid_provider import AcoustIDProvider
            results = await AcoustIDProvider(acoustid_key).lookup(row["path"], _real(row["album"]))
            if results:
                return [
                    {k: v for k, v in dataclasses.asdict(r).items() if k != "raw"}
                    for r in results
                ]
        except RuntimeError as e:
            if "fpcalc" in str(e):
                raise HTTPException(400, str(e))
            # Fingerprint failed for this file — fall back to text search

    # Text search with duration for better accuracy
    results = await _mb.search(
        title=row["title"],
        artist=row["artist"],
        album=_real(row["album"]),
        duration=row["duration"],
    )

    # Supplement with Discogs when a token is configured
    discogs_token = load_app_settings().discogs_token
    if discogs_token:
        try:
            from core.providers.discogs import DiscogsProvider
            results += await DiscogsProvider(discogs_token).search(
                title=row["title"], artist=row["artist"], album=row["album"]
            )
        except Exception:
            pass  # Discogs is best-effort; never fail the whole lookup

    results.sort(key=lambda r: r.score, reverse=True)
    return [
        {k: v for k, v in dataclasses.asdict(r).items() if k != "raw"}
        for r in results
    ]


@router.get("/release-tags/{mb_album_id}")
async def release_tags(mb_album_id: str, mb_track_id: str = ""):
    """
    What a per-track match's release gives beyond the track search: its credited
    album artist, its genres and the track's composer (Auto-fix). The release is
    cached, so an album's tracks cost one MusicBrainz request.
    """
    rel = await asyncio.to_thread(_release, mb_album_id)
    await asyncio.to_thread(mbp.release_genre, rel)
    track = next((t for t in rel["tracks"] if mb_track_id and t["mb_track_id"] == mb_track_id), None)
    album = albummatch.album_tags(rel)        # album, album artist, (original) year, genre, release ids
    if track:
        album |= {"track_number": str(track["position"]), "disc_number": str(track["disc"]),
                  "composer": track["composer"], "mb_release_track_id": track.get("mb_release_track_id")}
    keys = ("album", "album_artist", "mb_album_artist_id", "mb_release_group_id", "year", "genre", "composer",
            "track_number", "disc_number", "mb_release_track_id")
    return {k: album.get(k) for k in keys}


@router.get("/releases/{mb_track_id}")
async def list_releases(mb_track_id: str):
    """List the releases/editions a recording appears on (for the edition picker)."""
    return await _mb.list_releases(mb_track_id)


@router.post("/infer/{track_id}")
def infer_from_path(track_id: int):
    """Propose tags parsed from the file's path/name (source='filename')."""
    with db() as conn:
        row = conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Track not found")
    inferred = infer_tags_from_path(row["path"], get_music_dirs())
    if not inferred:
        return None
    return {
        "title":        inferred.get("title"),
        "artist":       inferred.get("artist"),
        "album":        inferred.get("album"),
        "album_artist": inferred.get("album_artist"),
        "year":         inferred.get("year"),
        "track_number": inferred.get("track_number"),
        "disc_number":  inferred.get("disc_number"),
        "mb_track_id":  None,
        "mb_artist_id": None,
        "mb_album_id":  None,
        "mb_album_artist_id": None,
        "score":        0.5,
        "source":       "filename",
    }


_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_MAX_COVER_BYTES = 20 * 1024 * 1024  # 20 MB


def _fetch_caa(mb_album_id: str, size: int = 1200) -> tuple[str, bytes]:
    """
    Fetch the front cover from the Cover Art Archive. Raises on failure.
    A sized JPEG (250/500/1200) first -- originals can be 8 MB PNGs; 0 = the original.
    """
    if size:
        try:
            return _fetch_caa_url(f"https://coverartarchive.org/release/{mb_album_id}/front-{size}")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    return _fetch_caa_url(f"https://coverartarchive.org/release/{mb_album_id}/front")


def _caa_size(size: int) -> int:
    """The smallest Cover Art Archive size (250/500/1200) at least `size`; 0 = the original."""
    return next((c for c in (250, 500, 1200) if size and size <= c), 0)


def _fetch_caa_url(url: str) -> tuple[str, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "tggr/0.3.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        data = resp.read(_MAX_COVER_BYTES + 1)
    if len(data) > _MAX_COVER_BYTES:
        raise ValueError("cover art exceeds 20 MB")
    if not mime.startswith("image/"):
        raise ValueError(f"unexpected content type: {mime}")
    return mime, data


@router.post("/cover/{track_id}")
async def apply_cover_from_mb(track_id: int, mb_album_id: str):
    """Fetch cover art from Cover Art Archive and write it to the audio file."""
    # mb_album_id is interpolated into the outbound URL — require a real UUID.
    if not _UUID_RE.match(mb_album_id):
        raise HTTPException(400, "Invalid MusicBrainz album id")
    with db() as conn:
        row = conn.execute("SELECT path FROM tracks WHERE id = ?", (track_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Track not found")
    try:
        mime, data = await asyncio.to_thread(_fetch_caa, mb_album_id)
    except urllib.error.HTTPError as e:
        raise HTTPException(e.code, f"Cover Art Archive returned {e.code}")
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch cover art: {e}")
    try:
        write_cover(row["path"], mime, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


# ── Album-level match (core/albummatch.py) ────────────────────────────────────

from typing import Optional

from pydantic import BaseModel

from difflib import SequenceMatcher

from core import albummatch, covers, staging
from core.providers import musicbrainz as mbp


class AlbumSearch(BaseModel):
    track_ids: list[int]
    album: Optional[str] = None      # override the selection's own values
    artist: Optional[str] = None
    by: str = "album"                # album | artist (releases by the artist) | track (releases containing it)
    track: Optional[str] = None      # title for by="track"
    source: str = "auto"             # auto (tags; Unknown/missing -> folder names) | names | tags
    release: Optional[str] = None    # a release to put first (one just added to MusicBrainz)


async def _pinned(req: "AlbumSearch", tracks: list[dict]) -> list[dict]:
    """
    Candidates that come before any search: the release just added (req.release),
    then the releases MusicBrainz has the rip's disc ID on -- an exact match.
    """
    out: list[dict] = []
    if req.release and _UUID_RE.match(req.release):
        rel = await asyncio.to_thread(mbp.get_release, req.release)
        if rel:
            out.append({"mb_album_id": req.release, "album": rel["album"], "artist": rel["album_artist"],
                        "date": rel["date"], "country": rel["country"], "formats": [], "discs": rel["discs"],
                        "tracks": len(rel["tracks"]), "type": None, "score": 1.0, "added": True})
    disc = _common(tracks, "mb_disc_id")
    if disc:
        for c in await asyncio.to_thread(mbp.releases_by_discid, disc):
            if all(c["mb_album_id"] != o["mb_album_id"] for o in out):
                out.append({**c, "by_disc_id": True})
    return out


def _selection(conn, ids: list[int]) -> list[dict]:
    """The selected tracks as staged (what a match should compare against)."""
    from api.tags import _rows
    rows = _rows(conn, ids)
    entries = staging.load(conn, [r["id"] for r in rows])
    return [staging.effective(r, entries.get(r["id"])) for r in rows]


def _common(tracks: list[dict], field: str) -> str | None:
    vals = [t.get(field) for t in tracks if not albummatch.is_placeholder(t.get(field))]
    return max(set(vals), key=vals.count) if vals else None


def _from_names(tracks: list[dict]) -> list[dict]:
    """The selection as its folder and file names say: album, artist, title (other fields kept)."""
    from api.config import get_library_roots
    from core.fileops import root_for
    roots = get_library_roots()
    out = []
    for t in tracks:
        album, artist = albummatch.names_from_path(t["path"], root_for(t["path"], roots))
        out.append({**t, "album": album, "album_artist": artist, "artist": artist,
                    "title": albummatch.name_title(t)})
    return out


def _artist_releases(artist: str, tracks: list[dict]) -> list[dict]:
    """
    "Which of this artist's releases holds these tracks?" A bare artist search
    returns whatever MusicBrainz scores highest (often obscure uploads), so
    instead look up releases by the artist containing each of your titles
    (up to 6) and order them by how many of your titles each holds.
    """
    titles = list(dict.fromkeys(albummatch.local_title(t) for t in tracks if albummatch.local_title(t)))[:6]
    if not titles:
        return mbp.search_releases(None, artist, 40)
    hits: dict[str, int] = {}
    cands: dict[str, dict] = {}
    want = albummatch._norm(artist)
    for title in titles:
        for c in mbp.releases_with_recording(title, artist):
            # MusicBrainz's artist filter is fuzzy: drop covers / other artists.
            got = albummatch._norm(c.get("artist"))
            if got and want not in got and SequenceMatcher(None, want, got).ratio() < 0.6:
                continue
            hits[c["mb_album_id"]] = hits.get(c["mb_album_id"], 0) + 1
            cands.setdefault(c["mb_album_id"], c)
    ranked = sorted(cands.values(), key=lambda c: (-hits[c["mb_album_id"]], c.get("type") != "Album",
                                                   abs((c.get("tracks") or 999) - len(tracks))))
    for c in ranked:
        c["titles_found"] = hits[c["mb_album_id"]]
    return ranked[:40]


@router.post("/album/search")
async def album_search(req: AlbumSearch):
    """Release candidates for the selection; one its files already name comes first."""
    with db() as conn:
        tracks = _selection(conn, req.track_ids)
    if not tracks:
        raise HTTPException(400, "No tracks")
    names = _from_names(tracks)
    if req.source == "names":
        tracks = names
    fallback = req.source == "auto"
    album = req.album if req.album is not None else (
        _common(tracks, "album") or (_common(names, "album") if fallback else None))
    artist = req.artist if req.artist is not None else (
        _common(tracks, "album_artist") or _common(tracks, "artist") or (_common(names, "artist") if fallback else None))
    if req.by == "track":
        title = (req.track or "").strip()
        if not title:
            raise HTTPException(400, "No track title to search for")
        found = await asyncio.to_thread(mbp.releases_with_recording, title, artist)
        return {"album": album, "artist": artist, "track": title, "by": "track", "source": req.source,
                "local_tracks": len(tracks), "candidates": found}
    if req.by == "artist":
        if not artist:
            raise HTTPException(400, "No artist to search for -- type one")
        found = await asyncio.to_thread(_artist_releases, artist, tracks)
        return {"album": album, "artist": artist, "by": "artist", "source": req.source, "local_tracks": len(tracks), "candidates": found}
    pinned = await _pinned(req, tracks)
    if not album and pinned:
        return {"album": album, "artist": artist, "by": "album", "source": req.source,
                "local_tracks": len(tracks), "candidates": pinned}
    if not album:
        raise HTTPException(400, "No album name to search for -- type one, or try " +
                            ("tags" if req.source == "names" else "folder names" if req.source == "tags" else "naming the folder"))
    found = await asyncio.to_thread(mbp.search_releases, album, artist)
    tagged = _common(tracks, "mb_album_id")
    if tagged and _UUID_RE.match(tagged):
        found = [r for r in found if r["mb_album_id"] != tagged]
        rel = await asyncio.to_thread(mbp.get_release, tagged)
        if rel:
            found.insert(0, {"mb_album_id": tagged, "album": rel["album"], "artist": rel["album_artist"],
                             "date": rel["date"], "country": rel["country"], "formats": [],
                             "discs": rel["discs"], "tracks": len(rel["tracks"]), "type": None,
                             "score": 1.0, "tagged": True})
    ids = {c["mb_album_id"] for c in pinned}
    found = pinned + [c for c in found if c["mb_album_id"] not in ids]
    return {"album": album, "artist": artist, "by": "album", "source": req.source, "local_tracks": len(tracks), "candidates": found}


class AlbumMatch(BaseModel):
    track_ids: list[int]
    mb_album_id: str


def _release(mb_album_id: str) -> dict:
    if not _UUID_RE.match(mb_album_id):
        raise HTTPException(400, "Invalid MusicBrainz album id")
    rel = mbp.get_release(mb_album_id)
    if not rel:
        raise HTTPException(502, "MusicBrainz didn't return that release")
    return rel


@router.post("/album/match")
async def album_match(req: AlbumMatch):
    """Proposed pairing of the selection with one release, with each pair's tag changes."""
    rel = await asyncio.to_thread(_release, req.mb_album_id)
    await asyncio.to_thread(mbp.release_genre, rel)
    with db() as conn:
        tracks = _selection(conn, req.track_ids)
    pairs = albummatch.match(tracks, rel["tracks"])
    items = []
    for t in sorted(tracks, key=lambda t: (albummatch._int(t.get("disc_number")) or 1,
                                           albummatch._int(t.get("track_number")), t["filename"])):
        key, sc = pairs[t["id"]]
        mb = next((r for r in rel["tracks"] if r["key"] == key), None)
        items.append({"id": t["id"], "filename": t["filename"], "title": t.get("title"),
                      "title_similarity": round(albummatch.title_similarity(t, mb), 3) if mb else None,
                      "artist": t.get("artist"), "track_number": t.get("track_number"),
                      "genre": t.get("genre"), "composer": t.get("composer"),
                      "disc_number": t.get("disc_number"), "duration": t.get("duration"),
                      "key": key, "score": sc})
    used = {i["key"] for i in items if i["key"]}
    release = {k: v for k, v in rel.items() if k not in ("tracks", "tag_list")}
    current = {f: _common(tracks, f) for f in ("album", "album_artist", "year", "genre")}
    return {"release": release, "release_tracks": rel["tracks"], "items": items, "current": current,
            "unmatched": [t["key"] for t in rel["tracks"] if t["key"] not in used]}


@router.post("/album/score")
async def album_score(req: AlbumMatch):
    """One candidate's fit to the selection -- the dialog ranks candidates by this."""
    rel = await asyncio.to_thread(_release, req.mb_album_id)
    with db() as conn:
        tracks = _selection(conn, req.track_ids)
    q = albummatch.quality(tracks, rel["tracks"])
    return {"mb_album_id": req.mb_album_id, **{k: v for k, v in q.items() if k != "pairs"}}


class AlbumApply(BaseModel):
    mb_album_id: str
    pairs: dict[int, str]                    # track id -> release track key
    fields: list[str] = list(albummatch.FIELDS)
    original_year: bool = True
    cover: bool = False
    keep: list[str] = []                     # fields only filled where empty (genre, composer)
    unpaired: list[int] = []                 # tracks on no release track: album-level fields only
    genre: Optional[str] = None              # the genres to write instead of the release's (some left out)


@router.post("/album/apply")
async def album_apply(req: AlbumApply):
    """Stage the chosen pairs' tags as one step; cover art (optional) is written now."""
    from api.tags import _finish, _rows
    rel = await asyncio.to_thread(_release, req.mb_album_id)
    if "genre" in req.fields:
        await asyncio.to_thread(mbp.release_genre, rel)
    by_key = {t["key"]: t for t in rel["tracks"]}
    fields = [f for f in req.fields if f in albummatch.FIELDS]
    if not fields and not req.cover:
        raise HTTPException(400, "Nothing chosen: pick tags or cover art")
    errors: list[dict] = []
    targets = {**{tid: by_key.get(key) for tid, key in req.pairs.items()}, **{tid: None for tid in req.unpaired}}
    with db() as conn:
        rows = {r["id"]: r for r in _rows(conn, list(targets))}
        entries = staging.load(conn, list(rows))
        todo = []
        for tid, mb in targets.items():
            row = rows.get(tid)
            if not row or (tid in req.pairs and not mb):
                errors.append({"id": tid, "error": "unknown track or release track"})
                continue
            eff = staging.effective(row, entries.get(tid))
            tags = albummatch.tags_for(rel, mb, req.original_year)
            if req.genre is not None:
                tags = {k: v for k, v in tags.items() if k != "genre"} | ({"genre": req.genre} if req.genre.strip() else {})
            change = {f: tags[f] for f in fields if f in tags and (eff.get(f) or "") != tags[f]
                      and not (f in req.keep and (eff.get(f) or "").strip())}
            if change:
                todo.append((row, change))
        res: dict = {"staged": True}
        if todo:
            step = staging.Step(conn, f"MusicBrainz: {rel['album']} ({len(todo)} tracks)")
            for row, change in todo:
                staging.stage_edit(conn, row, change, step)
            res = _finish(conn, step, [r["id"] for r, _ in todo])
    covered = folders = 0
    if req.cover and rows:
        cfg = load_app_settings()
        try:
            with db() as conn:
                if cfg.cover_target in ("folder", "both"):
                    mime, data = await asyncio.to_thread(_fetch_caa, req.mb_album_id, _caa_size(cfg.cover_folder_size))
                    for d in {r["directory"] for r in rows.values()}:
                        try:
                            covers.write_folder(conn, d, mime, data, cfg.cover_folder_size)
                            folders += 1
                        except Exception as e:  # noqa: BLE001
                            errors.append({"id": None, "error": f"folder cover: {e}"})
                if cfg.cover_target in ("tracks", "both"):
                    mime, data = await asyncio.to_thread(_fetch_caa, req.mb_album_id, _caa_size(cfg.cover_embed_size))
                    for row in rows.values():
                        try:
                            covers.set_track(conn, row, mime, data, cfg.cover_embed_size)
                            covered += 1
                        except Exception as e:  # noqa: BLE001 -- report per file
                            errors.append({"id": row["id"], "error": f"cover: {e}"})
        except Exception as e:  # noqa: BLE001
            errors.append({"id": None, "error": f"cover art: {e}"})
    return {**res, "changed": len(todo), "covers": covered, "folder_covers": folders,
            "errors": errors + res.get("errors", [])}


# ─── CD rips: disc IDs, adding a release, what the rip recorded ──────────────

def _disc_key(r) -> tuple[str, str, str]:
    """One disc: folder, album, disc number (no number = disc 1)."""
    return (r["directory"], r["album"] or "", (str(r["disc_number"] or "1").split("/")[0] or "1"))


def _discs(conn, ids: list[int]) -> dict[tuple, list[dict]]:
    """The selected tracks by disc, with whether the selection holds the whole disc."""
    from api.tags import _rows
    groups: dict[tuple, list[dict]] = {}
    for r in _rows(conn, ids):
        groups.setdefault(_disc_key(r), []).append(dict(r))
    return groups


def _whole(conn, key: tuple, got: list[dict]) -> bool:
    rows = conn.execute("SELECT album, disc_number, directory FROM tracks WHERE directory = ?", (key[0],)).fetchall()
    return sum(1 for r in rows if _disc_key(r) == key) == len(got)


class TrackIds(BaseModel):
    track_ids: list[int]


VERIFY_MAX = 15     # MusicBrainz allows ~1 request/s; a request must finish inside the proxy's 30 s


@router.post("/disc-ids")
async def fill_disc_ids(req: TrackIds):
    """
    Work out each selected disc's MusicBrainz disc ID and TOC from its tracks'
    exact lengths (core/discid.py) and stage them, for rips made before the
    ripper tagged them. Discs that already have one are left alone. The first
    few are checked against MusicBrainz.
    """
    from api.tags import _finish
    from core.discid import from_lengths
    from core.tagger import DISC_FIELDS, read_disc_tags
    if not req.track_ids:
        raise HTTPException(400, "No track IDs provided")
    with db() as conn:
        groups = _discs(conn, req.track_ids)
        results, todo = [], []
        for key, g in groups.items():
            name = key[1] or key[0].rsplit("/", 1)[-1]
            if len(groups) > 1 and any(k[:2] == key[:2] and k != key for k in groups):
                name += f" (disc {key[2]})"
            if all(r.get("mb_disc_id") for r in g):
                results.append({"album": name, "status": "has one", "disc_id": g[0]["mb_disc_id"]})
                continue
            if not _whole(conn, key, g):
                results.append({"album": name, "status": "skipped", "why": "select the whole disc"})
                continue
            got = from_lengths(g)
            if isinstance(got, str):
                results.append({"album": name, "status": "skipped", "why": got})
                continue
            res = {"album": name, "status": "staged", "disc_id": got[0], "toc": got[1],
                   "mb_album_id": _common(g, "mb_album_id")}
            results.append(res)
            todo.append((res, g))
    for res, _ in todo[:VERIFY_MAX]:
        rels = await asyncio.to_thread(mbp.releases_by_discid, res["disc_id"])
        res["on_musicbrainz"] = [c["mb_album_id"] for c in rels]
        res["matches_album"] = bool(res["mb_album_id"]) and res["mb_album_id"] in res["on_musicbrainz"]
    if not todo:
        return {"results": results, "staged": False}
    with db() as conn:
        n = sum(len(g) for _, g in todo)
        step = staging.Step(conn, f"Disc IDs from track lengths for {len(todo)} disc{'s' if len(todo) != 1 else ''}")
        for res, g in todo:
            for t in g:
                cur = read_disc_tags(t["path"])     # what the file holds: Review's "old", undo's target
                conn.execute(f"UPDATE tracks SET {', '.join(f'{f} = ?' for f in DISC_FIELDS)} WHERE id = ?",
                             [*(cur[f] for f in DISC_FIELDS), t["id"]])
                row = conn.execute("SELECT * FROM tracks WHERE id = ?", (t["id"],)).fetchone()
                staging.stage(conn, row, {"mb_disc_id": res["disc_id"], "cd_toc": res["toc"]}, step=step)
        out = _finish(conn, step, [t["id"] for _, g in todo for t in g])
    return {"results": results, "tracks": n, **out}


ARTIST_LOOKUPS = 20     # ~1 s each at MusicBrainz's rate: stay inside the proxy's 30 s


def _credit(prefix: str, names: str | None, ids: dict[str, str]) -> list[tuple[str, str]]:
    """
    artist_credit fields for a "; "-joined artist value ("A", "A & B", "A, B & C"),
    with each artist's MBID when known, so the release editor has it linked.
    """
    from core.multivalue import split_values
    parts = split_values(names or "") if names else []
    out = []
    for i, p in enumerate(parts):
        out.append((f"{prefix}artist_credit.names.{i}.name", p))
        out.append((f"{prefix}artist_credit.names.{i}.artist.name", p))
        if ids.get(p):
            out.append((f"{prefix}artist_credit.names.{i}.mbid", ids[p]))
        if i < len(parts) - 1:
            out.append((f"{prefix}artist_credit.names.{i}.join_phrase", " & " if i == len(parts) - 2 else ", "))
    return out


class Seed(BaseModel):
    track_ids: list[int]
    redirect_uri: Optional[str] = None


@router.post("/mb-seed")
def mb_seed(req: Seed):
    """
    The fields that open MusicBrainz's Add release page filled in from one
    album (https://musicbrainz.org/doc/Development/Release_Editor_Seeding):
    the browser POSTs them to /release/add, the user reviews and submits.
    Seeding has no disc ID field: it's attached once the release exists
    (disc-info's attach_url; the app offers it when MusicBrainz sends you back).
    """
    with db() as conn:
        groups = _discs(conn, req.track_ids)
    albums = {k[:2] for k in groups}
    if len(albums) != 1:
        raise HTTPException(400, "Select one album")
    tracks = [t for g in groups.values() for t in g]
    album = _common(tracks, "album") or next(iter(albums))[0].rsplit("/", 1)[-1]
    album_artist = _common(tracks, "album_artist") or _common(tracks, "artist")
    artists = _artist_ids(tracks, album_artist)
    f: list[tuple[str, str]] = [("name", album), ("status", "official")]
    f += _credit("", album_artist, artists["ids"])
    year = (_common(tracks, "year") or "")[:4]
    if year.isdigit():
        f.append(("events.0.date.year", year))
    barcode = _common(tracks, "barcode")
    if barcode:
        f.append(("barcode", barcode))
    for m, key in enumerate(sorted(groups, key=lambda k: int(k[2]) if k[2].isdigit() else 0)):
        g = sorted(groups[key], key=lambda t: int(str(t["track_number"] or 0).split("/")[0] or 0)
                   if str(t["track_number"] or "0").split("/")[0].isdigit() else 0)
        p = f"mediums.{m}."
        f.append((p + "format", "CD"))       # mediums are numbered by their index: no position field
        for i, t in enumerate(g):
            tp = f"{p}track.{i}."
            f.append((tp + "name", t["title"] or t["filename"].rsplit(".", 1)[0]))
            f.append((tp + "number", str(t["track_number"] or i + 1).split("/")[0]))
            if t.get("duration"):
                f.append((tp + "length", str(round(t["duration"] * 1000))))
            if t.get("artist") and t["artist"] != album_artist:
                f += _credit(tp, t["artist"], artists["ids"])
            if t.get("mb_track_id"):
                f.append((tp + "recording", t["mb_track_id"]))
    f.append(("edit_note", "Added with tggr from a CD rip (FLAC): titles and order from the tags, lengths from the files."))
    if req.redirect_uri:
        f.append(("redirect_uri", req.redirect_uri))
    return {"action": "https://musicbrainz.org/release/add", "album": album, "fields": f,
            "artists": {k: v for k, v in artists.items() if k != "ids"}}


def _artist_ids(tracks: list[dict], album_artist: str | None) -> dict:
    """
    An MBID for each artist the release credits, so the release editor arrives
    with them linked: from the tags when the files were matched before (a lone
    artist's mb_artist_id / mb_album_artist_id), else MusicBrainz's one artist
    with exactly that name. Several with that name, or none: left for you.
    """
    from core.multivalue import split_values
    ids: dict[str, str] = {}
    names: list[str] = []
    for a, mbid in [(album_artist, _common(tracks, "mb_album_artist_id")),
                    *((t.get("artist"), t.get("mb_artist_id")) for t in tracks)]:
        parts = split_values(a or "") if a else []
        if len(parts) == 1 and mbid and _UUID_RE.match(mbid):
            ids.setdefault(parts[0], mbid)
        names += [p for p in parts if p not in names]
    out = {"ids": ids, "linked": len([n for n in names if n in ids]), "ambiguous": [], "unknown": [], "unchecked": []}
    todo = [n for n in names if n not in ids]
    for n in todo[:ARTIST_LOOKUPS]:
        status, mbid = mbp.find_artist(n)
        if mbid:
            ids[n] = mbid
            out["linked"] += 1
        else:
            out[status].append(n)
    out["unchecked"] = todo[ARTIST_LOOKUPS:]
    return out


@router.post("/disc-info")
def disc_info(req: TrackIds):
    """What a rip recorded about its disc(s), with MusicBrainz links that use it."""
    import urllib.parse
    with db() as conn:
        groups = _discs(conn, req.track_ids)
    tracks = [t for g in groups.values() for t in g]
    mb_album_id = _common(tracks, "mb_album_id")
    discs = []
    for key, g in sorted(groups.items(), key=lambda kv: kv[0]):
        disc_id, toc = _common(g, "mb_disc_id"), _common(g, "cd_toc")
        attach = None
        if disc_id and toc:
            attach = "https://musicbrainz.org/cdtoc/attach?" + urllib.parse.urlencode(
                {"id": disc_id, "tracks": len(toc.split()) - 3, "toc": toc})
        discs.append({"disc": key[2], "disc_id": disc_id, "toc": toc, "attach_url": attach})
    ordered = sorted(tracks, key=lambda t: (_disc_key(t)[2].zfill(3), str(t["track_number"] or "").split("/")[0].zfill(3)))
    isrcs = [t.get("isrc") or "" for t in ordered]
    isrc_url = None
    if mb_album_id and any(isrcs):
        q = {"mbid": mb_album_id, **{f"isrc{i + 1}": v for i, v in enumerate(isrcs) if v}}
        isrc_url = "https://magicisrc.kepstin.ca/?" + urllib.parse.urlencode(q)
    trouble = [{"title": t["title"] or t["filename"], "quality": t["rip_quality"]} for t in ordered
               if t.get("rip_quality") not in (None, "", "clean")]
    matches = sorted({t["rip_match"] for t in tracks if t.get("rip_match")})
    return {"discs": discs, "barcode": _common(tracks, "barcode"), "isrcs": sum(1 for v in isrcs if v),
            "isrc_url": isrc_url, "rip_match": matches, "trouble": trouble,
            "ripped": any(t.get("rip_quality") for t in tracks), "mb_album_id": mb_album_id}
