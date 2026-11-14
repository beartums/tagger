"""Lidarr / Navidrome / Music Assistant integrations, with the HTTP side faked."""
import hashlib
import time
import urllib.parse

from core import integrations


def fake(monkeypatch, routes):
    """routes: (method-ish substring) -> (status, body); records each call."""
    calls = []

    def _request(url, *, headers=None, body=None, timeout=15):
        calls.append({"url": url, "headers": headers or {}, "body": body})
        key = body["command"] if body else urllib.parse.urlparse(url).path
        for k, v in routes.items():
            if k in key:
                return v(url, body) if callable(v) else v
        return 404, {}
    monkeypatch.setattr(integrations, "_request", _request)
    return calls


def test_lidarr_naming_maps_colon_ints_and_names(monkeypatch):
    calls = fake(monkeypatch, {"/config/naming": (200, {
        "replaceIllegalCharacters": True, "colonReplacementFormat": 2,
        "artistFolderFormat": "{Artist NameThe}", "standardTrackFormat": "{track:00} {Track Title}"})})
    n = integrations.lidarr_naming("http://lidarr:8686/", "k")
    assert n["colon"] == "space_dash" and n["replace_illegal"] and n["artist_folder_format"] == "{Artist NameThe}"
    assert calls[0]["url"] == "http://lidarr:8686/api/v1/config/naming" and calls[0]["headers"]["X-Api-Key"] == "k"
    fake(monkeypatch, {"/config/naming": (200, {"replaceIllegalCharacters": False, "colonReplacementFormat": "SpaceDashSpace"})})
    assert integrations.lidarr_naming("http://l", "k")["colon"] == "space_dash_space"


def test_lidarr_bad_key(monkeypatch):
    fake(monkeypatch, {"/config/naming": (401, {})})
    r = integrations.test_lidarr("http://l", "bad")
    assert not r["ok"] and "not authorized" in r["message"]


def test_navidrome_token_auth_and_admin_check(monkeypatch):
    def ok(url, body):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        assert q["t"] == hashlib.md5(("pw" + q["s"]).encode()).hexdigest() and q["f"] == "json"
        extra = {"user": {"username": "me", "adminRole": False}} if "getUser" in url else {}
        return 200, {"subsonic-response": {"status": "ok", **extra}}
    fake(monkeypatch, {"/rest/": ok})
    r = integrations.test_navidrome("http://nd", "me", "pw")
    assert not r["ok"] and "admin" in r["message"]


def test_navidrome_wrong_password(monkeypatch):
    fake(monkeypatch, {"/rest/": (200, {"subsonic-response": {"status": "failed", "error": {"code": 40, "message": "Wrong username or password"}}})})
    r = integrations.test_navidrome("http://nd", "me", "x")
    assert not r["ok"] and "Wrong username" in r["message"]


def test_ma_lists_file_providers(monkeypatch):
    calls = fake(monkeypatch, {
        "auth/me": (200, {"username": "admin"}),
        "config/providers": (200, [{"instance_id": "filesystem_local--ab12", "domain": "filesystem_local"},
                                   {"instance_id": "spotify--x", "domain": "spotify"}]),
    })
    r = integrations.test_ma("http://ma:8095", "tok")
    assert r["ok"] and "filesystem_local--ab12" in r["message"] and "spotify" not in r["message"]
    assert calls[0]["url"] == "http://ma:8095/api" and calls[0]["headers"]["Authorization"] == "Bearer tok"


def test_rescan_now_runs_each_configured_app_and_survives_failure(client, monkeypatch):
    client.patch("/api/config", json={
        "navidrome_url": "http://nd", "navidrome_user": "me", "navidrome_password": "pw",
        "ma_url": "http://ma", "ma_token": "tok", "ma_providers": ["filesystem_local--ab12"]})
    calls = fake(monkeypatch, {
        "/rest/startScan": (200, {"subsonic-response": {"status": "ok", "scanStatus": {"scanning": True, "count": 7}}}),
        "music/sync": (401, {}),
    })
    out = client.post("/api/config/rescan").json()
    assert out["navidrome"]["ok"] and "7 tracks" in out["navidrome"]["message"]
    assert not out["music_assistant"]["ok"]
    sync = next(c for c in calls if c["body"])
    assert sync["body"]["args"] == {"providers": ["filesystem_local--ab12"]}
    assert client.get("/api/config").json()["rescans"]["navidrome"]["ok"]


def _timed(monkeypatch, mode, wait):
    runs = []
    monkeypatch.setattr(integrations, "_timing", lambda: (mode, wait))
    monkeypatch.setattr(integrations, "rescan_now", lambda *a: runs.append(time.monotonic()))
    return runs


def test_quiet_waits_for_the_last_change(monkeypatch):
    runs = _timed(monkeypatch, "quiet", 0.15)
    start = time.monotonic()
    for _ in range(4):
        integrations.changed()
        time.sleep(0.1)              # each change restarts the wait
    time.sleep(0.3)
    assert len(runs) == 1 and runs[0] - start >= 0.4      # last change at 0.3 s + 0.15


def test_delay_does_not_restart(monkeypatch):
    runs = _timed(monkeypatch, "delay", 0.15)
    start = time.monotonic()
    for _ in range(4):
        integrations.changed()
        time.sleep(0.1)
    time.sleep(0.3)
    # due 0.15 s after the first change; the changes after it start a second one
    assert len(runs) == 2 and runs[0] - start < 0.3


def test_off_never_rescans(monkeypatch):
    runs = _timed(monkeypatch, "off", 0.01)
    integrations.changed()
    time.sleep(0.1)
    assert runs == [] and integrations.pending() is None


def test_timing_settings(client):
    r = client.patch("/api/config", json={"rescan_mode": "delay", "rescan_delay_seconds": 45}).json()
    assert r["rescan_mode"] == "delay"
    assert integrations.timing(type("S", (), {"rescan_mode": "quiet", "rescan_delay_seconds": 45, "rescan_quiet_minutes": 3})) == ("quiet", 180.0)
    assert client.patch("/api/config", json={"rescan_mode": "sometimes"}).status_code == 400
    assert client.patch("/api/config", json={"rescan_quiet_minutes": 0}).status_code == 400


def test_source_test_needs_settings(client):
    r = client.post("/api/config/test/lidarr", json={"value": ""}).json()
    assert not r["ok"] and "URL" in r["message"]
    assert client.get("/api/config/lidarr-naming").status_code == 400


def test_navidrome_targets(tmp_path):
    lib = tmp_path / "music"
    (lib / "Shared" / "Pogues, The" / "Rum").mkdir(parents=True)
    (lib / "Shared" / "AC+DC").mkdir(parents=True)
    m = {str(lib / "Shared"): "1:", str(lib / "Libraries"): "2:Side"}
    t = integrations.navidrome_targets({
        str(lib / "Shared/Pogues, The/Rum"), str(lib / "Shared/Pogues, The"),     # one covers the other
        str(lib / "Shared/AC_DC"),                                                # moved away: nearest existing
    }, m)
    assert sorted(t) == ["1:"]        # AC_DC is gone, so its target is the library root, covering the rest
    (lib / "Libraries" / "Cast" / "Show").mkdir(parents=True)
    assert integrations.navidrome_targets({str(lib / "Libraries/Cast/Show"), str(lib / "Shared/AC+DC")}, m) == \
        ["1:AC+DC", "2:Side/Cast/Show"]
    assert integrations.navidrome_targets({"/elsewhere/x"}, m) is None          # outside the mapping: full scan
    assert integrations.navidrome_targets({str(lib / "Shared/AC+DC")}, {}) is None


def test_navidrome_targets_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(integrations, "MAX_TARGETS", 2)
    for n in "abc":
        (tmp_path / n).mkdir()
    dirs = {str(tmp_path / n) for n in "abc"}
    assert integrations.navidrome_targets(dirs, {str(tmp_path): "1:"}) is None


def test_ma_providers_for():
    m = {"/music/Shared": "filesystem_local--shared", "/music/Libraries/Cast": "filesystem_local--cast"}
    assert integrations.ma_providers_for({"/music/Shared/A/B"}, m, []) == ["filesystem_local--shared"]
    assert integrations.ma_providers_for({"/music/Shared/A", "/music/Libraries/Cast/X"}, m, []) == \
        ["filesystem_local--cast", "filesystem_local--shared"]
    assert integrations.ma_providers_for({"/music/Other"}, m, ["all-mine"]) == ["all-mine"]
    assert integrations.ma_providers_for(None, m, []) == []


def test_targeted_rescan_sends_targets(client, monkeypatch, tmp_path):
    (tmp_path / "Shared" / "X").mkdir(parents=True)
    client.patch("/api/config", json={
        "navidrome_url": "http://nd", "navidrome_user": "me", "navidrome_password": "pw",
        "navidrome_folders": {str(tmp_path / "Shared"): "1:"}})
    calls = fake(monkeypatch, {"/rest/startScan": (200, {"subsonic-response": {"status": "ok"}})})
    out = integrations.rescan_now({str(tmp_path / "Shared" / "X")})
    q = urllib.parse.parse_qs(urllib.parse.urlparse(calls[0]["url"]).query)
    assert q["target"] == ["1:X"] and "1 folder" in out["navidrome"]["message"]
    assert client.patch("/api/config", json={"navidrome_folders": {"/music": "Shared"}}).status_code == 400


def test_changed_collects_folders(monkeypatch, tmp_path):
    got = []
    monkeypatch.setattr(integrations, "_timing", lambda: ("quiet", 0.05))
    monkeypatch.setattr(integrations, "rescan_now", lambda dirs=None: got.append(dirs))
    (tmp_path / "a").mkdir()
    integrations.changed(tmp_path / "a" / "01 x.flac")
    integrations.changed(tmp_path / "a", tmp_path / "b" / "new")
    time.sleep(0.2)
    assert got == [{str(tmp_path / "a"), str(tmp_path / "b")}]
