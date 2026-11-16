"""
Layouts: the folder/file template a track is expected to follow, and the
path it would have under it. A track uses the first layout set of: its
groups' (core/groups.py; two different ones = a conflict, no layout), its
library's, the standard one (the rename template). Only libraries checked in
Settings → Libraries are compared.

The Quality panel's "Not in layout" view lists tracks whose path differs from
their library's layout. Fixing them is always deliberate -- a staged re-file
of chosen tracks, reviewed and undoable -- never automatic.

Rename-on-save and re-file use the same order, checked library or not.
"""
from __future__ import annotations

import os
from pathlib import Path

from core.fileops import root_for
from core.naming import NamingRules, render_template

# Columns the SQL function takes, in order (see sql_function); the last is
# the track's group ids, comma-joined.
COLUMNS = ("path", "title", "artist", "album", "album_artist", "year", "genre",
           "track_number", "disc_number", "group_ids")
GROUP_IDS_SQL = "(SELECT group_concat(group_id) FROM group_members WHERE track_id = tracks.id)"
SQL_ARGS = ", ".join(COLUMNS[:-1]) + ", " + GROUP_IDS_SQL


class Layouts:
    """Settings read once: which layout a track uses, and whether it's compared."""

    def __init__(self):
        from api.config import _load, get_library_roots
        s = _load()
        self.standard = s.rename_template.strip()
        self.libraries = {os.path.normpath(k): v.strip() for k, v in s.library_templates.items() if v.strip()}
        self.groups = [g.model_dump() for g in s.groups]
        self.checked = {os.path.normpath(p) for p in s.layout_libraries}
        self.roots = get_library_roots()
        self.rules = NamingRules.from_settings(s)

    def template(self, path: str, group_ids: list[str] | None = None) -> str:
        """Its groups' layout, else its library's, else the standard one. Raises LayoutConflict."""
        from core.groups import layout_for
        mine = layout_for(self.groups, group_ids or [])
        if mine:
            return mine
        root = root_for(path, self.roots)
        return (self.libraries.get(str(root)) if root else None) or self.standard

    def expected(self, row, group_ids: list[str] | None = None) -> str | None:
        """Where row belongs, if its library is checked; None otherwise, when it can't render, or its groups conflict."""
        from core.groups import LayoutConflict
        root = root_for(row["path"], self.roots) if self.checked else None
        if root is None or str(root) not in self.checked:
            return None
        try:
            template = self.template(row["path"], group_ids)
        except LayoutConflict:
            return None
        if not template:
            return None
        try:
            return str(root / render_template(template, dict(row), Path(row["path"]).suffix, self.rules))
        except (KeyError, ValueError, IndexError):
            return None


def template_for(conn, row) -> str:
    """The layout row's track uses (see Layouts.template). Raises LayoutConflict."""
    from core import groups
    return Layouts().template(row["path"], groups.members(conn, [row["id"]]).get(row["id"], []))


def sql_function():
    """
    layout_path(path, title, ..., group_id) for SQL (columns as in COLUMNS):
    the path the layout gives, or NULL. Settings are read on first use, once
    per connection.
    """
    cache: dict = {}

    def layout_path(*values):
        if not cache:
            cache["layouts"] = Layouts()
        row = dict(zip(COLUMNS, values))
        ids = row.pop("group_ids")
        return cache["layouts"].expected(row, ids.split(",") if ids else [])

    return layout_path


def conflict_function():
    """group_layout_conflict(group ids, comma-joined) for SQL: 1 when two of them have different layouts."""
    cache: dict = {}

    def group_layout_conflict(ids):
        if not ids or "," not in ids:
            return 0
        from core.groups import LayoutConflict, layout_for
        if "groups" not in cache:
            cache["groups"] = Layouts().groups
        try:
            layout_for(cache["groups"], ids.split(","))
            return 0
        except LayoutConflict:
            return 1

    return group_layout_conflict
