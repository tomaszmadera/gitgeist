"""Environment loading helpers for Gitgeist."""

from __future__ import annotations

import os
from pathlib import Path

ENV_FILE_NAME = ".env"
ENV_OVERRIDE_VAR = "GITGEIST_ENV_FILE"
CONFIG_HOME_ENV = "XDG_CONFIG_HOME"
CONFIG_DIR_NAME = "gitgeist"


def find_dotenv(start_dir: Path | None = None) -> Path | None:
    """Find a .env file by searching start_dir and its parent directories.

    Search stops when a .env file is found, when a .git boundary is crossed
    (after checking that directory), or when reaching the root directory.
    """
    current = (start_dir or Path.cwd()).resolve()
    while True:
        candidate = current / ENV_FILE_NAME
        if candidate.is_file():
            return candidate
        if (current / ".git").exists():
            break
        if current.parent == current:
            break
        current = current.parent
    return None


def parse_dotenv(content: str) -> dict[str, str]:
    """Parse key-value pairs from .env formatted content.

    Rules:
    - Empty lines and lines starting with '#' are ignored.
    - Each valid line must contain a '=' delimiter.
    - Keys are stripped of whitespace.
    - Values are stripped of whitespace; matching surrounding single or double
      quotes are stripped.
    - An optional 'export ' prefix is supported and stripped.
    """
    values: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, raw_val = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        val = raw_val.strip()
        if len(val) >= 2 and (
            (val.startswith('"') and val.endswith('"'))
            or (val.startswith("'") and val.endswith("'"))
        ):
            val = val[1:-1]
        values[key] = val
    return values


def user_env_file() -> Path:
    """Return the user-level .env file path (~/.config/gitgeist/.env, XDG-aware)."""
    config_home = os.environ.get(CONFIG_HOME_ENV)
    base = Path(config_home) if config_home else Path.home() / ".config"
    return base / CONFIG_DIR_NAME / ENV_FILE_NAME


def load_dotenv(path: Path | str | None = None, override: bool = False) -> bool:
    """Load variables from a .env file into os.environ.

    Args:
        path: Path to the .env file. If None, checks GITGEIST_ENV_FILE or find_dotenv().
        override: If True, overwrite existing environment variables.
            Default is False (existing env vars take precedence).

    Returns:
        True if at least one .env file was found and loaded, False otherwise.

    When *path* is None, two sources are consulted in order, both only
    filling variables that are not set yet (unless override=True):

    1. The local file: ``GITGEIST_ENV_FILE`` if set, otherwise the nearest
       ``.env`` found from the current directory upward (``find_dotenv()``).
    2. The user-level file: ``$XDG_CONFIG_HOME/gitgeist/.env``
       (default ``~/.config/gitgeist/.env``) — global fallback that works
       regardless of the current working directory.

    Precedence: process environment > local .env > user-level .env.
    Empty values in a .env file are skipped and do not shadow a later source.
    """
    if path is not None:
        return _load_env_file(Path(path), override=override)

    loaded = False
    target = os.environ.get(ENV_OVERRIDE_VAR)
    env_path = Path(target) if target is not None else find_dotenv()
    if env_path is not None and _load_env_file(env_path, override=override):
        loaded = True
    if _load_env_file(user_env_file(), override=override):
        loaded = True
    return loaded


def _load_env_file(env_path: Path, override: bool = False) -> bool:
    if not env_path.is_file():
        return False

    try:
        content = env_path.read_text(encoding="utf-8")
    except OSError:
        return False

    parsed = parse_dotenv(content)
    for key, value in parsed.items():
        # An empty value (for example a copied .env.example) means "not set here",
        # so it must not shadow a lower-priority source such as the user-level file.
        if value == "":
            continue
        if override or key not in os.environ:
            os.environ[key] = value
    return True
