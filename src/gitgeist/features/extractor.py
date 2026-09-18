"""Unified repository feature extraction facade."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from gitgeist.features.history import compute_history_features
from gitgeist.features.static import compute_static_features
from gitgeist.ingest.docs_summary import extract_docs_summary
from gitgeist.ingest.git_history import extract_git_history
from gitgeist.ingest.repository import scan_repository_tree
from gitgeist.schemas.features import DocsSummaryFeatures, RepositoryFeatures


def extract_features(repo_path: Path | str) -> RepositoryFeatures:
    """Extract deterministic repository feature profile (Layer 1).

    Args:
        repo_path: Path to repository root directory.

    Returns:
        RepositoryFeatures containing static, git history, and docs features.

    Raises:
        FileNotFoundError: If the specified path does not exist.
        NotADirectoryError: If the specified path is not a directory.
    """
    path = Path(repo_path)
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")

    # 1. Ingest
    scan_res = scan_repository_tree(path)
    git_raw = extract_git_history(path)
    docs_raw = extract_docs_summary(path)

    # 2. Compute features
    static_features = compute_static_features(scan_res)
    history_features = compute_history_features(git_raw)
    docs_features = DocsSummaryFeatures(
        has_readme=docs_raw.has_readme,
        readme_length_chars=docs_raw.readme_length_chars,
        readme_snippet=docs_raw.readme_snippet,
        license_type=docs_raw.license_type,
    )

    return RepositoryFeatures(
        repository_path=str(path),
        extracted_at=datetime.now(timezone.utc),
        static=static_features,
        history=history_features,
        docs=docs_features,
    )
