"""Application data locations.

All user data (settings, exported reports) lives under one per-user
folder: ``%LOCALAPPDATA%/LendOps`` on Windows, ``~/.lendops`` elsewhere.
Set the ``LENDOPS_HOME`` environment variable to relocate everything.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def app_data_dir() -> Path:
    """Per-user writable data directory (created on first call)."""
    override = os.environ.get("LENDOPS_HOME")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LendOps"
    else:
        base = Path.home() / ".lendops"
    base.mkdir(parents=True, exist_ok=True)
    return base


def reports_dir() -> Path:
    path = app_data_dir() / "reports"
    path.mkdir(exist_ok=True)
    return path


def config_path() -> Path:
    return app_data_dir() / "config.json"
