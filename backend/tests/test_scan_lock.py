"""A scan must not hold the database write lock while it reads files (staged edits failed)."""
import sqlite3
import threading
import time

from core import scanner
from core.config import settings
from tests.test_staging import lib  # noqa: F401  (fixture)


def test_writes_go_through_while_a_scan_reads_slow_files(client, lib, monkeypatch):
    d = lib / "Shared" / "slow"
    d.mkdir(parents=True)
    for n in range(6):
        (d / f"{n}.mp3").write_bytes(b"")

    def slow_read(path, extended=True):
        time.sleep(0.4)                       # a file on a slow NAS
        return {"title": "t", "format": "mp3"}
    monkeypatch.setattr(scanner, "read_tags", slow_read)

    t = threading.Thread(target=scanner.scan_library, kwargs={"music_dirs": [str(lib / "Shared")]})
    t.start()
    time.sleep(1.5)                           # mid-scan: rows read, more being read
    conn = sqlite3.connect(str(settings.db_path), timeout=0.5)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS lock_probe (x)")
        conn.execute("INSERT INTO lock_probe VALUES (1)")
        conn.commit()                         # "database is locked" before the fix
    finally:
        conn.close()
    t.join()
    assert client.get("/api/library/tracks").json()["total"] == 6
