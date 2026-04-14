"""Runtime config: paths, defaults, persistence."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import os

SETTINGS_PATH = Path(__file__).resolve().parent / "settings.json"
DEFAULT_WORKSPACE = Path(r"C:\Users\MattL\LocalProjects")

# Detect Ollama host. Windows installs sometimes bind 11435 rather than the
# default 11434. Set OLLAMA_HOST env var to override.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST") or "http://localhost:11435"
if not OLLAMA_HOST.startswith(("http://", "https://")):
    OLLAMA_HOST = f"http://{OLLAMA_HOST}"


@dataclass
class Settings:
    workspace: str = str(DEFAULT_WORKSPACE)
    default_mode: str = "auto"
    destructive_confirm: bool = True
    mempalace_enabled: bool = False
    history: list[dict] = field(default_factory=list)

    @classmethod
    def load(cls) -> "Settings":
        if SETTINGS_PATH.exists():
            try:
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    def save(self) -> None:
        SETTINGS_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
