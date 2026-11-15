"""
Backup and restore: everything tggr keeps, in one zip.

    tggr-backup.json   what this is: app, version, when, the interface preferences
    library.db         the database (an SQLite online-backup snapshot)
    settings.json      settings as stored (API keys stay encrypted: restore
                       needs the same TGGR_SECRET_KEY to read them)
    trash/...          files moved to the trash, which History's undo puts back

Spectrogram images are a cache and are left out. Restore replaces all of it,
so a new config volume can start from a backup instead of being renamed.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import time
import zipfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.config import settings
from core.database import db, init_db

router = APIRouter()

MANIFEST = "tggr-backup.json"
FORMAT = 1


class BackupRequest(BaseModel):
    prefs: dict[str, str] = {}      # the browser's interface preferences (localStorage)


def _snapshot_db(dest: Path) -> None:
    src = sqlite3.connect(settings.db_path)
    out = sqlite3.connect(dest)
    try:
        src.backup(out)
    finally:
        out.close()
        src.close()


@router.post("")
def make_backup(req: BackupRequest, background: BackgroundTasks):
    """The zip, streamed as a download; the temp files go once it's sent."""
    from main import app
    tmp = Path(tempfile.mkdtemp(prefix="tggr-backup-"))
    background.add_task(shutil.rmtree, tmp, True)
    _snapshot_db(tmp / "library.db")
    with db() as conn:
        tracks = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    manifest = {"app": "tggr", "format": FORMAT, "version": app.version,
                "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tracks": tracks, "prefs": req.prefs}
    name = f"tggr-backup-{time.strftime('%Y%m%d-%H%M')}.zip"
    zpath = tmp / name
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(MANIFEST, json.dumps(manifest, indent=2))
        z.write(tmp / "library.db", "library.db")
        if settings.settings_file.exists():
            z.write(settings.settings_file, "settings.json")
        trash = settings.config_dir / "trash"
        if trash.is_dir():
            for f in sorted(trash.iterdir()):
                if f.is_file():
                    z.write(f, f"trash/{f.name}")
    return FileResponse(zpath, media_type="application/zip", filename=name)


def _running_jobs() -> int:
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM scan_jobs WHERE status IN ('pending', 'running')").fetchone()[0]


@router.post("/restore")
async def restore_backup(file: UploadFile = File(...)):
    """Replace the database, settings and trash with a backup's. Returns its interface preferences."""
    if _running_jobs():
        raise HTTPException(409, "A scan or lookup is running: stop it (Background) and try again")
    tmp = Path(tempfile.mkdtemp(prefix="tggr-restore-"))
    try:
        zpath = tmp / "backup.zip"
        with zpath.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        try:
            z = zipfile.ZipFile(zpath)
        except zipfile.BadZipFile:
            raise HTTPException(400, "Not a zip file")
        with z:
            names = set(z.namelist())
            if MANIFEST not in names or "library.db" not in names:
                raise HTTPException(400, "Not a tggr backup (no tggr-backup.json / library.db)")
            manifest = json.loads(z.read(MANIFEST))
            if manifest.get("format", 0) > FORMAT:
                raise HTTPException(400, "This backup is from a newer tggr: update first")
            z.extract("library.db", tmp)
            try:
                chk = sqlite3.connect(tmp / "library.db")
                ok = chk.execute("PRAGMA quick_check").fetchone()[0]
                chk.execute("SELECT COUNT(*) FROM tracks").fetchone()
                chk.close()
            except sqlite3.DatabaseError as exc:
                raise HTTPException(400, f"The backup's database can't be read: {exc}")
            if ok != "ok":
                raise HTTPException(400, f"The backup's database is damaged: {ok}")
            settings_json = z.read("settings.json") if "settings.json" in names else None
            if settings_json is not None:
                json.loads(settings_json)                       # must parse
            trash_files = [n for n in names if n.startswith("trash/") and not n.endswith("/")]

            # Everything checked: replace. The database first, page by page into
            # the live file, so open connections see the new contents.
            src = sqlite3.connect(tmp / "library.db")
            dst = sqlite3.connect(settings.db_path)
            try:
                src.backup(dst)
            finally:
                dst.close()
                src.close()
            init_db()                                           # an older backup gets today's columns
            if settings_json is not None:
                settings.settings_file.write_bytes(settings_json)
            trash = settings.config_dir / "trash"
            if trash.is_dir():
                shutil.rmtree(trash)
            trash.mkdir(parents=True, exist_ok=True)
            for n in trash_files:
                name = Path(n).name                             # flat; never a path out of trash/
                if name and name not in (".", ".."):
                    (trash / name).write_bytes(z.read(n))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with db() as conn:
        tracks = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    return {"ok": True, "tracks": tracks, "created": manifest.get("created"),
            "version": manifest.get("version"), "prefs": manifest.get("prefs") or {}}
