"""
ReplayGain: rsgain measures the files without writing them; the values are
then staged like any other tag edit (api/tags.py), so they show in Review,
write with the rest and can be undone.
"""
from __future__ import annotations

import os
import shutil
import subprocess


def rg_tool() -> str | None:
    return "rsgain" if shutil.which("rsgain") else None


class RgError(RuntimeError):
    pass


def _gain(v: str) -> str:
    return f"{float(v):.2f} dB"


def _peak(v: str) -> str:
    return f"{float(v):.6f}"


def measure(paths: list[str], album: bool) -> dict[str, dict[str, str]]:
    """
    Gain and peak per file ({path: {rg_track_gain, rg_track_peak, ...}}), plus
    the album's when `album` (the files must be one album). Raises RgError.
    """
    if not rg_tool():
        raise RgError("rsgain isn't installed")
    cmd = ["rsgain", "custom", "-s", "s", "-O", "-q", *(["-a"] if album else []), *paths]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise RgError("rsgain timed out")
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise RgError(msg[-1] if msg else "rsgain failed")
    # Filename, Loudness (LUFS), Gain (dB), Peak, Peak (dB), Peak Type, Clipping Adjustment?
    # One row per file in the order given, then "Album" with -a.
    rows = [line.split("\t") for line in proc.stdout.splitlines()[1:] if line.strip()]
    if len(rows) != len(paths) + (1 if album else 0):
        raise RgError(f"rsgain returned {len(rows)} rows for {len(paths)} files")
    out: dict[str, dict[str, str]] = {}
    for path, row in zip(paths, rows):
        if os.path.basename(row[0]) != os.path.basename(path):
            raise RgError(f"rsgain output out of order at {os.path.basename(path)}")
        out[path] = {"rg_track_gain": _gain(row[2]), "rg_track_peak": _peak(row[3])}
    if album:
        a = rows[-1]
        for v in out.values():
            v.update(rg_album_gain=_gain(a[2]), rg_album_peak=_peak(a[3]))
    return out
