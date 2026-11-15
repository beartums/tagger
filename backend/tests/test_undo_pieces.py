"""Undoing pieces: one staged field or action, one written field or move, in any order."""
from core import staging
from core.database import db
from core.tagger import read_tags
from tests.test_staging import _insert, _mp3, lib, needs_ffmpeg  # noqa: F401  (fixture)


def _staged(client):
    return {t["id"]: {c["field"]: c["new"] for c in t["changes"]} for t in client.get("/api/staged").json()["tracks"]}


def _write(client):
    return client.post("/api/staged/apply", json={}).json()["change_id"]


@needs_ffmpeg
def test_staged_field_and_action_discards_in_any_order(client, lib):
    f = _mp3(lib / "Shared" / "a.mp3", title="T")
    tid = _insert(f, title="T")
    client.patch(f"/api/tags/{tid}", json={"title": "New", "genre": "Rock"})      # action 1
    client.patch(f"/api/tags/{tid}", json={"year": "1999"})                       # action 2
    assert client.post("/api/staged/discard-part", json={"track_id": tid, "field": "title"}).json()["discarded"] == 1
    assert _staged(client)[tid] == {"genre": "Rock", "year": "1999"}
    client.post("/api/staged/undo")                                                # newest action: year
    assert _staged(client)[tid] == {"genre": "Rock"}                               # title doesn't come back
    client.patch(f"/api/tags/{tid}", json={"year": "2001"})                        # action 3
    first = client.get("/api/staged/actions").json()["steps"][-1]["id"]            # the oldest (action 1)
    client.post(f"/api/staged/steps/{first}/discard")                              # not the newest
    assert _staged(client)[tid] == {"year": "2001"}


@needs_ffmpeg
def test_written_fields_undo_in_any_order(client, lib):
    f = _mp3(lib / "Shared" / "a.mp3", title="T", genre="Pop")
    tid = _insert(f, title="T", genre="Pop")
    client.patch(f"/api/tags/{tid}", json={"title": "New"}); c1 = _write(client)
    client.patch(f"/api/tags/{tid}", json={"genre": "Rock"}); c2 = _write(client)

    parts = client.get(f"/api/library/history/{c1}").json()["parts"]
    assert parts == [{"track_id": tid, "name": "T", "field": "title", "old": "T", "new": "New", "undone": False, "blocked": None}]
    r = client.post(f"/api/library/history/{c1}/undo-part", json={"track_id": tid, "field": "title"})
    assert r.status_code == 200 and r.json()["change_undone"] is True      # the older change, first
    assert read_tags(str(f))["title"] == "T" and read_tags(str(f))["genre"] == "Rock"

    # Undoing the later change as a whole doesn't re-apply the earlier one's undone title.
    client.post(f"/api/library/history/{c2}/undo")
    assert read_tags(str(f))["title"] == "T" and read_tags(str(f))["genre"] == "Pop"


@needs_ffmpeg
def test_same_field_changed_later_blocks(client, lib):
    f = _mp3(lib / "Shared" / "a.mp3", title="T")
    tid = _insert(f, title="T")
    client.patch(f"/api/tags/{tid}", json={"title": "A", "genre": "Rock"}); c1 = _write(client)
    client.patch(f"/api/tags/{tid}", json={"title": "B"}); _write(client)
    parts = {p["field"]: p for p in client.get(f"/api/library/history/{c1}").json()["parts"]}
    assert "changed again later" in parts["title"]["blocked"] and parts["genre"]["blocked"] is None
    r = client.post(f"/api/library/history/{c1}/undo-part", json={"track_id": tid, "field": "title"})
    assert r.status_code == 400 and "later" in r.json()["detail"]
    assert client.post(f"/api/library/history/{c1}/undo-part", json={"track_id": tid, "field": "genre"}).status_code == 200
    assert read_tags(str(f))["title"] == "B" and not read_tags(str(f)).get("genre")


@needs_ffmpeg
def test_a_move_undoes_on_its_own(client, lib):
    f = _mp3(lib / "Shared" / "a.mp3", title="T")
    tid = _insert(f, title="T")
    dest = lib / "Shared" / "X" / "a.mp3"
    with db() as conn:
        row = conn.execute("SELECT * FROM tracks WHERE id = ?", (tid,)).fetchone()
        staging.stage(conn, row, {"genre": "Rock"}, new_path=str(dest))
    c = _write(client)
    assert dest.exists()
    r = client.post(f"/api/library/history/{c}/undo-part", json={"track_id": tid, "field": "path"}).json()
    assert r["change_undone"] is False
    assert f.exists() and not dest.exists() and not dest.parent.exists()
    assert read_tags(str(f))["genre"] == "Rock"                           # the tag edit stays
