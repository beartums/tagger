"""ReplayGain: measured per album, staged like a tag edit, written and undone."""
import pytest

from core.replaygain import RgError
from core.tagger import read_tags, write_tags, read_replaygain
from tests.test_staging import _insert, _mp3, lib, needs_ffmpeg  # noqa: F401  (fixture)


@pytest.mark.parametrize("ext", [".mp3", ".flac", ".m4a"])
def test_replaygain_roundtrip(make_audio, ext):
    path = make_audio(ext)
    write_tags(path, {"rg_track_gain": "-6.21 dB", "rg_track_peak": "0.987654"})
    got = read_replaygain(str(path))
    assert got == {"rg_track_gain": "-6.21 dB", "rg_track_peak": "0.987654", "rg_album_gain": "", "rg_album_peak": ""}
    write_tags(path, {"rg_track_gain": ""})
    assert read_tags(path)["rg_track_gain"] is None


def test_lowercase_id3_frames_are_read_and_replaced(make_audio):
    from mutagen.id3 import ID3, TXXX
    path = make_audio(".mp3")
    tags = ID3(str(path)); tags.add(TXXX(encoding=3, desc="replaygain_track_gain", text=["1.00 dB"])); tags.save()
    assert read_replaygain(str(path))["rg_track_gain"] == "1.00 dB"
    write_tags(path, {"rg_track_gain": "2.00 dB"})
    frames = [f.desc for f in ID3(str(path)).getall("TXXX")]
    assert frames == ["REPLAYGAIN_TRACK_GAIN"]


def _fake_measure(calls):
    def measure(paths, album):
        calls.append((sorted(p.rsplit("/", 1)[1] for p in paths), album))
        out = {p: {"rg_track_gain": "-1.00 dB", "rg_track_peak": "0.500000"} for p in paths}
        if album:
            for v in out.values():
                v.update(rg_album_gain="-2.00 dB", rg_album_peak="0.600000")
        return out
    return measure


@needs_ffmpeg
def test_each_album_measured_alone_and_staged(client, lib, monkeypatch):
    import api.tags as t
    calls = []
    monkeypatch.setattr(t, "rg_tool", lambda: "rsgain")
    monkeypatch.setattr(t, "rg_measure", _fake_measure(calls))
    a = [_insert(_mp3(lib / "Shared" / "A" / f"{i}.mp3"), album="A") for i in (1, 2)]
    b = [_insert(_mp3(lib / "Shared" / "B" / f"{i}.mp3"), album="B") for i in (1, 2)]

    res = client.post("/api/tags/replaygain", json={"track_ids": [*a, b[0]]}).json()
    assert res["staged"] is True and res["measured"] == 3 and res["albums"] == 1
    assert sorted(calls) == [(["1.mp3"], False), (["1.mp3", "2.mp3"], True)]   # B partly selected: track gain only
    assert read_tags(str(lib / "Shared" / "A" / "1.mp3"))["rg_track_gain"] is None   # staged, not written

    staged = {s["id"]: {c["field"]: c["new"] for c in s["changes"]} for s in client.get("/api/staged").json()["tracks"]}
    assert staged[a[0]]["rg_album_gain"] == "-2.00 dB"
    assert "rg_album_gain" not in staged[b[0]]

    w = client.post("/api/staged/apply", json={}).json()
    assert read_replaygain(str(lib / "Shared" / "A" / "1.mp3"))["rg_album_peak"] == "0.600000"
    client.post(f"/api/library/history/{w['change_id']}/undo")
    assert read_replaygain(str(lib / "Shared" / "A" / "1.mp3"))["rg_track_gain"] == ""   # undo removes them again


@needs_ffmpeg
def test_undo_of_other_edit_keeps_unread_replaygain(client, lib):
    f = _mp3(lib / "Shared" / "a.mp3", title="Old")
    write_tags(f, {"rg_track_gain": "-3.00 dB"})
    tid = _insert(f, title="Old")                     # rg_* NULL: scanned before ReplayGain was read
    client.patch(f"/api/tags/{tid}", json={"title": "New"})
    w = client.post("/api/staged/apply", json={}).json()
    client.post(f"/api/library/history/{w['change_id']}/undo")
    assert read_tags(str(f))["title"] == "Old"
    assert read_replaygain(str(f))["rg_track_gain"] == "-3.00 dB"


def test_rsgain_output_parsed_by_order(monkeypatch):
    import subprocess
    from core import replaygain
    out = ("Filename\tLoudness (LUFS)\tGain (dB)\tPeak\t Peak (dB)\tPeak Type\tClipping Adjustment?\n"
           "a.flac\t-21.75\t3.75\t0.124969\t-18.06\tSample\tN\n"
           "b.mp3\t-32.21\t14.21\t0.035767\t-28.93\tSample\tN\n"
           "Album\t-24.39\t6.39\t0.124969\t-18.06\tSample\tN\n")
    monkeypatch.setattr(replaygain, "rg_tool", lambda: "rsgain")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, out, ""))
    got = replaygain.measure(["/m/A/a.flac", "/m/A/b.mp3"], album=True)
    assert got["/m/A/b.mp3"] == {"rg_track_gain": "14.21 dB", "rg_track_peak": "0.035767",
                                 "rg_album_gain": "6.39 dB", "rg_album_peak": "0.124969"}
    with pytest.raises(RgError):
        replaygain.measure(["/m/A/b.mp3", "/m/A/a.flac"], album=True)   # out of order
