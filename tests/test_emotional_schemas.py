"""Unit tests for emotional state and sensor schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gitgeist.schemas.emotional import (
    ChoiceDistribution,
    EmotionalChoices,
    EmotionalNouls,
    EmotionalScores,
    EmotionalState,
)


def test_emotional_scores_valid() -> None:
    scores = EmotionalScores(
        coherence=0.85,
        maturity=0.7,
        volatility=0.2,
        fragility=0.15,
        novelty=0.4,
        discipline=0.9,
        tension=0.1,
        chaos=0.05,
        identity_strength=0.8,
        internal_conflict=0.1,
    )
    assert scores.coherence == 0.85
    assert scores.discipline == 0.9

    # Frozen immutability
    with pytest.raises(ValidationError):
        scores.coherence = 0.5  # type: ignore[misc]


def test_emotional_scores_bounds_validation() -> None:
    with pytest.raises(ValidationError):
        EmotionalScores(
            coherence=1.2,  # > 1.0
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

    with pytest.raises(ValidationError):
        EmotionalScores(
            coherence=-0.1,  # < 0.0
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


def test_emotional_nouls_valid() -> None:
    nouls = EmotionalNouls(
        appears_experimental=False,
        feels_stable=True,
        feels_overloaded=False,
        feels_under_control=True,
        feels_fragmented=False,
        feels_unfinished=False,
        feels_resilient=True,
    )
    assert nouls.feels_stable is True
    assert nouls.feels_overloaded is False

    with pytest.raises(ValidationError):
        nouls.feels_stable = False  # type: ignore[misc]


def test_choice_distribution_valid() -> None:
    dist = ChoiceDistribution(
        weights={
            "calm": 0.5,
            "disciplined": 0.3,
            "mysterious": 0.2,
        },
        dominant="calm",
    )
    assert dist.dominant == "calm"
    assert sum(dist.weights.values()) == pytest.approx(1.0)


def test_choice_distribution_invalid_dominant() -> None:
    # dominant is not the key with max weight
    with pytest.raises(ValidationError):
        ChoiceDistribution(
            weights={
                "calm": 0.7,
                "disciplined": 0.3,
            },
            dominant="disciplined",
        )


def test_choice_distribution_unnormalized_weights() -> None:
    # weights do not sum to 1.0
    with pytest.raises(ValidationError):
        ChoiceDistribution(
            weights={
                "calm": 0.5,
                "disciplined": 0.2,
            },
            dominant="calm",
        )


def test_choice_distribution_negative_weights() -> None:
    # negative weight
    with pytest.raises(ValidationError):
        ChoiceDistribution(
            weights={
                "calm": 1.2,
                "disciplined": -0.2,
            },
            dominant="calm",
        )


def test_emotional_choices_and_state_roundtrip() -> None:
    temperament = ChoiceDistribution(
        weights={"calm": 0.6, "disciplined": 0.4},
        dominant="calm",
    )
    visual_tone = ChoiceDistribution(
        weights={"luminous": 0.7, "dense": 0.3},
        dominant="luminous",
    )
    energy_profile = ChoiceDistribution(
        weights={"focused": 0.8, "pulsing": 0.2},
        dominant="focused",
    )
    choices = EmotionalChoices(
        temperament=temperament,
        visual_tone=visual_tone,
        energy_profile=energy_profile,
    )

    scores = EmotionalScores(
        coherence=0.8,
        maturity=0.7,
        volatility=0.2,
        fragility=0.1,
        novelty=0.3,
        discipline=0.85,
        tension=0.15,
        chaos=0.1,
        identity_strength=0.75,
        internal_conflict=0.05,
    )

    nouls = EmotionalNouls(
        appears_experimental=False,
        feels_stable=True,
        feels_overloaded=False,
        feels_under_control=True,
        feels_fragmented=False,
        feels_unfinished=False,
        feels_resilient=True,
    )

    state = EmotionalState(
        scores=scores,
        nouls=nouls,
        choices=choices,
        source_commit="37d9eea",
        engine_version="0.1.0-beta.1",
    )

    assert state.scores.coherence == 0.8
    assert state.choices.temperament.dominant == "calm"

    json_data = state.model_dump_json()
    reloaded = EmotionalState.model_validate_json(json_data)
    assert reloaded == state
