from pathlib import Path
import pytest
from gitgeist.features.extractor import extract_features
from gitgeist.schemas.features import RepositoryFeatures


def test_extract_features_minimal_repo(minimal_repo: Path) -> None:
    features = extract_features(minimal_repo)
    assert isinstance(features, RepositoryFeatures)
    assert features.repository_path == str(minimal_repo)
    assert features.static.file_count == 2
    assert features.history.is_git_repo is True
    assert features.history.commit_count == 1
    assert features.docs.has_readme is False


def test_extract_features_clean_modular_repo(clean_modular_repo: Path) -> None:
    features = extract_features(clean_modular_repo)
    assert features.static.has_tests is True
    assert features.static.has_documentation is True
    assert features.static.has_ci is True
    assert features.history.commit_count == 3
    assert features.docs.has_readme is True
    assert features.docs.license_type == "MIT"
    assert "Clean Modular Repo" in features.docs.readme_snippet


def test_extract_features_legacy_chaotic_repo(legacy_chaotic_repo: Path) -> None:
    features = extract_features(legacy_chaotic_repo)
    assert features.static.todo_count >= 5
    assert features.history.commit_count == 5
    assert len(features.history.hotspots) > 0


def test_extract_features_non_git_dir(non_git_dir: Path) -> None:
    features = extract_features(non_git_dir)
    assert features.history.is_git_repo is False
    assert features.history.commit_count == 0
    assert features.docs.has_readme is True
    assert features.static.file_count == 2


def test_extract_features_invalid_paths(tmp_path: Path) -> None:
    # Non-existent directory
    missing = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        extract_features(missing)

    # File path instead of directory
    file_path = tmp_path / "file.txt"
    file_path.write_text("not a dir", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        extract_features(file_path)


def test_extract_features_determinism(clean_modular_repo: Path) -> None:
    res1 = extract_features(clean_modular_repo)
    res2 = extract_features(clean_modular_repo)

    assert res1.static == res2.static
    assert res1.history == res2.history
    assert res1.docs == res2.docs


def test_docs_summary_priority_and_lgpl(tmp_path: Path) -> None:
    # Multiple README files: README.md must take precedence over README.txt
    (tmp_path / "README.txt").write_text("Old text readme", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Markdown Readme", encoding="utf-8")

    # LGPL license file containing GNU GENERAL PUBLIC LICENSE phrase
    (tmp_path / "LICENSE").write_text(
        "GNU LESSER GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\nThis version incorporates the terms of the GNU GENERAL PUBLIC LICENSE",
        encoding="utf-8",
    )

    features = extract_features(tmp_path)
    assert features.docs.has_readme is True
    assert features.docs.readme_snippet == "# Markdown Readme"
    assert features.docs.license_type == "LGPL"
