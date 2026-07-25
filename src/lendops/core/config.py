"""Tiny JSON-backed configuration with safe defaults.

LendOps is deliberately zero-config for laymen: the only persisted
preferences are the theme and the start page. A corrupt or missing file
silently falls back to defaults — the app must always start.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import config_path

logger = logging.getLogger(__name__)

_VALID_THEMES = ("dark", "light")


@dataclass
class AppConfig:
    theme: str = "dark"
    start_page: str = "home"


def load_config(path: Path | None = None) -> AppConfig:
    file_path = path if path is not None else config_path()
    if not file_path.is_file():
        return AppConfig()
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        config = AppConfig(**{k: v for k, v in raw.items() if k in AppConfig.__annotations__})
    except Exception as exc:  # noqa: BLE001 - a bad config must never block startup
        logger.warning("ignoring unreadable config %s: %s", file_path, exc)
        return AppConfig()
    if config.theme not in _VALID_THEMES:
        config.theme = "dark"
    return config


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    file_path = path if path is not None else config_path()
    tmp = file_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
    tmp.replace(file_path)
    return file_path
