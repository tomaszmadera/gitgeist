import subprocess
from pathlib import Path
import pytest
from gitgeist.features.history import compute_history_features
from gitgeist.ingest.git_history import extract_git_history


def test_git_history_clean_modular(clean_modular_repo: Path) -> None:
    raw_history = extract_git_history(clean_modular_repo)
    features = compute_history_features(raw_history)

    assert features.is_git_repo is True
    assert features.commit_count == 3
    assert features.unique_authors_count == 2
    assert features.first_commit_date is not None
    assert features.last_commit_date is not None
    assert features.last_commit_date >= features.first_commit_date
    assert features.repository_age_days >= 0
    assert features.velocity >= 0.0
    assert features.total_lines_added > 0
    assert features.total_lines_deleted >= 0


def test_git_history_legacy_hotspots(legacy_chaotic_repo: Path) -> None:
    raw_history = extract_git_history(legacy_chaotic_repo)
    features = compute_history_features(raw_history)

    assert features.is_git_repo is True
    assert features.commit_count == 5
    assert len(features.hotspots) > 0
    # hotspot.py should be the top modified file
    top_hotspot = features.hotspots[0]
    assert "hotspot.py" in top_hotspot.path
    assert top_hotspot.change_count >= 4


def test_git_history_non_git_dir(non_git_dir: Path) -> None:
    raw_history = extract_git_history(non_git_dir)
    features = compute_history_features(raw_history)

    assert features.is_git_repo is False
    assert features.commit_count == 0
    assert features.unique_authors_count == 0
    assert features.first_commit_date is None
    assert features.last_commit_date is None
    assert features.hotspots == []


def test_git_history_empty_repo(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty-repo"
    empty_dir.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=empty_dir, check=True, capture_output=True)

    raw_history = extract_git_history(empty_dir)
    features = compute_history_features(raw_history)

    assert features.is_git_repo is True
    assert features.commit_count == 0
    assert features.unique_authors_count == 0
    assert features.first_commit_date is None
    assert features.last_commit_date is None
    assert features.hotspots == []


def test_git_history_subdirectory_not_treated_as_repo_root(clean_modular_repo: Path) -> None:
    sub_dir = clean_modular_repo / "src" / "modular"
    assert sub_dir.is_dir()
    raw_history = extract_git_history(sub_dir)
    assert raw_history.is_git_repo is False


def test_git_history_non_linear_dates(tmp_path: Path) -> None:
    repo_dir = tmp_path / "date-test-repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "tester@test.local"], cwd=repo_dir, check=True, capture_output=True)

    # First commit: March 10
    (repo_dir / "f1.txt").write_text("1")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "commit 1"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        env={
            **subprocess.os.environ,
            "GIT_AUTHOR_DATE": "2026-03-10T12:00:00Z",
            "GIT_COMMITTER_DATE": "2026-03-10T12:00:00Z",
        },
    )

    # Second commit with an EARLIER author date: March 01
    (repo_dir / "f2.txt").write_text("2")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "commit 2"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        env={
            **subprocess.os.environ,
            "GIT_AUTHOR_DATE": "2026-03-01T12:00:00Z",
            "GIT_COMMITTER_DATE": "2026-03-11T12:00:00Z",
        },
    )

    raw_history = extract_git_history(repo_dir)
    features = compute_history_features(raw_history)

    assert features.first_commit_date is not None
    assert features.last_commit_date is not None
    assert features.first_commit_date <= features.last_commit_date
    assert features.first_commit_date.day == 1
    assert features.last_commit_date.day == 10
