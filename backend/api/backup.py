"""
Backup and restore: what tggr keeps, in one zip, all of it or the parts you pick.

    tggr-backup.json   what this is: app, version, when, which parts, the interface preferences
    data:        library.db (an SQLite online-backup snapshot) and trash/... (what
                 History's undo puts back)
    settings:    settings.json, as stored (API keys stay encrypted: restoring it
                 needs the same TGGR_SECRET_KEY)
    prefs:       the browser's interface preferences (in the manifest)
    environment: tggr.env, the TGGR_* / TAGGER_* the server runs with, to set on a
                 new container (secrets only when asked). Never applied by a restore.

Spectrogram images are a cache and are left out. A restore replaces the parts
you pick that the backup has, so a new config volume can start from a backup
instead of being renamed.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import time
import zipfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.config import settings
from core.database import db, init_db

router = APIRouter()

MANIFEST = "tggr-backup.json"
FORMAT = 2
PARTS = ("data", "settings", "prefs", "environment")
SECRET_ENV = ("SECRET_KEY", "PASSWORD")


class BackupRequest(BaseModel):
    prefs: dict[str, str] = {}      # the browser's interface preferences (localStorage)
    parts: list[str] = ["data", "settings", "prefs"]
    secrets: bool = False           # environment: include TGGR_SECRET_KEY / TGGR_PASSWORD


def _snapshot_db(dest: Path) -> None:
    src = sqlite3.connect(settings.db_path)
    out = sqlite3.connect(dest)
    try:
        src.backup(out)
    finally:
        out.close()
        src.close()


def _env_file(secrets: bool) -> str:
    lines = ["# tggr's environment when backed up: set these on the new container.",
             "# (TAGGER_* is the older name of each; TGGR_ wins when both are set.)"]
    for k in sorted(os.environ):
        if not k.startswith(("TGGR_", "TAGGER_")) or k.endswith(("IMAGE_VERSION", "GIT_SHA", "BUILD_DATE")):
            continue
        if any(k.endswith(s) for s in SECRET_ENV) and not secrets:
            lines.append(f"# {k}=<left out: back up with secrets to include it>")
        else:
            lines.append(f"{k}={os.environ[k]}")
    return "\n".join(lines) + "\n"


@router.post("")
def make_backup(req: BackupRequest, background: BackgroundTasks):
    """The zip, streamed as a download; the temp files go once it's sent."""
    from main import app
    parts = [p for p in PARTS if p in req.parts]
    if not parts:
        raise HTTPException(400, "Pick at least one part to back up")
    tmp = Path(tempfile.mkdtemp(prefix="tggr-backup-"))
    background.add_task(shutil.rmtree, tmp, True)
    with db() as conn:
        tracks = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    manifest = {"app": "tggr", "format": FORMAT, "version": app.version, "parts": parts,
                "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                **({"tracks": tracks} if "data" in parts else {}),
                **({"prefs": req.prefs} if "prefs" in parts else {})}
    name = f"tggr-backup-{'-'.join(parts) if len(parts) < len(PARTS) else 'all'}-{time.strftime('%Y%m%d-%H%M')}.zip"
    zpath = tmp / name
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(MANIFEST, json.dumps(manifest, indent=2))
        if "data" in parts:
            _snapshot_db(tmp / "library.db")
            z.write(tmp / "library.db", "library.db")
            trash = settings.config_dir / "trash"
            if trash.is_dir():
                for f in sorted(trash.iterdir()):
                    if f.is_file():
                        z.write(f, f"trash/{f.name}")
        if "settings" in parts and settings.settings_file.exists():
            z.write(settings.settings_file, "settings.json")
        if "environment" in parts:
            z.writestr("tggr.env", _env_file(req.secrets))
    return FileResponse(zpath, media_type="application/zip", filename=name)


def _running_jobs() -> int:
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM scan_jobs WHERE status IN ('pending', 'running')").fetchone()[0]


@router.post("/restore")
async def restore_backup(file: UploadFile = File(...), parts: str = Form("data,settings,prefs")):
    """
    Replace the picked parts (comma-separated: data, settings, prefs) with the
    backup's. Returns what was restored, the interface preferences when picked,
    and the environment file's text when it has one (to set by hand).
    """
    want = {p for p in parts.split(",") if p in PARTS}
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
            if MANIFEST not in names:
                raise HTTPException(400, "Not a tggr backup (no tggr-backup.json)")
            manifest = json.loads(z.read(MANIFEST))
            if manifest.get("format", 0) > FORMAT:
                raise HTTPException(400, "This backup is from a newer tggr: update first")
            has = {"data": "library.db" in names, "settings": "settings.json" in names,
                   "prefs": "prefs" in manifest, "environment": "tggr.env" in names}
            doing = [p for p in PARTS if p in want and has[p]]
            if not doing:
                raise HTTPException(400, "This backup has none of the parts picked (it has: "
                                    + (", ".join(p for p in PARTS if has[p]) or "nothing") + ")")
            if "data" in doing and _running_jobs():
                raise HTTPException(409, "A scan or lookup is running: stop it (Background) and try again")
            if "data" in doing:
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
            settings_json = z.read("settings.json") if "settings" in doing else None
            if settings_json is not None:
                json.loads(settings_json)                       # must parse
            env_text = z.read("tggr.env").decode() if has["environment"] else None

            # Everything checked: replace. The database page by page into the
            # live file, so open connections see the new contents.
            if "data" in doing:
                src = sqlite3.connect(tmp / "library.db")
                dst = sqlite3.connect(settings.db_path)
                try:
                    src.backup(dst)
                finally:
                    dst.close()
                    src.close()
                init_db()                                       # an older backup gets today's columns
                trash = settings.config_dir / "trash"
                if trash.is_dir():
                    shutil.rmtree(trash)
                trash.mkdir(parents=True, exist_ok=True)
                for n in names:
                    if n.startswith("trash/") and not n.endswith("/"):
                        name = Path(n).name                     # flat; never a path out of trash/
                        if name and name not in (".", ".."):
                            (trash / name).write_bytes(z.read(n))
            if settings_json is not None:
                settings.settings_file.write_bytes(settings_json)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with db() as conn:
        tracks = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    return {"ok": True, "restored": [p for p in doing if p != "environment"], "tracks": tracks,
            "created": manifest.get("created"), "version": manifest.get("version"),
            "prefs": (manifest.get("prefs") or {}) if "prefs" in doing else None,
            "environment": env_text if "environment" in doing else None}
