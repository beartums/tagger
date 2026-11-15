"""Environment settings: TGGR_<NAME>, or the older TAGGER_<NAME> (TGGR_ wins when both are set)."""
import os


def env(name: str, default: str = "") -> str:
    v = os.environ.get(f"TGGR_{name}")
    return v if v is not None else os.environ.get(f"TAGGER_{name}", default)
