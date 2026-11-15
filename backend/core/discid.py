"""
MusicBrainz disc IDs and tables of contents, and working them out for a rip
that wasn't tagged with them (from the tracks' exact lengths).

A ripped CD track is a whole number of 588-sample sectors (1/75 s at 44.1 kHz),
and cdparanoia rips track N from its start to track N+1's start. So for a plain
audio CD the lengths give the table of contents exactly: track 1 at sector 150
(the 2 s lead-in), each next track where the last ended, the lead-out after
the last. Wrong for a disc with audio hidden before track 1 or a data track
after the audio (enhanced CD): MusicBrainz won't know such an ID.
"""
from __future__ import annotations

import base64
import hashlib

SECTOR = 588          # samples per CD sector at 44.1 kHz


def disc_id(first: int, last: int, leadout: int, offsets: list[int]) -> str:
    """https://musicbrainz.org/doc/Disc_ID_Calculation"""
    h = hashlib.sha1()
    h.update(f"{first:02X}{last:02X}{leadout:08X}".encode())
    for i in range(99):
        h.update(f"{offsets[i] if i < len(offsets) else 0:08X}".encode())
    return base64.b64encode(h.digest()).decode().translate(str.maketrans("+/=", "._-"))


def toc_string(first: int, last: int, leadout: int, offsets: list[int]) -> str:
    return " ".join(str(x) for x in (first, last, leadout, *offsets))


def parse_toc(toc: str) -> tuple[int, int, int, list[int]] | None:
    try:
        n = [int(x) for x in toc.split()]
    except ValueError:
        return None
    if len(n) < 4 or len(n) != 3 + n[1] - n[0] + 1:
        return None
    return n[0], n[1], n[2], n[3:]


def from_lengths(tracks: list[dict]) -> tuple[str, str] | str:
    """
    (disc ID, toc) for one disc's tracks, or why it can't be done. Each track
    needs track_number, duration, sample_rate, channels and format.
    """
    try:
        rows = sorted(tracks, key=lambda t: int(str(t["track_number"]).split("/")[0]))
        nums = [int(str(t["track_number"]).split("/")[0]) for t in rows]
    except (TypeError, ValueError):
        return "a track has no track number"
    if nums != list(range(1, len(rows) + 1)):
        return "track numbers aren't 1 to N"
    if len(rows) > 99:
        return "more than 99 tracks"
    sectors = []
    for t in rows:
        if (t.get("format") or "").lower() not in ("flac", "wav", "aiff", "alac"):
            return "not lossless"
        if t.get("sample_rate") != 44100 or t.get("channels") not in (2, None):
            return "not CD audio (44.1 kHz stereo)"
        samples = round((t.get("duration") or 0) * 44100)
        if not samples or samples % SECTOR:
            return "a track isn't whole CD sectors long (not an exact rip)"
        sectors.append(samples // SECTOR)
    offsets = [150]
    for s in sectors[:-1]:
        offsets.append(offsets[-1] + s)
    leadout = offsets[-1] + sectors[-1]
    first, last = 1, len(rows)
    return disc_id(first, last, leadout, offsets), toc_string(first, last, leadout, offsets)
