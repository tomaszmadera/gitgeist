"""Emotional State Model evaluator combining sensors into a coherent Layer 2 profile."""

from __future__ import annotations

from datetime import datetime
from gitgeist.schemas.emotional import EmotionalState
from gitgeist.schemas.features import RepositoryFeatures
from gitgeist.sensors.choices import calculate_choices
from gitgeist.sensors.nouls import calculate_nouls
from gitgeist.sensors.scores import calculate_scores


def evaluate_emotional_state(
    features: RepositoryFeatures,
    source_commit: str | None = None,
    calculated_at: datetime | None = None,
    engine_version: str = "0.1.0-beta.1",
) -> EmotionalState:
    """Evaluate deterministic emotional state profile from repository features."""
    if not isinstance(features, RepositoryFeatures):
        raise TypeError(f"Expected RepositoryFeatures instance, got {type(features).__name__}")

    scores = calculate_scores(features)
    nouls = calculate_nouls(features, scores)
    choices = calculate_choices(features, scores)

    eval_time = calculated_at or features.extracted_at

    return EmotionalState(
        scores=scores,
        nouls=nouls,
        choices=choices,
        calculated_at=eval_time,
        source_commit=source_commit,
        engine_version=engine_version,
    )
