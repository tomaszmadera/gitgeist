"""Synthetic Git repository fixtures generator for Gitgeist testing."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _run_git(repo_dir: Path, args: list[str], env: dict[str, str] | None = None) -> None:
    git_env = os.environ.copy()
    git_env["GIT_AUTHOR_NAME"] = "Geist Author"
    git_env["GIT_AUTHOR_EMAIL"] = "author@gitgeist.local"
    git_env["GIT_COMMITTER_NAME"] = "Geist Author"
    git_env["GIT_COMMITTER_EMAIL"] = "author@gitgeist.local"
    if env:
        git_env.update(env)
    res = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        env=git_env,
        check=True,
    )


def create_minimal_repo(target_dir: Path) -> Path:
    """Create a minimal repository with 2 files and 1 commit, no tests, no docs."""
    target_dir.mkdir(parents=True, exist_ok=True)
    _run_git(target_dir, ["init", "-b", "main"])
    _run_git(target_dir, ["config", "user.name", "Minimal Author"])
    _run_git(target_dir, ["config", "user.email", "minimal@test.local"])

    (target_dir / "main.py").write_text("def main():\n    print('minimal')\n", encoding="utf-8")
    (target_dir / "helper.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    _run_git(target_dir, ["add", "."])
    _run_git(
        target_dir,
        ["commit", "-m", "Initial minimal commit"],
        env={
            "GIT_AUTHOR_DATE": "2026-01-01T10:00:00Z",
            "GIT_COMMITTER_DATE": "2026-01-01T10:00:00Z",
        },
    )
    return target_dir


def create_clean_modular_repo(target_dir: Path) -> Path:
    """Create a well-structured modular repository with tests, docs, CI, license, and multiple commits."""
    target_dir.mkdir(parents=True, exist_ok=True)
    _run_git(target_dir, ["init", "-b", "main"])
    _run_git(target_dir, ["config", "user.name", "Clean Dev"])
    _run_git(target_dir, ["config", "user.email", "dev@clean.local"])

    # Commit 1: Project structure and docs
    (target_dir / "README.md").write_text(
        "# Clean Modular Repo\n\nA well-structured repository demonstrating clean architecture.\n\n## Overview\nThis project contains modular components with unit tests.\n",
        encoding="utf-8",
    )
    (target_dir / "LICENSE").write_text(
        "MIT License\n\nCopyright (c) 2026 Clean Modular Team\n\nPermission is hereby granted, free of charge...",
        encoding="utf-8",
    )
    docs_dir = target_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "index.md").write_text("# Documentation\nArchitecture description.", encoding="utf-8")

    _run_git(target_dir, ["add", "."])
    _run_git(
        target_dir,
        ["commit", "-m", "chore: initialize project documentation and license"],
        env={
            "GIT_AUTHOR_DATE": "2026-02-01T10:00:00Z",
            "GIT_COMMITTER_DATE": "2026-02-01T10:00:00Z",
        },
    )

    # Commit 2: Source code and CI
    src_dir = target_dir / "src" / "modular"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "__init__.py").write_text('__version__ = "1.0.0"\n', encoding="utf-8")
    (src_dir / "core.py").write_text("class Engine:\n    def run(self) -> bool:\n        return True\n", encoding="utf-8")

    ci_dir = target_dir / ".github" / "workflows"
    ci_dir.mkdir(parents=True, exist_ok=True)
    (ci_dir / "ci.yml").write_text("name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n", encoding="utf-8")

    _run_git(target_dir, ["add", "."])
    _run_git(
        target_dir,
        ["commit", "-m", "feat: add core engine and CI workflow"],
        env={
            "GIT_AUTHOR_NAME": "Modular Architect",
            "GIT_AUTHOR_EMAIL": "arch@clean.local",
            "GIT_COMMITTER_NAME": "Modular Architect",
            "GIT_COMMITTER_EMAIL": "arch@clean.local",
            "GIT_AUTHOR_DATE": "2026-02-10T12:00:00Z",
            "GIT_COMMITTER_DATE": "2026-02-10T12:00:00Z",
        },
    )

    # Commit 3: Tests
    tests_dir = target_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "test_core.py").write_text(
        "from modular.core import Engine\n\ndef test_engine():\n    assert Engine().run() is True\n",
        encoding="utf-8",
    )

    _run_git(target_dir, ["add", "."])
    _run_git(
        target_dir,
        ["commit", "-m", "test: add unit tests for engine"],
        env={
            "GIT_AUTHOR_DATE": "2026-02-15T15:00:00Z",
            "GIT_COMMITTER_DATE": "2026-02-15T15:00:00Z",
        },
    )

    return target_dir


def create_legacy_chaotic_repo(target_dir: Path) -> Path:
    """Create a chaotic repository with deep nesting, mixed languages, TODO comments, and hotspots."""
    target_dir.mkdir(parents=True, exist_ok=True)
    _run_git(target_dir, ["init", "-b", "main"])
    _run_git(target_dir, ["config", "user.name", "Legacy Hacker"])
    _run_git(target_dir, ["config", "user.email", "hacker@legacy.local"])

    # Deep directory nesting with TODOs
    deep_path = target_dir / "legacy" / "deep" / "nested" / "subsystem" / "core"
    deep_path.mkdir(parents=True, exist_ok=True)
    (deep_path / "legacy_handler.py").write_text(
        "# TODO: refactor this entire subsystem\n# FIXME: security flaw here\ndef process():\n    pass\n",
        encoding="utf-8",
    )

    # Mixed languages and scripts
    (target_dir / "script.sh").write_text("#!/bin/sh\n# TODO: replace with python\necho 'running legacy script'\n", encoding="utf-8")
    (target_dir / "web.js").write_text("// TODO: migrate to TypeScript\nconsole.log('legacy');\n", encoding="utf-8")
    (target_dir / "data.json").write_text('{"legacy": true, "items": [1, 2, 3]}\n', encoding="utf-8")

    # Hotspot file
    hotspot = target_dir / "hotspot.py"
    hotspot.write_text("# Initial hotspot version\nx = 1\n", encoding="utf-8")

    _run_git(target_dir, ["add", "."])
    _run_git(
        target_dir,
        ["commit", "-m", "initial chaotic commit"],
        env={
            "GIT_AUTHOR_DATE": "2026-03-01T08:00:00Z",
            "GIT_COMMITTER_DATE": "2026-03-01T08:00:00Z",
        },
    )

    # Modifications to create churn and hotspot
    for i in range(2, 6):
        hotspot.write_text(f"# Hotspot iteration {i}\n# FIXME: bug {i}\nx = {i}\ny = {i * 2}\n", encoding="utf-8")
        _run_git(target_dir, ["add", "hotspot.py"])
        _run_git(
            target_dir,
            ["commit", "-m", f"fix: update hotspot logic v{i}"],
            env={
                "GIT_AUTHOR_DATE": f"2026-03-0{i}T10:00:00Z",
                "GIT_COMMITTER_DATE": f"2026-03-0{i}T10:00:00Z",
            },
        )

    return target_dir
