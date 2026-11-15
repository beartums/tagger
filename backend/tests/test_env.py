from core.env import env


def test_tggr_name_then_the_old_tagger_name(monkeypatch):
    monkeypatch.delenv("TGGR_X", raising=False)
    monkeypatch.delenv("TAGGER_X", raising=False)
    assert env("X", "d") == "d"
    monkeypatch.setenv("TAGGER_X", "old")
    assert env("X", "d") == "old"
    monkeypatch.setenv("TGGR_X", "new")
    assert env("X", "d") == "new"
    monkeypatch.setenv("TGGR_X", "")
    assert env("X", "d") == ""          # set, even if empty, wins
