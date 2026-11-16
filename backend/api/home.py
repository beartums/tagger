"""The landing page: the library at a glance, what's waiting, and what changed lately."""
from __future__ import annotations

from fastapi import APIRouter

from core import staging
from core.database import db
from core.history import list_changes

router = APIRouter()


@router.get("")
def home():
    from api.config import _load, list_libraries
    from api.library import QUALITY_ISSUE_LABELS
    off = set(_load().quality_off)
    with db() as conn:
        tracks = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        albums = conn.execute("SELECT COUNT(*) FROM (SELECT 1 FROM tracks GROUP BY directory, album)").fetchone()[0]
        quality = [{"key": r["key"], "tracks": r["tracks"], "albums": r["albums"], "at": r["checked_at"]}
                   for r in conn.execute("SELECT * FROM quality_results WHERE tracks > 0 ORDER BY tracks DESC")
                   if r["key"] not in off and r["key"] in QUALITY_ISSUE_LABELS]
        # Newest first by when they came in (track ids grow as files are added).
        recent = [dict(r) for r in conn.execute(
            "SELECT directory, album, COALESCE(NULLIF(album_artist, ''), artist) AS artist, COUNT(*) AS tracks,"
            " MAX(id) AS newest, MIN(id) AS cover_track_id FROM tracks GROUP BY directory, album"
            " ORDER BY newest DESC LIMIT 8")]
        jobs = [dict(r) for r in conn.execute(
            "SELECT id, kind, status, scanned, total FROM scan_jobs WHERE status IN ('pending', 'running')")]
        changes = list_changes(conn, 5)
        staged = staging.count(conn)
    return {"tracks": tracks, "albums": albums, "libraries": list_libraries(), "staged": staged,
            "quality": quality, "recent_albums": recent, "changes": changes, "jobs": jobs}
