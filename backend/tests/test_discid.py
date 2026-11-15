from core.discid import disc_id, from_lengths, parse_toc


def test_disc_id_matches_musicbrainz():
    # A real disc: MusicBrainz's ws/2 lists this ID with these offsets, and
    # tggr worked the same TOC out from the rip's FLAC lengths (2026-11-15).
    toc = "1 14 213472 150 19269 24547 40780 58012 71355 84560 98470 117305 132500 149302 164560 185262 200502"
    assert disc_id(*parse_toc(toc)) == "wqV8dKyb5F4uMJt0ltAS77GQ8Ig-"


def test_from_lengths_rebuilds_the_toc():
    toc = parse_toc("1 3 30150 150 10150 20150")
    tracks = [{"track_number": str(i + 1), "format": "flac", "sample_rate": 44100, "channels": 2,
               "duration": 10000 * 588 / 44100} for i in range(3)]
    got = from_lengths(tracks)
    assert got == (disc_id(*toc), "1 3 30150 150 10150 20150")


def test_from_lengths_refuses_what_isnt_an_exact_rip():
    t = {"track_number": "1", "format": "flac", "sample_rate": 44100, "channels": 2, "duration": 100.001}
    assert "whole CD sectors" in from_lengths([t])
    assert "lossless" in from_lengths([{**t, "format": "mp3"}])
    assert "1 to N" in from_lengths([{**t, "duration": 588 / 44100, "track_number": "2"}])
