"""Tests for the explainability layer (summary, why-this-look, profile.json)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gitgeist import evaluate_emotional_state, explain, extract_features, map_emotional_to_latent
from gitgeist.explain.explainer import ExplanationArtifacts
from gitgeist.schemas.emotional import (
    ChoiceDistribution,
    EmotionalChoices,
    EmotionalNouls,
    EmotionalScores,
    EmotionalState,
)
from gitgeist.schemas.features import (
    DocsSummaryFeatures,
    GitHistoryFeatures,
    StaticFeatures,
    RepositoryFeatures,
)
from gitgeist.schemas.visual_latent import (
    MaterialityDistribution,
    VisualLatentAxes,
    VisualLatentProfile,
)


def make_features() -> RepositoryFeatures:
    return RepositoryFeatures(
        repository_path="/tmp/sample-repo",
        extracted_at=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        static=StaticFeatures(
            file_count=24,
            directory_count=4,
            max_directory_depth=3,
            languages={"Python": 18, "Markdown": 4},
            total_size_bytes=48_000,
            avg_file_size_bytes=2_000.0,
            has_tests=True,
            has_documentation=True,
            has_ci=True,
            todo_count=2,
        ),
        history=GitHistoryFeatures(
            is_git_repo=True,
            commit_count=42,
            unique_authors_count=3,
            first_commit_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            last_commit_date=datetime(2026, 4, 30, tzinfo=timezone.utc),
            repository_age_days=485,
            velocity=1.4,
            total_lines_added=5_200,
            total_lines_deleted=1_100,
        ),
        docs=DocsSummaryFeatures(
            has_readme=True,
            readme_length_chars=900,
            readme_snippet="# Sample",
            license_type="MIT",
        ),
    )


def make_emotional_state() -> EmotionalState:
    scores = EmotionalScores(
        coherence=0.81,
        maturity=0.72,
        volatility=0.25,
        fragility=0.2,
        novelty=0.5,
        discipline=0.77,
        tension=0.3,
        chaos=0.15,
        identity_strength=0.69,
        internal_conflict=0.31,
    )
    choices = EmotionalChoices(
        temperament=ChoiceDistribution(
            weights={"calm": 0.4, "restless": 0.2, "proud": 0.2, "anxious": 0.2},
            dominant="calm",
        ),
        visual_tone=ChoiceDistribution(
            weights={"luminous": 0.5, "austere": 0.3, "dense": 0.2},
            dominant="luminous",
        ),
        energy_profile=ChoiceDistribution(
            weights={"focused": 0.6, "static": 0.4},
            dominant="focused",
        ),
    )
    return EmotionalState(scores=scores, nouls=EmotionalNouls(), choices=choices)


def make_profile() -> VisualLatentProfile:
    axes = VisualLatentAxes(
        form_complexity=0.5,
        symmetry=0.85,
        fragmentation=0.2,
        tension_curvature=0.4,
        texture_density=0.5,
        luminosity=0.6,
        contrast=0.55,
        sharpness=0.6,
        visual_rhythm=0.7,
        compositional_balance=0.8,
        biological_vs_mechanical=0.6,
        ornamental_load=0.45,
        opacity=0.65,
        layering=0.9,
    )
    materiality = MaterialityDistribution(
        weights={"organic": 0.1, "mechanical": 0.6, "crystalline": 0.2, "ethereal": 0.1},
        dominant="mechanical",
    )
    return VisualLatentProfile(
        axes=axes,
        materiality=materiality,
        dominant_features=["layering", "symmetry"],
    )


def make_axis_profile(axis_value: float) -> VisualLatentProfile:
    axes = VisualLatentAxes(**{name: axis_value for name in VisualLatentAxes.model_fields})
    return VisualLatentProfile(
        axes=axes,
        materiality=MaterialityDistribution(weights={"organic": 1.0}, dominant="organic"),
    )


def make_score_state(score_value: float) -> EmotionalState:
    scores = EmotionalScores(**{name: score_value for name in EmotionalScores.model_fields})
    return EmotionalState(scores=scores, nouls=EmotionalNouls(), choices=make_emotional_state().choices)


def make_neutral_bundle() -> tuple[RepositoryFeatures, EmotionalState, VisualLatentProfile]:
    features = make_features()
    scores = EmotionalScores(
        coherence=0.5,
        maturity=0.5,
        volatility=0.5,
        fragility=0.5,
        novelty=0.5,
        discipline=0.5,
        tension=0.5,
        chaos=0.5,
        identity_strength=0.5,
        internal_conflict=0.5,
    )
    state = EmotionalState(scores=scores, nouls=EmotionalNouls(), choices=make_emotional_state().choices)
    axes = VisualLatentAxes(
        form_complexity=0.5,
        symmetry=0.5,
        fragmentation=0.5,
        tension_curvature=0.5,
        texture_density=0.5,
        luminosity=0.5,
        contrast=0.5,
        sharpness=0.5,
        visual_rhythm=0.5,
        compositional_balance=0.5,
        biological_vs_mechanical=0.5,
        ornamental_load=0.5,
        opacity=0.5,
        layering=0.5,
    )
    profile = VisualLatentProfile(
        axes=axes,
        materiality=MaterialityDistribution(weights={"organic": 1.0}, dominant="organic"),
    )
    return features, state, profile


def section_lines(summary_md: str, header: str) -> list[str]:
    lines = summary_md.splitlines()
    start = lines.index(header) + 1
    end = start
    while end < len(lines) and not lines[end].startswith("#"):
        end += 1
    return [line for line in lines[start:end] if line.startswith("- ")]


def test_explain_returns_complete_artifacts():
    artifacts = explain(make_features(), make_emotional_state(), make_profile())
    assert isinstance(artifacts, ExplanationArtifacts)
    assert isinstance(artifacts.why_this_look, tuple)
    assert artifacts.summary_path is None
    assert artifacts.profile_path is None
    assert artifacts.summary_md.endswith("\n")
    assert artifacts.profile_json.endswith("\n")


def test_explain_summary_contains_required_sections():
    summary = explain(make_features(), make_emotional_state(), make_profile(), repository_name="sample").summary_md
    assert summary.startswith("# Repository Portrait: sample")
    for header in (
        "## Repository overview",
        "## Emotional state",
        "## Visual latent profile",
        "## Why does this portrait look layered, symmetrical and balanced?",
        "## Top JEV sensors",
        "## Top contributing repository signals",
    ):
        assert header in summary


def test_explain_summary_excludes_repository_name_when_missing():
    summary = explain(make_features(), make_emotional_state(), make_profile()).summary_md
    assert summary.startswith("# Repository Portrait\n")
    assert "sample-repo" not in summary


def test_explain_summary_has_no_volatile_fields():
    summary = explain(make_features(), make_emotional_state(), make_profile(), repository_name="sample").summary_md
    for forbidden in ("calculated_at", "source_commit", "engine_version", "/tmp/sample-repo"):
        assert forbidden not in summary


def test_explain_is_deterministic():
    features, state, profile = make_features(), make_emotional_state(), make_profile()
    first = explain(features, state, profile, repository_name="sample")
    second = explain(features, state, profile, repository_name="sample")
    assert first.summary_md == second.summary_md
    assert first.why_this_look == second.why_this_look
    assert first.profile_json == second.profile_json


def test_explain_texts_stable_against_volatile_fields():
    features = make_features()
    state = make_emotional_state()
    profile = make_profile()
    shifted_state = state.model_copy(
        update={
            "calculated_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
            "source_commit": "other-commit",
            "engine_version": "9.9.9",
        }
    )
    shifted_profile = profile.model_copy(
        update={
            "calculated_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
            "source_commit": "other-commit",
            "engine_version": "9.9.9",
        }
    )
    baseline = explain(features, state, profile)
    shifted = explain(features, shifted_state, shifted_profile)
    assert baseline.summary_md == shifted.summary_md
    assert baseline.why_this_look == shifted.why_this_look
    assert baseline.profile_json != shifted.profile_json
    assert '"source_commit": "other-commit"' in shifted.profile_json


def test_why_this_look_headline_and_attributions():
    artifacts = explain(make_features(), make_emotional_state(), make_profile())
    why = artifacts.why_this_look
    assert why[0] == "Why does this portrait look layered, symmetrical and balanced?"
    assert "high coherence (raises layering)" in why
    assert "high maturity (raises layering)" in why
    assert "low chaos (raises symmetry)" in why
    assert "high discipline (raises symmetry)" in why
    assert "high coherence (raises compositional_balance)" in why
    assert "low volatility (raises compositional_balance)" in why


def test_why_this_look_attribution_qualifiers_match_scores():
    state = make_emotional_state()
    profile = make_profile()
    qualifier = lambda value: "low" if value <= 0.33 else "medium" if value <= 0.66 else "high"
    for line in explain(make_features(), state, profile).why_this_look[1:]:
        if " (" not in line:
            continue
        phrase, _ = line.split(" (", 1)
        qualifier_word, score_name = phrase.split(" ", 1)
        assert qualifier_word == qualifier(getattr(state.scores, score_name))


def test_why_this_look_neutral_profile_tie_break():
    features, state, profile = make_neutral_bundle()
    why = explain(features, state, profile).why_this_look
    assert why[0] == (
        "Why does this portrait look moderately mechanical, "
        "moderately balanced and moderately high-contrast?"
    )
    assert "no single dominant emotional driver behind biological_vs_mechanical" in why
    assert "no single dominant emotional driver behind compositional_balance" in why
    assert "no single dominant emotional driver behind contrast" in why


def test_extreme_high_profile_boundaries():
    state = make_score_state(1.0)
    profile = make_axis_profile(1.0)
    artifacts = explain(make_features(), state, profile)
    why = artifacts.why_this_look
    assert why[0] == "Why does this portrait look mechanical, balanced and high-contrast?"
    axis_bullets = [line for line in why[1:]]
    assert len(axis_bullets) == 8
    assert "high discipline (raises biological_vs_mechanical)" in why
    assert "high novelty (lowers biological_vs_mechanical)" in why
    assert "high coherence (raises compositional_balance)" in why
    assert "high volatility (lowers compositional_balance)" in why
    assert "high identity_strength (raises contrast)" in why
    summary = artifacts.summary_md
    assert "- chaos: high (1.00)" in summary
    assert "- contrast: high (1.00)" in summary
    assert "- dominant features:" not in summary


def test_extreme_low_profile_boundaries():
    state = make_score_state(0.0)
    profile = make_axis_profile(0.0)
    artifacts = explain(make_features(), state, profile)
    why = artifacts.why_this_look
    assert why[0] == "Why does this portrait look organic, unbalanced and low-contrast?"
    assert "low identity_strength (lowers contrast)" in why
    assert "low tension (lowers contrast)" in why
    assert "low maturity (lowers biological_vs_mechanical)" in why
    summary = artifacts.summary_md
    assert "- chaos: low (0.00)" in summary
    assert "- contrast: low (0.00)" in summary
    assert "- dominant features:" not in summary


def test_empty_dominant_features_line_omitted():
    profile = make_profile().model_copy(update={"dominant_features": []})
    summary = explain(make_features(), make_emotional_state(), profile).summary_md
    assert "- dominant features:" not in summary
    assert "## Visual latent profile" in summary


def test_top_sensors_ranking():
    summary = explain(make_features(), make_emotional_state(), make_profile()).summary_md
    sensors = section_lines(summary, "## Top JEV sensors")
    assert len(sensors) == 5
    assert sensors[0] == "- chaos: low (0.15)"
    assert sensors[1] == "- coherence: high (0.81)"
    assert sensors[2] == "- fragility: low (0.20)"
    assert sensors[3] == "- discipline: high (0.77)"
    assert sensors[4] == "- volatility: low (0.25)"


def test_top_signals_match_top_sensors():
    summary = explain(make_features(), make_emotional_state(), make_profile()).summary_md
    signals = section_lines(summary, "## Top contributing repository signals")
    assert len(signals) == 5
    assert signals[0] == "- chaos: no distinguishing repository signals"
    assert signals[1].startswith("- coherence: ")
    assert "README present" in signals[1]


def test_qualifier_boundaries_in_summary():
    scores = EmotionalScores(
        coherence=0.33,
        maturity=0.34,
        volatility=0.66,
        fragility=0.67,
        novelty=0.5,
        discipline=0.5,
        tension=0.5,
        chaos=0.5,
        identity_strength=0.5,
        internal_conflict=0.5,
    )
    state = EmotionalState(scores=scores, nouls=EmotionalNouls(), choices=make_emotional_state().choices)
    features, _, profile = make_neutral_bundle()
    summary = explain(features, state, profile).summary_md
    assert "- coherence: low (0.33)" in summary
    assert "- maturity: medium (0.34)" in summary
    assert "- volatility: medium (0.66)" in summary
    assert "- fragility: high (0.67)" in summary


def test_repository_overview_facts():
    summary = explain(make_features(), make_emotional_state(), make_profile()).summary_md
    overview = section_lines(summary, "## Repository overview")
    assert "- files: 24 in 4 directories (max depth 3)" in overview
    assert "- languages: Python (18), Markdown (4)" in overview
    assert "- size: 48000 bytes (average 2000.0 bytes per file)" in overview
    assert "- git: 42 commits by 3 authors, age 485 days, velocity 1.40 commits/day" in overview
    assert "- churn: +5200 -1100 lines" in overview
    assert "- hygiene: tests, CI, README, documentation, license: MIT" in overview
    assert "- TODO/FIXME markers: 2" in overview


def test_repository_overview_without_git_history(non_git_dir: Path):
    features = extract_features(non_git_dir)
    state = evaluate_emotional_state(features)
    profile = map_emotional_to_latent(state)
    summary = explain(features, state, profile).summary_md
    assert "- git: no history available" in summary


def test_profile_json_roundtrip():
    features, state, profile = make_features(), make_emotional_state(), make_profile()
    payload = json.loads(explain(features, state, profile).profile_json)
    assert set(payload) == {"emotional_state", "repository", "visual_latent"}
    assert RepositoryFeatures.model_validate(payload["repository"]) == features
    assert EmotionalState.model_validate(payload["emotional_state"]) == state
    assert VisualLatentProfile.model_validate(payload["visual_latent"]) == profile


def test_profile_json_keys_sorted_and_full():
    text = explain(make_features(), make_emotional_state(), make_profile()).profile_json
    assert text.index('"emotional_state"') < text.index('"repository"') < text.index('"visual_latent"')
    for key in ("calculated_at", "source_commit", "engine_version"):
        assert f'"{key}"' in text


def test_explain_writes_artifacts(tmp_path: Path):
    output_dir = tmp_path / "nested" / "out"
    artifacts = explain(
        make_features(),
        make_emotional_state(),
        make_profile(),
        output_dir=output_dir,
    )
    assert artifacts.summary_path == output_dir / "summary.md"
    assert artifacts.profile_path == output_dir / "profile.json"
    assert artifacts.summary_path.read_text(encoding="utf-8") == artifacts.summary_md
    assert artifacts.profile_path.read_text(encoding="utf-8") == artifacts.profile_json


def test_explain_without_output_writes_nothing(tmp_path: Path):
    explain(make_features(), make_emotional_state(), make_profile())
    assert list(tmp_path.iterdir()) == []


def test_explain_write_failure_raises_oserror(tmp_path: Path):
    blocker = tmp_path / "occupied"
    blocker.write_text("not a directory", encoding="utf-8")
    with pytest.raises(OSError):
        explain(make_features(), make_emotional_state(), make_profile(), output_dir=blocker)
    assert not (blocker / "summary.md").exists()
    assert not (blocker / "profile.json").exists()


def test_explain_rejects_wrong_types():
    features, state, profile = make_features(), make_emotional_state(), make_profile()
    with pytest.raises(TypeError):
        explain("not-features", state, profile)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        explain(features, "not-a-state", profile)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        explain(features, state, "not-a-profile")  # type: ignore[arg-type]


def test_explain_integration_with_pipeline(clean_modular_repo: Path):
    features = extract_features(clean_modular_repo)
    state = evaluate_emotional_state(features, source_commit="abc1234")
    profile = map_emotional_to_latent(state)
    artifacts = explain(features, state, profile, repository_name="clean-modular-repo")
    assert artifacts.why_this_look[0].startswith("Why does this portrait look ")
    for line in artifacts.why_this_look[1:]:
        if " (" not in line:
            continue
        phrase = line.split(" (", 1)[0]
        qualifier_word, score_name = phrase.split(" ", 1)
        value = getattr(state.scores, score_name)
        expected = "low" if value <= 0.33 else "medium" if value <= 0.66 else "high"
        assert qualifier_word == expected
