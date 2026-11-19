"""
An album's other files -- cover art, .cue, rip logs, booklets, Scans/, lyrics
sidecars -- when its tracks move. Planned per source folder: the same plan is
shown in Move to layout's preview and carried out when the moves are written
(core/staging.apply).

Whole album = every track in the folder moves. Then, by default, everything
else in it follows the tracks to their (one) destination folder and the old
folder is pruned. A per-track sidecar (same name as a track, e.g. .lrc) is
renamed with its track. A disc folder (CD1, Disc 2) counts with its parent: the
parent's own files follow once all its disc folders have.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from core.fileops import IMAGE_EXTS
from core.tagger import ANY_AUDIO

DISC = re.compile(r"^(cd|dis[ck])[\s._-]*\d+$", re.I)
STALE_REFS = {".cue", ".m3u", ".m3u8"}   # name tracks by file name


def _audio(p: Path) -> bool:
    return p.suffix.lower() in ANY_AUDIO


def _has_audio(d: Path) -> bool:
    try:
        return any(_audio(p) for p in d.rglob("*") if p.is_file())
    except OSError:
        return True


def _files(p: Path) -> int:
    return 1 if p.is_file() else sum(1 for q in p.rglob("*") if q.is_file())


@dataclass
class FolderPlan:
    src: str
    whole: bool                      # every track in it moves
    dest: str | None                 # where its other files go (None: tracks scatter)
    items: list[tuple[str, str | None]] = field(default_factory=list)   # (from, to); to None = the trash
    files: int = 0                   # files in items, subfolders counted inside
    refs: bool = False               # a .cue / .m3u whose file names go stale
    parent_of_discs: bool = False

    def describe(self) -> dict:
        return {"dir": self.src, "whole": self.whole, "dest": self.dest, "files": self.files,
                "items": [{"name": Path(a).name, "dir": Path(a).is_dir(),
                           "files": _files(Path(a)) if Path(a).exists() else 0, "to": b,
                           "trash": b is None} for a, b in self.items],
                "refs": self.refs, "discs": self.parent_of_discs}


def _contents(d: Path) -> list[Path]:
    """d's non-audio entries: files, and subfolders holding no audio."""
    try:
        entries = list(d.iterdir())
    except OSError:
        return []
    out = []
    for e in entries:
        if e.name.startswith(".tggr-"):
            continue
        if e.is_dir():
            if not _has_audio(e):
                out.append(e)
        elif not _audio(e):
            out.append(e)
    return out


def plan(moves: dict[str, str], remaining: dict[str, int], occupied: set[str] = frozenset()) -> list[FolderPlan]:
    """
    moves: old path -> new path for the tracks moving now. remaining: folder ->
    tracks that stay in it. occupied: destination folders already holding
    another album's tracks -- cover art doesn't join those (it goes to the
    trash); the rest still follows.
    """
    by_dir: dict[Path, dict[str, str]] = {}
    for old, new in moves.items():
        by_dir.setdefault(Path(old).parent, {})[old] = new
    plans: list[FolderPlan] = []
    for d, mv in sorted(by_dir.items()):
        dests = {Path(n).parent for n in mv.values()}
        dest = next(iter(dests)) if len(dests) == 1 else None
        p = FolderPlan(str(d), whole=remaining.get(str(d), 0) == 0, dest=str(dest) if dest else None)
        olds = sorted(((Path(o).stem, Path(n)) for o, n in mv.items()), key=lambda x: -len(x[0]))
        for e in _contents(d):
            # A track's sidecar: "01 Song.lrc", "01 Song.en.lrc" -> renamed with it.
            side = next(((st, n) for st, n in olds if e.is_file() and e.name.startswith(st + ".")), None)
            if side:
                st, n = side
                p.items.append((str(e), str(n.parent / (n.stem + e.name[len(st):]))))
            elif dest is not None:
                art = e.is_file() and e.suffix.lower() in IMAGE_EXTS and str(dest) in occupied
                p.items.append((str(e), None if art else str(dest / e.name)))
            else:
                continue
            p.files += _files(e)
            p.refs = p.refs or e.suffix.lower() in STALE_REFS
        plans.append(p)

    # A parent of disc folders: its own files follow once every disc folder has.
    whole = {Path(p.src) for p in plans if p.whole}
    for parent in sorted({d.parent for d in whole if DISC.match(d.name)}):
        try:
            subs = [e for e in parent.iterdir() if e.is_dir() and _has_audio(e)]
        except OSError:
            continue
        if remaining.get(str(parent), 0) or any(not DISC.match(s.name) or s not in whole for s in subs):
            continue
        # Where the album went: the tracks' folder, or its parent for disc folders.
        albums = {(q.parent if DISC.match(q.name) else q)
                  for q in (Path(n).parent for o, n in moves.items() if Path(o).parent.parent == parent)}
        if len(albums) != 1:
            continue
        common = albums.pop()
        p = FolderPlan(str(parent), whole=True, dest=str(common), parent_of_discs=True)
        for e in _contents(parent):
            p.items.append((str(e), str(common / e.name)))
            p.files += _files(e)
            p.refs = p.refs or e.suffix.lower() in STALE_REFS
        if p.items:
            plans.append(p)
    return plans


def plan_delete(folders: set[str], remaining: dict[str, int]) -> list[FolderPlan]:
    """
    The folders whose tracks are being deleted: each one's other files (all
    to the trash, items' `to` None), whole = no track stays. A parent of disc
    folders comes last, once every one of its disc folders is whole.
    """
    plans = []
    for d in sorted(folders):
        p = FolderPlan(d, whole=remaining.get(d, 0) == 0, dest=None)
        for e in _contents(Path(d)):
            p.items.append((str(e), None))
            p.files += _files(e)
        plans.append(p)
    whole = {Path(p.src) for p in plans if p.whole}
    for parent in sorted({d.parent for d in whole if DISC.match(d.name)}):
        try:
            subs = [e for e in parent.iterdir() if e.is_dir() and _has_audio(e)]
        except OSError:
            continue
        if remaining.get(str(parent), 0) or any(not DISC.match(s.name) or s not in whole for s in subs):
            continue
        p = FolderPlan(str(parent), whole=True, dest=None, parent_of_discs=True)
        for e in _contents(parent):
            p.items.append((str(e), None))
            p.files += _files(e)
        plans.append(p)
    return plans
