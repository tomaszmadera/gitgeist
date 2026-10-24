from pathlib import Path
from datetime import datetime, timezone
import pytest
from gitgeist.explain import explain
from gitgeist.features.extractor import extract_features
from gitgeist.interpretation.emotional_model import evaluate_emotional_state
from gitgeist.mapping.latent_mapper import map_emotional_to_latent
from gitgeist.schemas.features import RepositoryFeatures
from gitgeist.visual import compute_traits


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


_V2_FIELDS = {
    "static": ("code_bytes", "code_file_count", "test_file_count", "test_ratio", "doc_ratio",
               "todo_density", "top_level_directory_count", "language_shares"),
    "history": ("timeline_start", "timeline", "active_months_ratio", "top_author_share", "top3_author_share"),
}


def _without_v2(features: RepositoryFeatures) -> RepositoryFeatures:
    """The same features with every v2 field reset to its default."""
    data = features.model_dump()
    del data["structure"]
    for block, keys in _V2_FIELDS.items():
        for key in keys:
            del data[block][key]
    for hotspot in data["history"]["hotspots"]:
        del hotspot["change_share"], hotspot["mass"]
    return RepositoryFeatures.model_validate(data)


@pytest.mark.parametrize(
    "fixture",
    ["minimal_repo", "clean_modular_repo", "legacy_chaotic_repo", "timeline_repo", "wide_repo", "non_git_dir"],
)
def test_v2_fields_do_not_change_downstream_layers(fixture: str, request: pytest.FixtureRequest) -> None:
    features = extract_features(request.getfixturevalue(fixture))
    baseline = _without_v2(features)
    assert baseline != features

    state = evaluate_emotional_state(features)
    baseline_state = evaluate_emotional_state(baseline)
    profile = map_emotional_to_latent(state)
    baseline_profile = map_emotional_to_latent(baseline_state)

    assert state == baseline_state
    assert profile == baseline_profile
    traits = compute_traits(features, reference_time=datetime(2026, 4, 16, tzinfo=timezone.utc))
    assert explain(features, state, profile, traits=traits).summary_md == explain(baseline, baseline_state, baseline_profile).summary_md


def test_extract_features_fills_structure(wide_repo: Path) -> None:
    features = extract_features(wide_repo)

    assert len(features.structure.masses) == 8
    assert all(h.mass is not None for h in features.history.hotspots)


def test_extract_features_v2_determinism(wide_repo: Path) -> None:
    first = extract_features(wide_repo)
    second = extract_features(wide_repo)

    assert first.model_copy(update={"extracted_at": second.extracted_at}) == second
