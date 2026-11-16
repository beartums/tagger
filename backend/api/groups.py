"""Group membership (core/groups.py). The groups themselves are settings (api/config.py)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import groups
from core.database import db

router = APIRouter()


@router.get("")
def list_groups():
    """The groups, with how many tracks are in each."""
    with db() as conn:
        counts = dict(conn.execute("SELECT group_id, COUNT(*) FROM group_members GROUP BY group_id").fetchall())
    return [{**g, "tracks": counts.get(g["id"], 0)} for g in groups.groups()]


class Members(BaseModel):
    track_ids: list[int]
    group_id: str
    add: bool = True


@router.post("/members")
def set_members(req: Members):
    """Put tracks in a group, or take them out (tggr's DB only; no file changes)."""
    if req.group_id not in {g["id"] for g in groups.groups()}:
        raise HTTPException(400, "No such group")
    with db() as conn:
        n = groups.set_members(conn, req.track_ids, req.group_id, req.add)
    return {"changed": n}


class Selection(BaseModel):
    track_ids: list[int]


@router.post("/of")
def groups_of(req: Selection):
    """For each group, how many of these tracks are in it."""
    with db() as conn:
        got = groups.members(conn, req.track_ids)
    counts: dict[str, int] = {}
    for ids in got.values():
        for g in ids:
            counts[g] = counts.get(g, 0) + 1
    return {"total": len(req.track_ids), "in": counts}
