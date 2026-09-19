"""Resolved engine version shared by schema defaults and renderers."""

from __future__ import annotations

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


def current_engine_version() -> str:
    """Return the source-tree or installed package version, "unknown" when unresolvable."""
    try:
        with _PYPROJECT_PATH.open("rb") as handle:
            return tomllib.load(handle)["project"]["version"]
    except (OSError, UnicodeError, KeyError, tomllib.TOMLDecodeError):
        pass
    try:
        return version("gitgeist")
    except PackageNotFoundError:
        return "unknown"
