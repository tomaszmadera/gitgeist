"""Semantic qualitative flags (nouls) calculation from repository features and scores."""

from __future__ import annotations

from gitgeist.schemas.emotional import EmotionalNouls, EmotionalScores
from gitgeist.schemas.features import RepositoryFeatures


def calculate_nouls(features: RepositoryFeatures, scores: EmotionalScores) -> EmotionalNouls:
    """Evaluate semantic nouls based on features and computed emotional scores."""
    static = features.static
    docs = features.docs

    appears_experimental = scores.novelty > 0.6 or (scores.maturity < 0.35 and scores.volatility > 0.3)
    feels_stable = (
        scores.coherence >= 0.5
        and scores.discipline >= 0.5
        and scores.chaos < 0.4
        and scores.volatility < 0.5
    )
    feels_overloaded = (
        scores.tension > 0.6
        or scores.fragility > 0.7
        or scores.internal_conflict > 0.6
        or static.todo_count > 10
    )
    feels_under_control = (
        scores.discipline >= 0.5
        and scores.chaos < 0.4
        and scores.fragility < 0.5
    )
    feels_fragmented = (
        scores.chaos > 0.5
        or scores.coherence < 0.4
        or (static.directory_count == 0 and static.file_count > 5)
    )
    feels_unfinished = (
        not static.has_tests
        or not docs.has_readme
        or scores.maturity < 0.3
    )
    feels_resilient = (
        scores.maturity > 0.5
        and scores.discipline > 0.5
        and static.has_tests
        and scores.fragility < 0.4
    )

    return EmotionalNouls(
        appears_experimental=appears_experimental,
        feels_stable=feels_stable,
        feels_overloaded=feels_overloaded,
        feels_under_control=feels_under_control,
        feels_fragmented=feels_fragmented,
        feels_unfinished=feels_unfinished,
        feels_resilient=feels_resilient,
    )
