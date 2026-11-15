import pytest

from core.naming import NamingRules, render_template, safe_name, _safe
from api.library import _m3u, _fts_query
from core.tagger import TAG_FIELDS, is_audio_file, _detect_format
from api.config import ALL_SCAN_TAGS


# ── render_template ────────────────────────────────────────────────────────

SAMPLE = {
    "title": "So What", "artist": "Miles Davis", "album": "Kind of Blue",
    "album_artist": "Miles Davis", "year": "1959", "track_number": "1", "disc_number": "1",
}


def test_render_basic():
    out = render_template("{album_artist}/{album}/{track_number:02d} {title}", SAMPLE, ".flac")
    assert out == "Miles Davis/Kind of Blue/01 So What.flac"


def test_render_sanitizes_unsafe_chars():
    tags = {**SAMPLE, "title": "A: B?", "album": "X<Y>"}
    out = render_template("{album}/{title}", tags, ".mp3")
    assert out.count("/") == 1  # only the template's own separator survives
    for ch in ':?<>*|"':
        assert ch not in out


def test_render_defaults_missing_numbers_to_zero():
    out = render_template("{track_number:02d} {title}", {"title": "T"}, ".flac")
    assert out == "00 T.flac"


def test_render_bad_template_raises():
    with pytest.raises((KeyError, ValueError, IndexError)):
        render_template("{nonexistent}", SAMPLE, ".flac")


def test_safe_never_empty():
    assert _safe("...") == "_"
    assert _safe("") == "_"


def test_slash_in_a_value_is_not_a_folder():
    tags = {**SAMPLE, "album_artist": "AC/DC", "album": "Love\\Hate"}
    assert render_template("{album_artist}/{album}/{title}", tags, ".flac") == "AC+DC/Love+Hate/So What.flac"
    assert render_template("{album_artist_the}/{title}", {**SAMPLE, "album_artist": "The A/B"}, ".flac") == "A+B, The/So What.flac"


def test_lidarr_illegal_and_smart_colon():
    tags = {**SAMPLE, "title": 'Re: Mix? <"10:30"> * |x|'}
    assert render_template("{title}", tags, ".mp3") == "Re - Mix! 10-30 - x.mp3"


@pytest.mark.parametrize("colon,want", [
    ("delete", "Re Mix 1030"), ("dash", "Re- Mix 10-30"),
    ("space_dash", "Re - Mix 10 -30"), ("space_dash_space", "Re -  Mix 10 - 30"),
])
def test_colon_options(colon, want):
    out = render_template("{title}", {"title": "Re: Mix 10:30"}, "", NamingRules.lidarr(colon=colon))
    assert out == want


def test_replace_illegal_off_deletes():
    rules = NamingRules.lidarr(replace_illegal=False)
    assert render_template("{title}", {"title": "AC/DC: Live?*"}, "", rules) == "ACDC Live"


def test_per_character_choices_and_others():
    rules = NamingRules.make(False, {"/": "&", ":": " -"}, other="_")
    assert render_template("{title}", {"title": "AC/DC: Live?*"}, "", rules) == "AC&DC - Live__"
    # A replacement can't smuggle in a folder or another illegal character.
    rules = NamingRules.make(True, {"/": "/x?"})
    assert render_template("{title}", {"title": "A/B: c"}, "", rules) == "AxB - c"


def test_settings_before_per_character_choices():
    class S:
        naming_replace_illegal = True; naming_colon = "dash"; naming_chars = None; naming_other = ""
    assert NamingRules.from_settings(S()) == NamingRules.lidarr(True, "dash")
    S.naming_chars = {"?": ""}; S.naming_colon = "smart"
    r = NamingRules.from_settings(S())
    assert r.smart_colon and r.sub("?") == "" and r.sub("/") == ""


def test_names_trimmed_and_control_chars():
    assert render_template("{album}/{title}", {"album": "Vol. 2...", "title": " a\x01b. "}, ".mp3") == "Vol. 2/a_b.mp3"


def test_template_text_still_sanitized():
    assert render_template("{title}: live", {"title": "X"}, "") == "X_ live"


def test_safe_name_for_typed_folder():
    assert safe_name("AC/DC: Live") == "AC+DC - Live"


# ── m3u ────────────────────────────────────────────────────────────────────

def test_m3u_format():
    tracks = [
        {"path": "/m/a.flac", "duration": 191.5, "artist": "Miles", "title": "So What"},
        {"path": "/m/b.mp3", "duration": None, "artist": None, "title": None, "filename": "b.mp3"},
    ]
    out = _m3u(tracks)
    lines = out.splitlines()
    assert lines[0] == "#EXTM3U"
    assert lines[1] == "#EXTINF:191,Miles - So What"
    assert lines[2] == "/m/a.flac"
    assert lines[3] == "#EXTINF:-1,b.mp3"
    assert lines[4] == "/m/b.mp3"


# ── fts query ──────────────────────────────────────────────────────────────

def test_fts_query_prefix_terms():
    assert _fts_query("miles blue", ["title", "year"]) == '{title year} : "miles"* {title year} : "blue"*'
    assert _fts_query("  ") == ""


# ── tagger helpers ─────────────────────────────────────────────────────────

def test_tag_fields_is_canonical():
    assert ALL_SCAN_TAGS is TAG_FIELDS
    assert TAG_FIELDS == [
        "title", "artist", "album", "album_artist", "year",
        "genre", "track_number", "disc_number", "comment", "composer", "bpm",
        "lyrics", "compilation",
    ]


@pytest.mark.parametrize("name,expected", [
    ("a.flac", True), ("a.mp3", True), ("a.m4a", True), ("a.ogg", True),
    ("a.txt", False), ("a", False),
])
def test_is_audio_file(name, expected):
    assert is_audio_file(name) is expected


@pytest.mark.parametrize("name,fmt", [
    ("x.mp3", "mp3"), ("x.flac", "flac"), ("x.m4a", "aac"),
    ("x.ogg", "ogg"), ("x.wav", "unknown"),
])
def test_detect_format(name, fmt):
    assert _detect_format(name) == fmt


def test_render_the_variables_match_lidarr():
    tags = {**SAMPLE, "artist": "The Pogues", "album_artist": "A Tribe Called Quest (US)", "album": "The Album"}
    out = render_template("{artist_the}/{album_artist_the}/{album_the}/{title}", tags, ".mp3")
    assert out == "Pogues, The/Tribe Called Quest, A (US)/Album, The/So What.mp3"
    assert render_template("{artist_the}", {"artist": "Theatre"}, ".mp3") == "Theatre.mp3"   # a word, not an article
    assert render_template("{artist_the}", {"artist": "The"}, ".mp3") == "The.mp3"


def test_render_keeps_dots_in_the_last_part():
    assert render_template("{title}", {"title": "Vol. 2"}, ".mp3") == "Vol. 2.mp3"
