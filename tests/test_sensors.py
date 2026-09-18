"""Unit tests for emotional sensors and metric calculations."""

from __future__ import annotations

from pathlib import Path
import pytest

from gitgeist.features.extractor import extract_features
from gitgeist.schemas.emotional import EmotionalScores
from gitgeist.sensors.choices import calculate_choices
from gitgeist.sensors.nouls import calculate_nouls
from gitgeist.sensors.scores import calculate_scores


def test_calculate_scores_clean_modular_repo(clean_modular_repo: Path) -> None:
    features = extract_features(clean_modular_repo)
    scores = calculate_scores(features)

    # Clean repo should score high on coherence, discipline, maturity
    assert scores.coherence >= 0.5
    assert scores.discipline >= 0.5
    assert scores.chaos <= 0.4
    assert 0.0 <= scores.tension <= 1.0
    assert 0.0 <= scores.volatility <= 1.0
    assert 0.0 <= scores.fragility <= 1.0


def test_calculate_scores_legacy_chaotic_repo(legacy_chaotic_repo: Path) -> None:
    features = extract_features(legacy_chaotic_repo)
    scores = calculate_scores(features)

    # Chaotic repo has files in root, TODOs, high churn in hotspots, no clean tests
    assert scores.chaos >= 0.4
    assert scores.discipline <= 0.6
    assert scores.fragility >= 0.3


def test_calculate_scores_minimal_repo(minimal_repo: Path) -> None:
    features = extract_features(minimal_repo)
    scores = calculate_scores(features)

    # Safe evaluation without division by zero
    for field_name in EmotionalScores.model_fields:
        val = getattr(scores, field_name)
        assert 0.0 <= val <= 1.0


def test_calculate_nouls(clean_modular_repo: Path, legacy_chaotic_repo: Path) -> None:
    clean_feat = extract_features(clean_modular_repo)
    clean_scores = calculate_scores(clean_feat)
    clean_nouls = calculate_nouls(clean_feat, clean_scores)

    assert clean_nouls.feels_stable is True
    assert clean_nouls.feels_fragmented is False

    chaotic_feat = extract_features(legacy_chaotic_repo)
    chaotic_scores = calculate_scores(chaotic_feat)
    chaotic_nouls = calculate_nouls(chaotic_feat, chaotic_scores)

    assert chaotic_nouls.feels_under_control is False or chaotic_nouls.feels_fragmented is True


def test_calculate_choices(clean_modular_repo: Path) -> None:
    features = extract_features(clean_modular_repo)
    scores = calculate_scores(features)
    choices = calculate_choices(features, scores)

    # Verify distribution constraints
    for dist in (choices.temperament, choices.visual_tone, choices.energy_profile):
        assert sum(dist.weights.values()) == pytest.approx(1.0, abs=1e-4)
        assert dist.dominant in dist.weights
        assert dist.weights[dist.dominant] == max(dist.weights.values())


def test_choices_tie_breaking_alphabetical() -> None:
    from gitgeist.sensors.choices import build_distribution

    # When scores tie, earliest alphabetical candidate must be chosen
    dist = build_distribution({"zebra": 1.0, "apple": 1.0})
    assert dist.dominant == "apple"
    assert dist.weights["apple"] == dist.weights["zebra"]


def test_calculate_scores_non_git_dir(non_git_dir: Path) -> None:
    features = extract_features(non_git_dir)
    scores = calculate_scores(features)
    assert 0.0 <= scores.coherence <= 1.0
    assert 0.0 <= scores.volatility <= 1.0
    assert scores.volatility == 0.1  # Non-git default
