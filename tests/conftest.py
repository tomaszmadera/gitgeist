"""Pytest fixtures for Gitgeist tests."""

import os
from pathlib import Path
import pytest

from tests.fixtures.builder import (
    create_clean_modular_repo,
    create_legacy_chaotic_repo,
    create_minimal_repo,
    create_timeline_repo,
    create_wide_repo,
)


# Variables a test process (and git or Python child processes) needs to run.
# None of them holds a credential.
_KEPT_ENV_VARS = frozenset(
    {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "SYSTEMDRIVE",
        "WINDIR",
        "COMSPEC",
        "TEMP",
        "TMP",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "PYTHONPATH",
        "VIRTUAL_ENV",
    }
)
_KEPT_ENV_PREFIXES = ("PYTEST_",)


@pytest.fixture(autouse=True)
def isolated_environ(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
    """Give every test a minimal environment instead of the real one.

    The real process environment can hold API keys. Every other variable is
    removed for the test, so no test, no child process it starts, and no failure
    output can read or print it. HOME and USERPROFILE point to an empty temp
    directory, and GITGEIST_ENV_FILE points to a missing file, so no real user
    or project .env file is loaded. monkeypatch restores everything afterwards.
    """
    home = tmp_path_factory.mktemp("home")
    for name in list(os.environ):
        upper = name.upper()
        if upper not in _KEPT_ENV_VARS and not upper.startswith(_KEPT_ENV_PREFIXES):
            monkeypatch.delenv(name)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("GITGEIST_ENV_FILE", str(home / "no-such-file.env"))


@pytest.fixture
def minimal_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "minimal-repo"
    return create_minimal_repo(repo_path)


@pytest.fixture
def clean_modular_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "clean-modular-repo"
    return create_clean_modular_repo(repo_path)


@pytest.fixture
def legacy_chaotic_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "legacy-chaotic-repo"
    return create_legacy_chaotic_repo(repo_path)


@pytest.fixture
def timeline_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "timeline-repo"
    return create_timeline_repo(repo_path)


@pytest.fixture
def wide_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "wide-repo"
    return create_wide_repo(repo_path)


@pytest.fixture
def non_git_dir(tmp_path: Path) -> Path:
    plain_dir = tmp_path / "plain-directory"
    plain_dir.mkdir(parents=True, exist_ok=True)
    (plain_dir / "sample.py").write_text("# TODO: implement\nprint('hello')\n", encoding="utf-8")
    (plain_dir / "README.md").write_text("# Plain directory\nNo git here.", encoding="utf-8")
    return plain_dir
