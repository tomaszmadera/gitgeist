"""Tests for structure features: directory masses and hotspot concentration."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitgeist.features.extractor import extract_features
from gitgeist.features.structure import compute_structure_features
from gitgeist.ingest.git_history import RawGitHistory, extract_git_history
from gitgeist.ingest.repository import scan_repository_tree
from gitgeist.schemas.features import StructureFeatures
from tests.fixtures.builder import create_emptied_repo


def _structure(repo: Path) -> StructureFeatures:
    return compute_structure_features(scan_repository_tree(repo), extract_git_history(repo))


def _mass(structure: StructureFeatures, name: str, is_merged: bool = False):
    return next(m for m in structure.masses if m.name == name and m.is_merged is is_merged)


def test_masses_minimal(minimal_repo: Path) -> None:
    structure = _structure(minimal_repo)

    assert [m.name for m in structure.masses] == ["."]
    root = structure.masses[0]
    assert root.file_share == 1.0
    assert root.churn_share == 1.0
    assert root.dominant_language == "Python"


def test_masses_clean_modular(clean_modular_repo: Path) -> None:
    structure = _structure(clean_modular_repo)

    assert [m.name for m in structure.masses] == [".", "src", "tests", ".github", "docs"]
    assert _mass(structure, "tests").test_file_share == 1.0
    assert _mass(structure, ".").dominant_language == "Markdown"
    assert structure.hotspot_concentration == 0.0


def test_masses_legacy_chaotic(legacy_chaotic_repo: Path) -> None:
    structure = _structure(legacy_chaotic_repo)

    assert [(m.name, m.file_share, m.churn_share) for m in structure.masses] == [
        (".", 0.8, 0.8889),
        ("legacy", 0.2, 0.1111),
    ]


def test_masses_wide(wide_repo: Path) -> None:
    structure = _structure(wide_repo)

    assert [(m.name, m.is_merged) for m in structure.masses] == [
        *((name, False) for name in "abcdefg"),
        ("other", True),
    ]
    other = _mass(structure, "other", is_merged=True)
    assert other.file_count == 7
    assert other.churn_share == 0.1429
    a = _mass(structure, "a")
    assert a.file_share == 0.1786
    assert a.churn_share == 0.2381
    assert structure.hotspot_concentration == 0.0754


def test_hotspots_wide_have_share_and_mass(wide_repo: Path) -> None:
    hotspots = extract_features(wide_repo).history.hotspots

    assert (hotspots[0].path, hotspots[0].change_count, hotspots[0].change_share, hotspots[0].mass) == (
        "a/m0.py",
        6,
        0.0952,
        "a",
    )
    assert (hotspots[1].path, hotspots[1].change_count, hotspots[1].change_share, hotspots[1].mass) == (
        "old/x.py",
        2,
        0.0317,
        "other",
    )


def test_real_other_directory_and_merged_other(tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()
    for i in range(5):
        (other / f"o{i}.py").write_text("x\n", encoding="utf-8")
    for i in range(1, 9):
        directory = tmp_path / f"d{i}"
        directory.mkdir()
        (directory / "f.py").write_text("x\n", encoding="utf-8")

    structure = compute_structure_features(scan_repository_tree(tmp_path), RawGitHistory(is_git_repo=False))

    assert [(m.name, m.is_merged) for m in structure.masses] == [
        ("other", False),
        *((f"d{i}", False) for i in range(1, 7)),
        ("other", True),
    ]
    assert _mass(structure, "other").file_count == 5
    assert _mass(structure, "other", is_merged=True).file_count == 2


def test_top_level_directory_without_files_is_not_a_mass(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x\n", encoding="utf-8")

    features = extract_features(tmp_path)

    assert [m.name for m in features.structure.masses] == ["src"]
    assert features.static.top_level_directory_count == 2


def test_root_files_only_form_one_mass(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("x\n", encoding="utf-8")

    masses = extract_features(tmp_path).structure.masses

    assert [(m.name, m.file_share, m.churn_share) for m in masses] == [(".", 1.0, 0.0)]


def test_empty_directory_has_no_masses_even_with_deleted_history(tmp_path: Path) -> None:
    raw = RawGitHistory(is_git_repo=True, commit_count=1, authors=["A"], file_changes={"gone.py": 2})

    structure = compute_structure_features(scan_repository_tree(tmp_path), raw)

    assert structure.masses == []
    assert structure.hotspot_concentration == 0.0


def test_hotspots_keep_mass_other_when_no_file_is_scanned(tmp_path: Path) -> None:
    # Q1 from the PR #6 review, decided by Tomasz: with history but 0 scanned
    # files there are no masses, and every hotspot still gets mass "other".
    repo = create_emptied_repo(tmp_path / "emptied-repo")

    features = extract_features(repo)

    assert features.static.file_count == 0
    assert features.structure.masses == []
    assert sorted((h.path, h.change_count, h.mass) for h in features.history.hotspots) == [
        ("helper.py", 2, "other"),
        ("main.py", 2, "other"),
    ]


def test_masses_without_git_have_no_churn(non_git_dir: Path) -> None:
    features = extract_features(non_git_dir)

    assert [(m.name, m.churn_share) for m in features.structure.masses] == [(".", 0.0)]
    assert features.structure.hotspot_concentration == 0.0
    assert features.history.hotspots == []


@pytest.mark.parametrize("fixture", ["clean_modular_repo", "legacy_chaotic_repo", "wide_repo", "timeline_repo"])
def test_mass_shares_sum_to_one(fixture: str, request: pytest.FixtureRequest) -> None:
    structure = _structure(request.getfixturevalue(fixture))

    assert sum(m.file_share for m in structure.masses) == pytest.approx(1.0, abs=0.001)
    assert sum(m.churn_share for m in structure.masses) == pytest.approx(1.0, abs=0.001)
