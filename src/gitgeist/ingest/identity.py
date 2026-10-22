"""Repository identity seed from the root commits.

The seed must not change when the repository gets new commits, so it is
derived from the root commits (all of them, sorted) instead of HEAD. A path
that is not a Git repository root with commits uses its directory name.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from gitgeist.schemas.identity import IdentitySeed

GIT_TIMEOUT_SECONDS = 30


def _git(repo_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )


def _is_repository_root_with_commits(repo_path: Path) -> bool:
    """Same rule as ingest/git_history.py: a repository root that has a HEAD commit."""
    try:
        toplevel = _git(repo_path, "rev-parse", "--show-toplevel")
        if toplevel.returncode != 0 or not toplevel.stdout.strip():
            return False
        if Path(toplevel.stdout.strip()).resolve() != repo_path.resolve():
            return False
        return _git(repo_path, "rev-parse", "--verify", "HEAD").returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_identity_seed(repo_path: Path) -> IdentitySeed:
    """Return the identity seed of the repository at ``repo_path``.

    Raises:
        RuntimeError: If ``repo_path`` is a repository root with commits but
            listing its root commits fails.
    """
    if not _is_repository_root_with_commits(repo_path):
        return IdentitySeed(
            identity_seed=_sha256(repo_path.resolve().name),
            source="directory-name",
        )

    try:
        result = _git(repo_path, "rev-list", "--max-parents=0", "HEAD")
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"cannot list root commits of {repo_path}: {exc}") from exc
    roots = sorted(line.strip() for line in result.stdout.splitlines() if line.strip())
    if result.returncode != 0 or not roots:
        raise RuntimeError(
            f"cannot list root commits of {repo_path}: {result.stderr.strip() or 'no output'}"
        )
    return IdentitySeed(
        identity_seed=_sha256("\n".join(roots)),
        source="root-commits",
        root_commits=roots,
    )
