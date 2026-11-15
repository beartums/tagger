import os
from pathlib import Path

from pydantic import BaseModel
from core.env import env


class Settings(BaseModel):
    music_dir: Path = Path(env("MUSIC_DIR", "/music"))
    config_dir: Path = Path(env("CONFIG_DIR", "/config"))
    acoustid_api_key: str = os.environ.get("ACOUSTID_API_KEY", "")
    # Colon-separated root patterns (globs allowed); see core/fileops.py.
    library_roots: list[str] = [
        r for r in env("LIBRARY_ROOTS", "").split(":") if r
    ]

    @property
    def db_path(self) -> Path:
        return self.config_dir / "library.db"

    @property
    def settings_file(self) -> Path:
        return self.config_dir / "settings.json"


settings = Settings()
