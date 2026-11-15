"""
Other music apps Tagger talks to (Settings → Sources → Integrations), each
optional:

- Lidarr: read its file-naming choices (GET /api/v1/config/naming) so
  Settings → Layouts → Characters in names can copy them.
- Navidrome: Subsonic startScan after files change (needs an admin user).
- Music Assistant: POST /api {"command": "music/sync"} after files change
  (a long-lived token of an admin user; providers = instance ids, blank = all).

Every write calls changed(); when the rescan fires is a setting (rescan_mode):
"off"; "delay" = rescan_delay_seconds after the first change, however many
follow (they ride along); "quiet" = rescan_quiet_minutes after the LAST change,
each change restarting the wait. Either way a 500-track write is one rescan.
Checked against upstream source 2026-11-14 (Lidarr develop, Navidrome master,
Music Assistant stable).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import posixpath
import secrets as _secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("tagger.integrations")

RESCAN_MODES = ("off", "delay", "quiet")
_SETTINGS_TTL = 10.0     # changed() runs per file written: don't re-read settings each time
_UA = "tagger (https://github.com/beartums/tagger)"

# Lidarr's ColonReplacementFormat (an int in the API) -> core.naming.COLONS.
LIDARR_COLONS = {0: "delete", 1: "dash", 2: "space_dash", 3: "space_dash_space", 4: "smart"}

# Last rescan per app, shown in Settings: {"at": epoch, "ok": bool, "message": str}.
last: dict[str, dict] = {}
_timer: threading.Timer | None = None
_lock = threading.Lock()
_cached: tuple[float, str, float] | None = None     # (read at, mode, wait seconds)
pending_since: float | None = None                  # first change not yet rescanned
due_at: float | None = None
_dirs: set[str] = set()                             # folders changed since the last rescan

# More folders than this in one rescan: Navidrome scans everything instead.
MAX_TARGETS = 50


def _request(url: str, *, headers: dict | None = None, body: dict | None = None, timeout: float = 15) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": _UA, **({"Content-Type": "application/json"} if data else {}), **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw, status = e.read(), e.code
    except (urllib.error.URLError, OSError) as e:
        return 0, {"error": str(getattr(e, "reason", e))}
    try:
        return status, json.loads(raw or b"null")
    except ValueError:
        return status, {"text": raw[:200].decode(errors="replace")}


def _base(url: str) -> str:
    return url.strip().rstrip("/")


# ── Lidarr ─────────────────────────────────────────────────────────────────

def lidarr_naming(url: str, key: str) -> dict:
    """Lidarr's naming config, in Tagger's terms. Raises ValueError with a readable message."""
    status, body = _request(f"{_base(url)}/api/v1/config/naming", headers={"X-Api-Key": key})
    if status != 200 or not isinstance(body, dict):
        raise ValueError(_why("Lidarr", status, body))
    colon = body.get("colonReplacementFormat")
    return {
        "replace_illegal": bool(body.get("replaceIllegalCharacters", True)),
        "colon": _lidarr_colon(colon),
        "artist_folder_format": body.get("artistFolderFormat") or "",
        "track_format": body.get("standardTrackFormat") or "",
        "multi_disc_track_format": body.get("multiDiscTrackFormat") or "",
    }


def _lidarr_colon(v) -> str:
    """An int per the API; a name ("SpaceDashSpace") accepted too."""
    if isinstance(v, int):
        return LIDARR_COLONS.get(v, "smart")
    names = {"delete": "delete", "dash": "dash", "spacedash": "space_dash",
             "spacedashspace": "space_dash_space", "smart": "smart"}
    return names.get(str(v).lower(), "smart")


def test_lidarr(url: str, key: str) -> dict:
    try:
        n = lidarr_naming(url, key)
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    on = "replaced" if n["replace_illegal"] else "removed"
    return {"ok": True, "message": f"Lidarr: illegal characters {on}, colons {n['colon'].replace('_', ' ')}"}


# ── Navidrome (Subsonic API) ───────────────────────────────────────────────

def _subsonic(url: str, user: str, password: str, method: str, **params) -> dict:
    salt = _secrets.token_hex(6)
    q = {"u": user, "t": hashlib.md5((password + salt).encode()).hexdigest(), "s": salt,
         "v": "1.16.1", "c": "tagger", "f": "json", **params}
    status, body = _request(f"{_base(url)}/rest/{method}?{urllib.parse.urlencode(q, doseq=True)}")
    r = body.get("subsonic-response") if isinstance(body, dict) else None
    if status != 200 or not isinstance(r, dict):
        raise ValueError(_why("Navidrome", status, body))
    if r.get("status") != "ok":
        raise ValueError(f"Navidrome: {(r.get('error') or {}).get('message') or 'request failed'}")
    return r


def test_navidrome(url: str, user: str, password: str) -> dict:
    try:
        _subsonic(url, user, password, "ping")
        u = _subsonic(url, user, password, "getUser", username=user).get("user") or {}
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    if u and not u.get("adminRole"):
        return {"ok": False, "message": f"Navidrome: signed in as {user}, but rescans need an admin user"}
    try:
        libs = ", ".join(f"{l['id']} = {l['name']}" for l in navidrome_libraries(url, user, password))
    except ValueError:
        libs = ""
    return {"ok": True, "message": f"Navidrome: signed in as {user}" + (f"; libraries: {libs}" if libs else "")}


def navidrome_libraries(url: str, user: str, password: str) -> list[dict]:
    """[{id, name}]: getMusicFolders ids are Navidrome's library ids (the target prefix)."""
    r = _subsonic(url, user, password, "getMusicFolders")
    return [{"id": f.get("id"), "name": f.get("name")} for f in (r.get("musicFolders") or {}).get("musicFolder") or []]


def rescan_navidrome(url: str, user: str, password: str, targets: list[str] | None = None) -> str:
    """Scan everything, or just the given "libraryID:folder" targets (and below)."""
    r = _subsonic(url, user, password, "startScan", **({"target": targets} if targets else {}))
    s = r.get("scanStatus") or {}
    what = f"{len(targets)} folder{'s' if len(targets) != 1 else ''}" if targets else "full scan"
    return f"scan started ({what})" + (f", {s['count']} tracks known" if "count" in s else "")


def _longest(path: str, mapping: dict[str, str]) -> tuple[str, str] | None:
    """The mapping entry whose Tagger folder contains path (deepest wins)."""
    best = None
    for root, v in mapping.items():
        root = os.path.normpath(root)
        if path == root or path.startswith(root.rstrip("/") + "/"):
            if best is None or len(root) > len(best[0]):
                best = (root, v)
    return best


def _existing(path: str, stop: str) -> str:
    """path, or its nearest folder that still exists (a moved-away folder is gone)."""
    while path != stop and not os.path.isdir(path):
        path = os.path.dirname(path)
    return path


def _outermost(paths) -> list[str]:
    """Drop folders inside another one in the set: a target scans its subfolders."""
    out: list[str] = []
    for p in sorted(set(paths)):
        if not any(p == o or p.startswith(o.rstrip("/") + "/") for o in out):
            out.append(p)
    return out


def navidrome_targets(dirs: set[str], mapping: dict[str, str]) -> list[str] | None:
    """
    "libraryID:folder" targets for the changed folders, or None = scan everything
    (no mapping, a folder outside it, or more than MAX_TARGETS). mapping:
    Tagger folder -> "libraryID:folder in that library" ("1:" = the library root).
    """
    if not mapping or not dirs:
        return None
    found = []
    for d in dirs:
        hit = _longest(os.path.normpath(d), mapping)
        if hit is None:
            return None
        root, spec = hit
        lib, _, prefix = spec.partition(":")
        found.append((lib.strip(), root, _existing(os.path.normpath(d), root), prefix.strip().strip("/")))
    targets = []
    for lib, root, d, prefix in found:
        rel = os.path.relpath(d, root)
        rel = "" if rel == "." else rel.replace(os.sep, "/")
        targets.append(f"{lib}:{posixpath.join(prefix, rel) if prefix and rel else prefix or rel}")
    # outermost per library: "1:A" covers "1:A/B"; "1:" covers all of library 1
    by_lib: dict[str, list[str]] = {}
    for t in targets:
        lib, _, folder = t.partition(":")
        by_lib.setdefault(lib, []).append(folder)
    out = []
    for lib, folders in sorted(by_lib.items()):
        if "" in folders:
            out.append(f"{lib}:")
        else:
            out += [f"{lib}:{f}" for f in _outermost(folders)]
    return out if len(out) <= MAX_TARGETS else None


# ── Music Assistant ────────────────────────────────────────────────────────

def _ma(url: str, token: str, command: str, **args):
    status, body = _request(f"{_base(url)}/api", headers={"Authorization": f"Bearer {token}"},
                            body={"message_id": "tagger", "command": command, "args": args})
    if status != 200:
        raise ValueError(_why("Music Assistant", status, body))
    return body


def test_ma(url: str, token: str) -> dict:
    try:
        me = _ma(url, token, "auth/me")
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    me = me if isinstance(me, dict) else {}
    who = f"signed in as {me['username']}" if me.get("username") else "token accepted"
    try:
        provs = _ma(url, token, "config/providers", provider_type="music")
    except ValueError as exc:
        return {"ok": False, "message": f"Music Assistant: {who}, but can't list providers ({exc}) -- syncing needs an admin's token"}
    ids = [p.get("instance_id") for p in provs or [] if isinstance(p, dict) and str(p.get("domain", "")).startswith("filesystem")]
    found = f"; file providers: {', '.join(ids)}" if ids else "; no file providers found"
    return {"ok": True, "message": f"Music Assistant: {who}{found}"}


def ma_providers_for(dirs: set[str] | None, mapping: dict[str, str], default: list[str]) -> list[str]:
    """
    Providers whose folders changed (mapping: Tagger folder -> provider instance id);
    the default list (blank = all) when there's no mapping, no folder list, or a
    changed folder outside the mapping.
    """
    if not mapping or not dirs:
        return default
    hits = [_longest(os.path.normpath(d), mapping) for d in dirs]
    if any(h is None for h in hits):
        return default
    return sorted({h[1] for h in hits})


def rescan_ma(url: str, token: str, providers: list[str]) -> str:
    _ma(url, token, "music/sync", providers=providers or None)
    return "sync started" + (f" ({', '.join(providers)})" if providers else "")


def _why(app: str, status: int, body) -> str:
    if status == 0:
        return f"{app}: can't connect ({(body or {}).get('error', '?')})"
    if status in (401, 403):
        return f"{app}: not authorized (HTTP {status}) -- check the key/token"
    return f"{app}: HTTP {status}"


# ── Rescan after writes ────────────────────────────────────────────────────

def timing(s) -> tuple[str, float]:
    """(mode, wait in seconds) from settings."""
    mode = s.rescan_mode if s.rescan_mode in RESCAN_MODES else "quiet"
    wait = s.rescan_delay_seconds if mode == "delay" else s.rescan_quiet_minutes * 60
    return mode, max(float(wait), 1.0)


def _timing() -> tuple[str, float]:
    global _cached
    now = time.monotonic()
    if _cached is None or now - _cached[0] > _SETTINGS_TTL:
        from api.config import _load
        _cached = (now, *timing(_load()))
    return _cached[1], _cached[2]


def cancel_pending() -> set[str]:
    """Stop a waiting rescan; returns the folders it would have covered."""
    global _timer, pending_since, due_at
    with _lock:
        if _timer is not None:
            _timer.cancel()
        _timer = pending_since = due_at = None
        dirs = set(_dirs)
        _dirs.clear()
        return dirs


def settings_changed() -> None:
    """Saved settings: read the timing afresh; "off" cancels a pending rescan."""
    global _cached
    _cached = None
    if _timing()[0] == "off":
        cancel_pending()


def changed(*paths) -> None:
    """
    Files changed (paths: the files or folders touched; their folders are what
    get rescanned): start -- or, waiting for quiet, restart -- the countdown
    to one rescan.
    """
    global _timer, pending_since, due_at
    mode, wait = _timing()
    if mode == "off":
        return
    with _lock:
        for p in paths:
            p = os.path.normpath(str(p))
            _dirs.add(p if os.path.isdir(p) else os.path.dirname(p))
        if _timer is not None:
            if mode == "delay":
                return              # already due; this change rides along
            _timer.cancel()
        pending_since = pending_since or time.time()
        due_at = time.time() + wait
        _timer = threading.Timer(wait, _fire)
        _timer.daemon = True
        _timer.start()


def _fire() -> None:
    global _timer, pending_since, due_at
    with _lock:
        _timer = pending_since = due_at = None
        dirs = set(_dirs)
        _dirs.clear()
    rescan_now(dirs)


def pending() -> dict | None:
    """A rescan waiting to happen, for Settings: {since, due} (epoch seconds)."""
    return {"since": pending_since, "due": due_at, "folders": len(_dirs)} if due_at else None


def rescan_now(dirs: set[str] | None = None) -> dict:
    """
    Ask every configured app to rescan -- just the changed folders where it
    can (dirs; None = everything). Records and returns each result.
    """
    from api.config import _load
    s = _load()
    jobs = []
    if s.navidrome_url and s.navidrome_user and s.navidrome_password:
        targets = navidrome_targets(dirs or set(), s.navidrome_folders) if dirs else None
        jobs.append(("navidrome", lambda: rescan_navidrome(s.navidrome_url, s.navidrome_user, s.navidrome_password, targets)))
    if s.ma_url and s.ma_token:
        providers = ma_providers_for(dirs, s.ma_folders, s.ma_providers)
        jobs.append(("music_assistant", lambda: rescan_ma(s.ma_url, s.ma_token, providers)))
    for name, fn in jobs:
        try:
            last[name] = {"at": time.time(), "ok": True, "message": fn()}
        except Exception as exc:     # never let a rescan break a write
            last[name] = {"at": time.time(), "ok": False, "message": str(exc)}
            logger.warning("rescan %s failed: %s", name, exc)
    return dict(last)
