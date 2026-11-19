"""
Folders with no tracks left (Clean up → Empty folders): under the chosen
library roots, every folder with no audio file anywhere inside it, listed at
the top-most such level (not inside an album folder: its Scans/ is part of it), with whatever non-track files it still holds.
Deleting moves each to the trash (an empty one is just removed) and prunes
parents left empty; undo puts them back.
"""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from core.config import settings
from core.fileops import prune_empty_dirs
from core.tagger import AUDIO_EXTENSIONS

LISTED = 20   # file names shown per folder


def _audio(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in AUDIO_EXTENSIONS


def find(roots: list[str]) -> list[dict]:
    out = []
    for root in roots:
        root = os.path.normpath(root)
        if not os.path.isdir(root):
            continue
        has_audio: dict[str, bool] = {}
        direct: dict[str, bool] = {}     # audio files right in it (an album folder)
        files: dict[str, list[tuple[str, int]]] = {}
        for d, subdirs, names in os.walk(root, topdown=False):
            mine = [n for n in names if not n.startswith(".tggr-")]
            files[d] = []
            for n in mine:
                try:
                    files[d].append((n, os.path.getsize(os.path.join(d, n))))
                except OSError:
                    files[d].append((n, 0))
            direct[d] = any(_audio(n) for n in mine)
            has_audio[d] = direct[d] or any(has_audio.get(os.path.join(d, s), True) for s in subdirs)
        for d in sorted(has_audio):
            if d == root or has_audio[d]:
                continue
            parent = os.path.dirname(d)
            if parent != root and not has_audio.get(parent, True):
                continue   # listed with its parent
            if direct.get(parent):
                continue   # Scans/, Artwork/ inside an album: part of it
            inside = [(os.path.relpath(os.path.join(x, n), d), sz)
                      for x in files if x == d or x.startswith(d + os.sep) for n, sz in files[x]]
            out.append({"dir": d, "root": root, "count": len(inside), "bytes": sum(sz for _, sz in inside),
                        "files": sorted(n for n, _ in inside)[:LISTED]})
    return out


def delete(dirs: list[str], roots: list[str]) -> tuple[list[dict], list[dict]]:
    """Trash each folder (still trackless); returns (moved [{src, dst}], errors)."""
    roots = [os.path.normpath(r) for r in roots]
    trash = settings.config_dir / "trash"
    moved, errors = [], []
    for d in dirs:
        d = os.path.normpath(d)
        root = next((r for r in roots if d.startswith(r + os.sep)), None)
        if root is None:
            errors.append({"dir": d, "name": Path(d).name, "error": "not inside a library root"})
            continue
        if not os.path.isdir(d):
            errors.append({"dir": d, "name": Path(d).name, "error": "folder not found"})
            continue
        if any(_audio(n) for _, _, ns in os.walk(d) for n in ns):
            errors.append({"dir": d, "name": Path(d).name, "error": "it holds audio files now -- rescan"})
            continue
        try:
            if any(os.scandir(d)):
                trash.mkdir(parents=True, exist_ok=True)
                to = trash / f"folder_{uuid.uuid4().hex[:8]}_{Path(d).name}"
                shutil.move(d, str(to))
                moved.append({"src": d, "dst": str(to)})
            else:
                os.rmdir(d)
                moved.append({"src": d, "dst": None})
        except OSError as exc:
            errors.append({"dir": d, "name": Path(d).name, "error": str(exc)})
            continue
        prune_empty_dirs(os.path.dirname(d), root)
    return moved, errors


def undo(files: list[dict], errors: list[dict]) -> int:
    back = 0
    for f in files:
        src = Path(f["src"])
        if f["dst"] is None:
            src.mkdir(parents=True, exist_ok=True)
            back += 1
            continue
        if src.exists():
            errors.append({"name": src.name, "error": f"something is already at {src}"})
            continue
        if not Path(f["dst"]).exists():
            errors.append({"name": src.name, "error": "no copy left in the trash"})
            continue
        src.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(f["dst"], str(src))
        back += 1
    return back
