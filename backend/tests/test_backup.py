"""Backup and restore: database, settings, trash and interface preferences."""
import io
import json
import zipfile

from core.config import settings
from core.database import db


def _insert(path):
    with db() as conn:
        return conn.execute("INSERT INTO tracks (path, filename, directory, format, scanned_at) VALUES (?, ?, ?, 'mp3', 1)",
                            (path, path.rsplit("/", 1)[1], path.rsplit("/", 1)[0])).lastrowid


def _count():
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]


def test_backup_then_restore_puts_everything_back(client):
    _insert("/music/A/1.mp3"); _insert("/music/A/2.mp3")
    client.patch("/api/config", json={"rename_template": "{artist}/{title}"})
    (settings.config_dir / "trash").mkdir(exist_ok=True)
    (settings.config_dir / "trash" / "gone.mp3").write_bytes(b"x")

    r = client.post("/api/backup", json={"prefs": {"tggr.pageSize": "250"}, "parts": ["data", "settings", "prefs"]})
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert {"tggr-backup.json", "library.db", "settings.json", "trash/gone.mp3"} <= set(z.namelist())
    assert json.loads(z.read("tggr-backup.json"))["tracks"] == 2

    # Things change after the backup ...
    _insert("/music/B/3.mp3")
    client.patch("/api/config", json={"rename_template": "{title}"})
    (settings.config_dir / "trash" / "gone.mp3").unlink()
    (settings.config_dir / "trash" / "later.mp3").write_bytes(b"y")

    # ... and the restore puts them back.
    res = client.post("/api/backup/restore", files={"file": ("b.zip", r.content, "application/zip")}).json()
    assert res["tracks"] == 2 and res["prefs"] == {"tggr.pageSize": "250"}
    assert res["restored"] == ["data", "settings", "prefs"] and res["environment"] is None
    assert _count() == 2
    assert client.get("/api/config").json()["rename_template"] == "{artist}/{title}"
    assert sorted(p.name for p in (settings.config_dir / "trash").iterdir()) == ["gone.mp3"]


def test_restore_refuses_what_isnt_a_backup(client):
    _insert("/music/A/1.mp3")
    bad = client.post("/api/backup/restore", files={"file": ("x.zip", b"not a zip", "application/zip")})
    assert bad.status_code == 400
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("tggr-backup.json", "{}")                # a manifest and nothing else
    bad = client.post("/api/backup/restore", files={"file": ("x.zip", buf.getvalue(), "application/zip")})
    assert bad.status_code == 400 and "none of the parts" in bad.json()["detail"]
    buf2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "w") as z:
        z.writestr("tggr-backup.json", json.dumps({"parts": ["data"]}))
        z.writestr("library.db", b"garbage")
    bad = client.post("/api/backup/restore", files={"file": ("x.zip", buf2.getvalue(), "application/zip")})
    assert bad.status_code == 400 and "database" in bad.json()["detail"]
    assert _count() == 1                                    # nothing replaced


def test_backup_and_restore_just_the_parts_picked(client, monkeypatch):
    _insert("/music/A/1.mp3")
    client.patch("/api/config", json={"rename_template": "{artist}/{title}"})
    monkeypatch.setenv("TGGR_MUSIC_DIR", "/music")
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("TGGR_SECRET_KEY", key)
    r = client.post("/api/backup", json={"parts": ["settings", "environment"]})
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert set(z.namelist()) == {"tggr-backup.json", "settings.json", "tggr.env"}          # no data
    env = z.read("tggr.env").decode()
    assert "TGGR_MUSIC_DIR=/music" in env and key not in env and "# TGGR_SECRET_KEY=<left out" in env
    with_secrets = client.post("/api/backup", json={"parts": ["environment"], "secrets": True}).content
    assert f"TGGR_SECRET_KEY={key}" in zipfile.ZipFile(io.BytesIO(with_secrets)).read("tggr.env").decode()
    assert client.post("/api/backup", json={"parts": []}).status_code == 400

    _insert("/music/A/2.mp3")                                   # data changes; restore only settings
    client.patch("/api/config", json={"rename_template": "{title}"})
    res = client.post("/api/backup/restore", data={"parts": "settings,environment"},
                      files={"file": ("b.zip", r.content, "application/zip")}).json()
    assert res["restored"] == ["settings"] and "TGGR_MUSIC_DIR=/music" in res["environment"]
    assert client.get("/api/config").json()["rename_template"] == "{artist}/{title}"
    assert _count() == 2                                       # the data was left alone


def test_home_and_about(client):
    _insert("/music/A/1.mp3"); _insert("/music/A/2.mp3")
    h = client.get("/api/home").json()
    assert h["tracks"] == 2 and h["albums"] == 1 and h["staged"] == 0
    assert h["recent_albums"][0]["tracks"] == 2 and h["changes"] == [] and h["jobs"] == []
    a = client.get("/api/about").json()
    assert a["license"] == "MIT" and a["db_bytes"] > 0 and a["source"].endswith("/tggr")
