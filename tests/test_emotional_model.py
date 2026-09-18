"""Integration tests for Emotional State Model evaluation."""

from __future__ import annotations

from pathlib import Path
import pytest

from gitgeist import evaluate_emotional_state, extract_features
from gitgeist.schemas.emotional import EmotionalState


def test_evaluate_emotional_state_integration(clean_modular_repo: Path) -> None:
    features = extract_features(clean_modular_repo)
    state = evaluate_emotional_state(features, source_commit="abc1234")

    assert isinstance(state, EmotionalState)
    assert 0.0 <= state.scores.coherence <= 1.0
    assert state.choices.temperament.dominant in state.choices.temperament.weights
    assert state.source_commit == "abc1234"


def test_evaluate_emotional_state_determinism(legacy_chaotic_repo: Path) -> None:
    features = extract_features(legacy_chaotic_repo)
    state1 = evaluate_emotional_state(features)
    state2 = evaluate_emotional_state(features)

    assert state1.scores == state2.scores
    assert state1.nouls == state2.nouls
    assert state1.choices == state2.choices
    assert state1.model_dump() == state2.model_dump()


def test_evaluate_emotional_state_invalid_type() -> None:
    with pytest.raises((TypeError, ValueError)):
        evaluate_emotional_state("not-features")  # type: ignore[arg-type]
