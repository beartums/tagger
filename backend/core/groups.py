"""
Groups: sets of tracks you make, each with optional attributes.

  layout       a folder/file template that overrides the library and default
               layouts for its tracks (core/layout.py)
  quality_off  Quality checks that don't apply to its tracks ("Missing lyrics"
               for Instrumental): they stop being listed or counted

There are none until you make one. A track can be in several groups; if two
of them have different layouts, the track has no layout (LayoutConflict) and
re-filing it is an error until one goes. Membership lives in tggr's DB
(group_members), not the files.
"""
from __future__ import annotations

import re


class LayoutConflict(ValueError):
    pass


def groups() -> list[dict]:
    from api.config import _load
    return [g.model_dump() for g in _load().groups]


def slug(name: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "group"
    out, n = base, 2
    while out in taken:
        out, n = f"{base}-{n}", n + 1
    return out


def members(conn, ids: list[int]) -> dict[int, list[str]]:
    """Each track's group ids (tracks in none are left out)."""
    out: dict[int, list[str]] = {}
    for i in range(0, len(ids), 900):
        chunk = ids[i:i + 900]
        for tid, gid in conn.execute(f"SELECT track_id, group_id FROM group_members WHERE track_id IN "
                                     f"({','.join('?' * len(chunk))}) ORDER BY group_id", chunk):
            out.setdefault(tid, []).append(gid)
    return out


def set_members(conn, ids: list[int], group_id: str, add: bool) -> int:
    if add:
        conn.executemany("INSERT OR IGNORE INTO group_members (track_id, group_id) VALUES (?, ?)",
                         [(i, group_id) for i in ids])
    else:
        for i in range(0, len(ids), 900):
            chunk = ids[i:i + 900]
            conn.execute(f"DELETE FROM group_members WHERE group_id = ? AND track_id IN "
                         f"({','.join('?' * len(chunk))})", [group_id, *chunk])
    return len(ids)


def forget(conn, known: set[str]) -> None:
    """Drop memberships of groups that no longer exist."""
    if known:
        conn.execute(f"DELETE FROM group_members WHERE group_id NOT IN ({','.join('?' * len(known))})", list(known))
    else:
        conn.execute("DELETE FROM group_members")


def _q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def excluded_sql(key: str, gs: list[dict] | None = None) -> str:
    """SQL (over tracks) that is true for tracks a group turns this Quality check off for; '0' if none."""
    off = [g["id"] for g in (gs if gs is not None else groups()) if key in g.get("quality_off", [])]
    if not off:
        return "0"
    return f"tracks.id IN (SELECT track_id FROM group_members WHERE group_id IN ({', '.join(map(_q, off))}))"


def quality_off(gs: list[dict], ids: list[str]) -> list[str]:
    """The Quality checks a track's groups turn off."""
    by = {g["id"]: g for g in gs}
    return sorted({k for gid in ids for k in by.get(gid, {}).get("quality_off", [])})


def layout_for(gs: list[dict], ids: list[str]) -> str | None:
    """The layout a track's groups give it: None if none has one; LayoutConflict if two differ."""
    by = {g["id"]: g for g in gs}
    have = {(by[i].get("layout") or "").strip(): by[i]["name"] for i in ids if i in by and (by[i].get("layout") or "").strip()}
    if len(have) > 1:
        raise LayoutConflict("its groups have different layouts: " + ", ".join(sorted(have.values())))
    return next(iter(have), None)
