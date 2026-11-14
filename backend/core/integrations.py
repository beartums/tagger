"""
Other music apps Tagger talks to (Settings → Sources → Integrations), each
optional:

- Lidarr: read its file-naming choices (GET /api/v1/config/naming) so
  Settings → Layouts → Characters in names can copy them.
- Navidrome: Subsonic startScan after files change (needs an admin user).
- Music Assistant: POST /api {"command": "music/sync"} after files change
  (a long-lived token of an admin user; providers = instance ids, blank = all).

Rescans are debounced: every write calls changed(), and the rescan fires
RESCAN_DELAY seconds after the last one, so a 500-track write is one rescan.
Checked against upstream source 2026-11-14 (Lidarr develop, Navidrome master,
Music Assistant stable).
"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets as _secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("tagger.integrations")

RESCAN_DELAY = 30.0
_UA = "tagger (https://github.com/beartums/tagger)"

# Lidarr's ColonReplacementFormat (an int in the API) -> core.naming.COLONS.
LIDARR_COLONS = {0: "delete", 1: "dash", 2: "space_dash", 3: "space_dash_space", 4: "smart"}

# Last rescan per app, shown in Settings: {"at": epoch, "ok": bool, "message": str}.
last: dict[str, dict] = {}
_timer: threading.Timer | None = None
_lock = threading.Lock()


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
    status, body = _request(f"{_base(url)}/rest/{method}?{urllib.parse.urlencode(q)}")
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
    return {"ok": True, "message": f"Navidrome: signed in as {user}"}


def rescan_navidrome(url: str, user: str, password: str) -> str:
    r = _subsonic(url, user, password, "startScan")
    s = r.get("scanStatus") or {}
    return "scan started" + (f" ({s['count']} tracks known)" if "count" in s else "")


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

def changed() -> None:
    """Files changed: (re)start the countdown to one rescan of each configured app."""
    global _timer
    with _lock:
        if _timer is not None:
            _timer.cancel()
        _timer = threading.Timer(RESCAN_DELAY, rescan_now)
        _timer.daemon = True
        _timer.start()


def rescan_now() -> dict:
    """Ask every configured app to rescan; records and returns each result."""
    from api.config import _load
    s = _load()
    jobs = []
    if s.navidrome_url and s.navidrome_user and s.navidrome_password:
        jobs.append(("navidrome", lambda: rescan_navidrome(s.navidrome_url, s.navidrome_user, s.navidrome_password)))
    if s.ma_url and s.ma_token:
        jobs.append(("music_assistant", lambda: rescan_ma(s.ma_url, s.ma_token, s.ma_providers)))
    for name, fn in jobs:
        try:
            last[name] = {"at": time.time(), "ok": True, "message": fn()}
        except Exception as exc:     # never let a rescan break a write
            last[name] = {"at": time.time(), "ok": False, "message": str(exc)}
            logger.warning("rescan %s failed: %s", name, exc)
    return dict(last)
