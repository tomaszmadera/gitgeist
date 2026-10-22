"""Pytest fixtures for Gitgeist tests."""

from pathlib import Path
import pytest

from tests.fixtures.builder import (
    create_clean_modular_repo,
    create_legacy_chaotic_repo,
    create_minimal_repo,
    create_timeline_repo,
    create_wide_repo,
)


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
