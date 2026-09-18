from datetime import datetime, timezone
import json
from gitgeist.schemas.features import (
    Hotspot,
    StaticFeatures,
    GitHistoryFeatures,
    DocsSummaryFeatures,
    RepositoryFeatures,
)


def test_hotspot_model() -> None:
    h = Hotspot(path="src/main.py", change_count=15)
    assert h.path == "src/main.py"
    assert h.change_count == 15
    data = json.loads(h.model_dump_json())
    assert data["path"] == "src/main.py"
    assert data["change_count"] == 15


def test_static_features_defaults() -> None:
    sf = StaticFeatures()
    assert sf.file_count == 0
    assert sf.directory_count == 0
    assert sf.max_directory_depth == 0
    assert sf.languages == {}
    assert sf.total_size_bytes == 0
    assert sf.avg_file_size_bytes == 0.0
    assert not sf.has_tests
    assert not sf.has_documentation
    assert not sf.has_ci
    assert sf.todo_count == 0


def test_git_history_features_defaults() -> None:
    gh = GitHistoryFeatures()
    assert not gh.is_git_repo
    assert gh.commit_count == 0
    assert gh.unique_authors_count == 0
    assert gh.first_commit_date is None
    assert gh.last_commit_date is None
    assert gh.repository_age_days == 0
    assert gh.velocity == 0.0
    assert gh.total_lines_added == 0
    assert gh.total_lines_deleted == 0
    assert gh.hotspots == []


def test_docs_summary_features_defaults() -> None:
    ds = DocsSummaryFeatures()
    assert not ds.has_readme
    assert ds.readme_length_chars == 0
    assert ds.readme_snippet == ""
    assert ds.license_type is None


def test_repository_features_serialization_roundtrip() -> None:
    now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    rf = RepositoryFeatures(
        repository_path="/test/repo",
        extracted_at=now,
        static=StaticFeatures(
            file_count=5,
            directory_count=2,
            max_directory_depth=2,
            languages={"Python": 4, "Markdown": 1},
            total_size_bytes=1024,
            avg_file_size_bytes=204.8,
            has_tests=True,
            has_documentation=True,
            has_ci=True,
            todo_count=2,
        ),
        history=GitHistoryFeatures(
            is_git_repo=True,
            commit_count=10,
            unique_authors_count=2,
            first_commit_date=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            last_commit_date=now,
            repository_age_days=260,
            velocity=0.27,
            total_lines_added=500,
            total_lines_deleted=100,
            hotspots=[Hotspot(path="src/app.py", change_count=8)],
        ),
        docs=DocsSummaryFeatures(
            has_readme=True,
            readme_length_chars=350,
            readme_snippet="# Test Repo\nDescription",
            license_type="MIT",
        ),
    )

    json_str = rf.model_dump_json()
    data = json.loads(json_str)
    assert data["repository_path"] == "/test/repo"
    assert data["static"]["file_count"] == 5
    assert data["static"]["languages"]["Python"] == 4
    assert data["history"]["hotspots"][0]["path"] == "src/app.py"
    assert data["docs"]["license_type"] == "MIT"

    restored = RepositoryFeatures.model_validate_json(json_str)
    assert restored.repository_path == rf.repository_path
    assert restored.static.file_count == 5
    assert restored.history.commit_count == 10
    assert restored.history.hotspots[0].change_count == 8
    assert restored.docs.has_readme is True
