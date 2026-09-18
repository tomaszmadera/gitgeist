"""Git commit log and history ingestor."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

GIT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class RawGitHistory:
    """Raw history metrics extracted from Git."""

    is_git_repo: bool
    commit_count: int = 0
    authors: list[str] = field(default_factory=list)
    first_commit_date: datetime | None = None
    last_commit_date: datetime | None = None
    total_added: int = 0
    total_deleted: int = 0
    file_changes: dict[str, int] = field(default_factory=dict)


def _parse_iso_date(date_str: str) -> datetime | None:
    """Parse ISO 8601 date string returned by git log."""
    try:
        return datetime.fromisoformat(date_str.strip())
    except (ValueError, TypeError):
        return None


def extract_git_history(repo_path: Path) -> RawGitHistory:
    """Extract Git commit history, authors, churn and hotspots deterministically."""
    # Check if repo_path itself is the root of a Git repository
    try:
        toplevel = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
        if toplevel.returncode != 0 or not toplevel.stdout.strip():
            return RawGitHistory(is_git_repo=False)

        resolved_toplevel = Path(toplevel.stdout.strip()).resolve()
        if resolved_toplevel != repo_path.resolve():
            # repo_path is a subdirectory inside another repository, not a standalone repo root
            return RawGitHistory(is_git_repo=False)
    except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
        return RawGitHistory(is_git_repo=False)

    # Check if repository has commits (HEAD exists)
    try:
        head_check = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
        if head_check.returncode != 0:
            # Freshly initialized repository without commits
            return RawGitHistory(is_git_repo=True, commit_count=0)
    except (OSError, subprocess.TimeoutExpired):
        return RawGitHistory(is_git_repo=True, commit_count=0)

    # Extract commits and authors
    try:
        log_res = subprocess.run(
            ["git", "log", "--format=%H|%an|%aI"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return RawGitHistory(is_git_repo=True, commit_count=0)

    if log_res.returncode != 0 or not log_res.stdout.strip():
        return RawGitHistory(is_git_repo=True, commit_count=0)

    lines = [line.strip() for line in log_res.stdout.splitlines() if line.strip()]
    if not lines:
        return RawGitHistory(is_git_repo=True, commit_count=0)

    commit_count = len(lines)
    authors: list[str] = []
    dates: list[datetime] = []

    for line in lines:
        parts = line.split("|", 2)
        if len(parts) >= 3:
            authors.append(parts[1].strip())
            dt = _parse_iso_date(parts[2])
            if dt:
                dates.append(dt)

    first_commit_date = min(dates) if dates else None
    last_commit_date = max(dates) if dates else None

    # Extract numstat for churn and hotspots
    total_added = 0
    total_deleted = 0
    file_changes: dict[str, int] = {}

    try:
        stat_res = subprocess.run(
            ["git", "log", "--numstat", "--format="],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
        if stat_res.returncode == 0 and stat_res.stdout:
            for stat_line in stat_res.stdout.splitlines():
                stat_line = stat_line.strip()
                if not stat_line:
                    continue
                parts = stat_line.split(None, 2)
                if len(parts) == 3:
                    added_str, deleted_str, path = parts
                    if added_str.isdigit():
                        total_added += int(added_str)
                    if deleted_str.isdigit():
                        total_deleted += int(deleted_str)
                    norm_path = path.replace("\\", "/")
                    file_changes[norm_path] = file_changes.get(norm_path, 0) + 1
    except (OSError, subprocess.TimeoutExpired):
        pass

    return RawGitHistory(
        is_git_repo=True,
        commit_count=commit_count,
        authors=authors,
        first_commit_date=first_commit_date,
        last_commit_date=last_commit_date,
        total_added=total_added,
        total_deleted=total_deleted,
        file_changes=file_changes,
    )
