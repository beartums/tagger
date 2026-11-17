"""CD rips: disc IDs from track lengths, the MusicBrainz pre-fill, rip info and checks."""
import re
from core.discid import disc_id, parse_toc
from core.database import db

TOC = "1 3 30150 150 10150 20150"


def _rip(lib_dir, n=3, **extra):
    ids = []
    with db() as conn:
        for i in range(1, n + 1):
            p = f"{lib_dir}/Artist/Album/0{i} Song {i}.flac"
            cols = {"path": p, "filename": p.rsplit("/", 1)[1], "directory": p.rsplit("/", 1)[0], "format": "flac",
                    "scanned_at": 1.0, "title": f"Song {i}", "artist": "Artist", "album_artist": "Artist",
                    "album": "Album", "track_number": str(i), "sample_rate": 44100, "channels": 2,
                    "duration": 10000 * 588 / 44100, "year": "1999", **extra}
            ids.append(conn.execute(f"INSERT INTO tracks ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                                    list(cols.values())).lastrowid)
    return ids


def test_disc_ids_from_lengths_are_staged(client, monkeypatch):
    import api.lookup as lk
    monkeypatch.setattr(lk.mbp, "releases_by_discid", lambda d: [])
    ids = _rip("/music/CD Rips")
    res = client.post("/api/lookup/disc-ids", json={"track_ids": ids}).json()
    assert res["staged"] is True
    r = res["results"][0]
    assert r["status"] == "staged" and r["toc"] == TOC and r["disc_id"] == disc_id(*parse_toc(TOC))
    assert r["on_musicbrainz"] == [] and r["matches_album"] is False
    staged = client.get("/api/staged").json()["tracks"]
    assert {c["field"] for c in staged[0]["changes"]} == {"mb_disc_id", "cd_toc"}


def test_disc_ids_need_the_whole_disc(client, monkeypatch):
    import api.lookup as lk
    monkeypatch.setattr(lk.mbp, "releases_by_discid", lambda d: [])
    ids = _rip("/music/CD Rips")
    r = client.post("/api/lookup/disc-ids", json={"track_ids": ids[:2]}).json()["results"][0]
    assert r["status"] == "skipped" and "whole disc" in r["why"]


def test_mb_seed_fills_the_add_release_form(client, monkeypatch):
    import api.lookup as lk
    monkeypatch.setattr(lk.mbp, "find_artist", lambda n: ("linked", "33333333-3333-3333-3333-333333333333"))
    ids = _rip("/music/CD Rips", cd_toc=TOC, barcode="0123456789012", mb_track_id="11111111-1111-1111-1111-111111111111")
    s = client.post("/api/lookup/mb-seed", json={"track_ids": ids, "redirect_uri": "https://tggr.example/"}).json()
    f = dict(s["fields"])
    assert s["action"] == "https://musicbrainz.org/release/add"
    assert f["name"] == "Album" and f["artist_credit.names.0.name"] == "Artist"
    assert f["artist_credit.names.0.mbid"] == "33333333-3333-3333-3333-333333333333"      # linked for the editor
    assert s["artists"] == {"linked": 1, "ambiguous": [], "unknown": [], "unchecked": []}
    assert f["events.0.date.year"] == "1999" and f["barcode"] == "0123456789012"
    assert f["mediums.0.format"] == "CD" and not any(k.endswith(".toc") for k in f)   # not a seeding field
    assert f["mediums.0.track.2.name"] == "Song 3" and f["mediums.0.track.2.length"] == str(round(10000 * 588 / 44.1))
    assert f["mediums.0.track.0.recording"] == "11111111-1111-1111-1111-111111111111"
    assert "mediums.0.track.0.artist_credit.names.0.name" not in f      # same as the album artist
    assert f["redirect_uri"] == "https://tggr.example/"
    # Only fields MusicBrainz documents (wiki: Development/Seeding/Release_Editor);
    # anything else shows as "Unknown field" on its page.
    ac = r"artist_credit\.names\.\d+\.(mbid|name|artist\.name|join_phrase)"
    documented = re.compile("|".join([
        r"name|release_group|type|comment|annotation|barcode|language|script|status|packaging|edit_note|redirect_uri",
        r"events\.\d+\.(date\.(year|month|day)|country)", r"labels\.\d+\.(mbid|catalog_number|name)", ac,
        r"mediums\.\d+\.(format|name)", r"mediums\.\d+\.track\.\d+\.(name|number|recording|length)",
        rf"mediums\.\d+\.track\.\d+\.{ac}", r"urls\.\d+\.(url|link_type)"]))
    assert [k for k, _ in s["fields"] if not documented.fullmatch(k)] == []


def test_disc_info_links_and_rip_checks(client):
    did = disc_id(*parse_toc(TOC))
    ids = _rip("/music/CD Rips", mb_disc_id=did, cd_toc=TOC, isrc="USABC9900001",
               mb_album_id="22222222-2222-2222-2222-222222222222", rip_match="near", rip_quality="clean")
    with db() as conn:
        conn.execute("UPDATE tracks SET rip_quality = 'repaired 2' WHERE id = ?", (ids[1],))
    info = client.post("/api/lookup/disc-info", json={"track_ids": ids}).json()
    assert info["discs"][0]["attach_url"].startswith("https://musicbrainz.org/cdtoc/attach?id=")
    assert "tracks=3" in info["discs"][0]["attach_url"]
    assert info["isrcs"] == 3 and "isrc1=USABC9900001" in info["isrc_url"]
    assert info["trouble"] == [{"title": "Song 2", "quality": "repaired 2"}] and info["rip_match"] == ["near"]
    near = client.get("/api/library/tracks?issues=rip_near").json()["total"]
    trouble = client.get("/api/library/tracks?issues=rip_trouble").json()["total"]
    assert (near, trouble) == (3, 1)


def test_disc_tags_roundtrip_as_the_ripper_writes_them(make_audio):
    import mutagen
    from core.tagger import read_disc_tags, read_tags, write_tags
    path = make_audio(".flac")
    f = mutagen.File(str(path))
    f["MUSICBRAINZ_DISCID"] = "abc-"; f["MUSICBRAINZ_TOC"] = TOC; f["ISRC"] = "USABC9900001"
    f["RIP_MATCH"] = "exact"; f["RIP_QUALITY"] = "clean"; f.save()       # abcde's uppercase names
    assert read_disc_tags(str(path)) == {"mb_disc_id": "abc-", "cd_toc": TOC, "barcode": "", "isrc": "USABC9900001",
                                         "rip_match": "exact", "rip_quality": "clean"}
    write_tags(path, {"mb_disc_id": "xyz-"})
    assert read_tags(path)["mb_disc_id"] == "xyz-"


def test_artists_linked_from_tags_then_by_exact_name(client, monkeypatch):
    import api.lookup as lk
    asked = []
    answers = {"Guest": ("linked", "44444444-4444-4444-4444-444444444444"), "John Smith": ("ambiguous", None),
               "Nobody Yet": ("unknown", None)}
    monkeypatch.setattr(lk.mbp, "find_artist", lambda n: (asked.append(n), answers[n])[1])
    ids = _rip("/music/CD Rips", mb_album_artist_id="55555555-5555-5555-5555-555555555555")
    with db() as conn:
        conn.execute("UPDATE tracks SET artist = 'Artist; Guest' WHERE id = ?", (ids[0],))
        conn.execute("UPDATE tracks SET artist = 'John Smith' WHERE id = ?", (ids[1],))
        conn.execute("UPDATE tracks SET artist = 'Nobody Yet' WHERE id = ?", (ids[2],))
    s = client.post("/api/lookup/mb-seed", json={"track_ids": ids}).json()
    f = dict(s["fields"])
    assert f["artist_credit.names.0.mbid"] == "55555555-5555-5555-5555-555555555555"     # from the tags: not asked
    assert "Artist" not in asked
    assert f["mediums.0.track.0.artist_credit.names.1.mbid"] == "44444444-4444-4444-4444-444444444444"
    assert "mediums.0.track.1.artist_credit.names.0.mbid" not in f                          # ambiguous: yours to pick
    assert s["artists"] == {"linked": 2, "ambiguous": ["John Smith"], "unknown": ["Nobody Yet"], "unchecked": []}


def test_seed_artists_looked_up_one_request_each(client, monkeypatch):
    # The browser asks which names need a lookup, looks each up on its own
    # (each well inside the proxy's 30 s), then seeds with the answers: mb-seed makes no calls.
    import api.lookup as lk
    answers = {"Guest": ("linked", "44444444-4444-4444-4444-444444444444"), "John Smith": ("ambiguous", None)}
    monkeypatch.setattr(lk.mbp, "find_artist", lambda n: answers[n])
    ids = _rip("/music/CD Rips", mb_album_artist_id="55555555-5555-5555-5555-555555555555")
    with db() as conn:
        conn.execute("UPDATE tracks SET artist = 'Artist; Guest' WHERE id = ?", (ids[0],))
        conn.execute("UPDATE tracks SET artist = 'John Smith' WHERE id = ?", (ids[1],))
    names = client.post("/api/lookup/mb-seed/artists", json={"track_ids": ids}).json()
    assert names == {"lookup": ["Guest", "John Smith"], "linked": 1}
    found = {n: client.post("/api/lookup/mb-artist", json={"name": n}).json() for n in names["lookup"]}
    monkeypatch.setattr(lk.mbp, "find_artist", lambda n: (_ for _ in ()).throw(AssertionError("no lookups in mb-seed")))
    s = client.post("/api/lookup/mb-seed", json={"track_ids": ids, "artists": found}).json()
    f = dict(s["fields"])
    assert f["mediums.0.track.0.artist_credit.names.1.mbid"] == "44444444-4444-4444-4444-444444444444"
    assert s["artists"] == {"linked": 2, "ambiguous": ["John Smith"], "unknown": [], "unchecked": []}
