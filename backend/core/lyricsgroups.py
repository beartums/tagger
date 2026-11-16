"""
How a track's lyrics are looked up on LRCLIB: one list of queries for every
track, tried in order until LRCLIB has something.

Each query is a title / artist / album template over the track's tags (plus
the cleaned-up variables below). The first ones are the plain ones; the
rest are what cast albums and soundtracks need (no artist: title + album,
the cast album's own name), tried only when the plain ones find nothing.
Groups (core/groups.py) no longer change the lookup: a group that turns
"Missing lyrics" off just stops its tracks being looked up or listed.
"""
from __future__ import annotations

import re
import string

from core.multivalue import split_values

QUERIES = [
    {"title": "{title}", "artist": "{artist}", "album": "{album}"},
    {"title": "{title_base}", "artist": "{artist_first}", "album": ""},
    {"title": "{title_base}", "artist": "{artist_first}", "album": "{album}"},
    {"title": "{title_base}", "artist": "{album_artist_first}", "album": ""},
    {"title": "{title_base}", "artist": "", "album": "{album_base}"},
]
LOOKUP = {"id": "lyrics", "name": "Lyrics", "skip": False, "queries": QUERIES}

FIELDS = ("title", "artist", "album")
VARIABLES = ("title", "artist", "album", "album_artist", "year", "title_base", "album_base",
             "artist_first", "album_artist_first")

# Trailing "(Original Broadway Cast Recording)", "[Live]", ' (From "Frozen")',
# " - From the Motion Picture …": what LRCLIB's names usually lack.
_TAIL = re.compile(r'(\s*(\([^)]*\)|\[[^\]]*\]))+\s*$|\s+-\s+(from|theme from)\b.*$', re.IGNORECASE)


def _base(s: str) -> str:
    out = _TAIL.sub("", s or "").strip()
    return out or (s or "").strip()


def variables(track) -> dict:
    t = dict(track)
    v = {k: (t.get(k) or "").strip() if isinstance(t.get(k), str) else str(t.get(k) or "") for k in
         ("title", "artist", "album", "album_artist", "year")}
    v["title_base"], v["album_base"] = _base(v["title"]), _base(v["album"])
    v["artist_first"] = (split_values(v["artist"]) or [""])[0]
    v["album_artist_first"] = (split_values(v["album_artist"]) or [""])[0]
    return v


_VAR = re.compile(r"\{(\w+)\}")


def _render(template: str, v: dict) -> str:
    """Fill {variables}; anything else is literal text (a typed-in album name)."""
    return " ".join(_VAR.sub(lambda m: v.get(m.group(1), m.group(0)), template).split())


def unknown(template: str) -> str | None:
    """The first {name} in template that isn't a variable, if any."""
    return next((m.group(0) for m in _VAR.finditer(template) if m.group(1) not in VARIABLES), None)


_STAMP = re.compile(r"\[\d+:\d\d")


def kind(text: str | None) -> str:
    """'synced' (timestamped lines), 'plain', or 'none' -- what a track already has."""
    if not (text or "").strip():
        return "none"
    return "synced" if _STAMP.search(text) else "plain"


def upgrade(existing: str | None, res: dict) -> dict:
    """
    A lookup for a track that already has plain lyrics: only synced is worth
    offering. Anything else keeps what it has ('has_plain', no lyrics).
    """
    if kind(existing) != "plain" or res["status"] == "synced":
        return res
    return {**res, "status": "has_plain", "lyrics": None}


def check(template: str) -> None:
    """Raise ValueError naming the problem if template uses anything but VARIABLES."""
    for _, name, spec, conv in string.Formatter().parse(template):
        if name is None:
            continue
        if name not in VARIABLES or spec or conv:
            raise ValueError(f"unknown variable {{{name}}}" if name not in VARIABLES
                             else f"{{{name}}} takes no format")


def queries(group: dict, track) -> list[dict]:
    """The group's queries rendered for track: distinct, each with a title."""
    v, out = variables(track), []
    for q in group.get("queries", []):
        r = {f: _render(q.get(f, ""), v) for f in FIELDS}
        if r["title"] and (r["artist"] or r["album"]) and r not in out:
            out.append(r)
    return out


def resolver():
    """group_for(path, _) -> the one lookup (kept for callers that used to pick a group)."""
    return lambda path, assigned=None: LOOKUP


def lookups(conn, ids: list[int]) -> dict[int, dict]:
    out = {}
    for i in range(0, len(ids), 900):
        chunk = ids[i:i + 900]
        for r in conn.execute(f"SELECT * FROM lyrics_lookups WHERE track_id IN "
                              f"({','.join('?' * len(chunk))})", chunk):
            out[r["track_id"]] = {"status": r["status"], "at": r["at"]}
    return out


def record(conn, track_id: int, status: str, at: float) -> None:
    conn.execute("INSERT INTO lyrics_lookups (track_id, status, at) VALUES (?, ?, ?) "
                 "ON CONFLICT(track_id) DO UPDATE SET status = excluded.status, at = excluded.at",
                 (track_id, status, at))


def look_up(track, group: dict, prefer: str = "synced") -> dict:
    """
    Try the group's queries in order: {'status', 'lyrics', 'query'}. Status is
    synced | plain | instrumental | missing | untagged; 'query' is the one that
    answered (or None).
    """
    from core import lyrics as lrclib
    qs = queries(group, track)
    if not qs:
        return {"status": "untagged", "lyrics": None, "query": None}
    t = dict(track)
    for q in qs:
        hit = (lrclib.fetch(q["title"], q["artist"], q["album"] or None, t.get("duration")) if q["artist"]
               else lrclib.fetch_by_album(q["title"], q["album"], t.get("duration")))
        if not hit:
            continue
        if hit["instrumental"] and not (hit["synced"] or hit["plain"]):
            return {"status": "instrumental", "lyrics": None, "query": q}
        text = (hit["synced"] or hit["plain"]) if prefer == "synced" else (hit["plain"] or hit["synced"])
        return {"status": "synced" if text == hit["synced"] else "plain", "lyrics": text, "query": q}
    return {"status": "missing", "lyrics": None, "query": None}
