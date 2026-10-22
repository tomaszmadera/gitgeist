import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from gitgeist.features.history import compute_history_features, days_since_last_commit
from gitgeist.ingest.git_history import RawGitHistory, extract_git_history
from gitgeist.schemas.features import GitHistoryFeatures


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


def _git(repo_dir: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_dir, check=True, capture_output=True)


def test_git_history_author_name_with_pipe_keeps_name_and_date(tmp_path: Path) -> None:
    repo_dir = tmp_path / "pipe-author-repo"
    repo_dir.mkdir()
    _git(repo_dir, "init", "-b", "main")
    _git(repo_dir, "config", "user.name", "Ada | Lovelace")
    _git(repo_dir, "config", "user.email", "ada@test.local")
    (repo_dir / "f1.txt").write_text("1")
    _git(repo_dir, "add", ".")
    _git(repo_dir, "commit", "-m", "commit 1")

    raw_history = extract_git_history(repo_dir)

    assert raw_history.authors == ["Ada | Lovelace"]
    assert raw_history.first_commit_date is not None
    assert raw_history.last_commit_date is not None


def test_git_history_file_changes_use_real_paths_for_renames_and_non_ascii(
    tmp_path: Path,
) -> None:
    repo_dir = tmp_path / "rename-repo"
    repo_dir.mkdir()
    _git(repo_dir, "init", "-b", "main")
    _git(repo_dir, "config", "user.name", "Tester")
    _git(repo_dir, "config", "user.email", "tester@test.local")
    (repo_dir / "old.py").write_text("print(1)\n" * 20, encoding="utf-8")
    (repo_dir / "zażółć.py").write_text("print(2)\n", encoding="utf-8")
    _git(repo_dir, "add", ".")
    _git(repo_dir, "commit", "-m", "commit 1")
    _git(repo_dir, "mv", "old.py", "new.py")
    _git(repo_dir, "commit", "-m", "rename")

    raw_history = extract_git_history(repo_dir)

    assert set(raw_history.file_changes) == {"old.py", "new.py", "zażółć.py"}
    assert not any("=>" in path for path in raw_history.file_changes)


def test_git_history_keeps_date_of_commit_with_malformed_zone(tmp_path: Path) -> None:
    # Real case from the requests repository: commit 5e6ecdad stores the zone
    # "+051800", which git prints as "+518:00" in %aI and Python cannot parse.
    repo_dir = tmp_path / "malformed-zone-repo"
    repo_dir.mkdir()
    _git(repo_dir, "init", "-b", "main")
    (repo_dir / "f1.txt").write_text("1")
    _git(repo_dir, "add", ".")
    tree = subprocess.run(
        ["git", "write-tree"], cwd=repo_dir, check=True, capture_output=True, text=True
    ).stdout.strip()
    root_object = (
        f"tree {tree}\n"
        "author Zone Author <zone@test.local> 1293876000 +0000\n"
        "committer Zone Author <zone@test.local> 1293876000 +0000\n"
        "\nroot commit\n"
    )
    root = _hash_commit_object(repo_dir, root_object)
    malformed_object = (
        f"tree {tree}\nparent {root}\n"
        "author Zone Author <zone@test.local> 1313584730 +051800\n"
        "committer Zone Author <zone@test.local> 1313584730 +051800\n"
        "\ncommit with a malformed zone\n"
    )
    head = _hash_commit_object(repo_dir, malformed_object)
    _git(repo_dir, "update-ref", "refs/heads/main", head)

    raw_history = extract_git_history(repo_dir)

    assert raw_history.commit_count == 2
    assert raw_history.first_commit_date == datetime.fromtimestamp(1293876000, timezone.utc)
    assert raw_history.last_commit_date == datetime.fromtimestamp(1313584730, timezone.utc)
    assert compute_history_features(raw_history).repository_age_days == 228


def _hash_commit_object(repo_dir: Path, content: str) -> str:
    # --literally: git refuses to write a commit with a malformed zone otherwise.
    # Bytes, not text=True: text mode would turn "\n" into "\r\n" on Windows.
    return (
        subprocess.run(
            ["git", "hash-object", "-t", "commit", "-w", "--literally", "--stdin"],
            cwd=repo_dir,
            input=content.encode("utf-8"),
            check=True,
            capture_output=True,
        )
        .stdout.decode("ascii")
        .strip()
    )


def test_history_v2_timeline_repo(timeline_repo: Path) -> None:
    raw_history = extract_git_history(timeline_repo)
    features = compute_history_features(raw_history)

    assert len(raw_history.commit_dates) == 5
    assert all(d.tzinfo is not None and d.utcoffset() == timedelta(0) for d in raw_history.commit_dates)
    assert features.timeline_start == "2025-11"
    assert features.timeline == [2, 0, 1, 0, 2]
    assert features.active_months_ratio == 0.6
    assert features.top_author_share == 0.4
    assert features.top3_author_share == 0.8


def test_history_v2_clean_modular(clean_modular_repo: Path) -> None:
    features = compute_history_features(extract_git_history(clean_modular_repo))

    assert features.top_author_share == 0.6667
    assert features.top3_author_share == 1.0
    assert features.timeline == [3]
    assert features.active_months_ratio == 1.0


def test_history_v2_legacy_hotspot_change_share(legacy_chaotic_repo: Path) -> None:
    features = compute_history_features(extract_git_history(legacy_chaotic_repo))

    assert features.hotspots[0].path == "hotspot.py"
    assert features.hotspots[0].change_share == 0.5556


def test_timeline_spans_year_end_and_ignores_log_order() -> None:
    dates = [
        datetime(2026, 1, 3, tzinfo=timezone.utc),
        datetime(2025, 12, 30, tzinfo=timezone.utc),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    ]
    raw = RawGitHistory(
        is_git_repo=True,
        commit_count=3,
        authors=["Solo", "Solo", "Solo"],
        first_commit_date=min(dates),
        last_commit_date=max(dates),
        commit_dates=dates,
    )

    features = compute_history_features(raw)

    assert features.timeline_start == "2025-12"
    assert features.timeline == [1, 2]
    assert features.top_author_share == 1.0
    assert features.top3_author_share == 1.0


def test_days_since_last_commit() -> None:
    history = GitHistoryFeatures(
        is_git_repo=True,
        commit_count=1,
        last_commit_date=datetime(2026, 3, 6, 10, 0, 0, tzinfo=timezone.utc),
    )

    assert days_since_last_commit(history, datetime(2026, 3, 16, 10, 0, 0, tzinfo=timezone.utc)) == 10.0
    assert days_since_last_commit(history, datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)) == 0.0
    assert days_since_last_commit(GitHistoryFeatures(), datetime(2026, 3, 16, tzinfo=timezone.utc)) is None
    with pytest.raises(ValueError):
        days_since_last_commit(history, datetime(2026, 3, 16, 10, 0, 0))


def _assert_v2_history_defaults(features: GitHistoryFeatures) -> None:
    assert features.timeline_start is None
    assert features.timeline == []
    assert features.active_months_ratio == 0.0
    assert features.top_author_share == 0.0
    assert features.top3_author_share == 0.0


def test_history_v2_defaults_without_git(non_git_dir: Path) -> None:
    _assert_v2_history_defaults(compute_history_features(extract_git_history(non_git_dir)))


def test_history_v2_defaults_for_empty_repo(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty-repo"
    empty_dir.mkdir()
    _git(empty_dir, "init", "-b", "main")

    _assert_v2_history_defaults(compute_history_features(extract_git_history(empty_dir)))
