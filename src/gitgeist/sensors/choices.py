"""Categorical choice distributions calculation from repository features and scores."""

from __future__ import annotations

from gitgeist.schemas.emotional import ChoiceDistribution, EmotionalChoices, EmotionalScores
from gitgeist.schemas.features import RepositoryFeatures


def build_distribution(raw_map: dict[str, float]) -> ChoiceDistribution:
    """Normalize raw scores to a probability distribution summing to 1.0 with a verified dominant choice."""
    epsilon = 0.01
    adjusted = {k: max(0.0, v) + epsilon for k, v in raw_map.items()}
    total = sum(adjusted.values())
    raw_weights = {k: v / total for k, v in adjusted.items()}

    # Sort keys for deterministic behavior
    sorted_keys = sorted(raw_weights.keys())

    # Round weights to 4 decimal places
    rounded = {k: round(raw_weights[k], 4) for k in sorted_keys}

    # Deterministically select dominant key (highest weight, then earliest alphabetical for ties)
    dominant_key = min(sorted_keys, key=lambda k: (-rounded[k], k))

    # Adjust dominant weight so sum is exactly 1.0
    current_sum = round(sum(rounded.values()), 4)
    diff = round(1.0 - current_sum, 4)
    rounded[dominant_key] = round(rounded[dominant_key] + diff, 4)

    # Re-evaluate dominant in case of precision adjustments
    actual_dominant = min(sorted_keys, key=lambda k: (-rounded[k], k))

    return ChoiceDistribution(weights=rounded, dominant=actual_dominant)


def calculate_choices(features: RepositoryFeatures, scores: EmotionalScores) -> EmotionalChoices:
    """Calculate temperament, visual tone, and energy profile choice distributions."""
    static = features.static

    # 1. Temperament
    raw_temperament = {
        "calm": scores.coherence * (1.0 - scores.tension) * (1.0 - scores.volatility),
        "restless": scores.volatility * 0.7 + scores.tension * 0.3,
        "disciplined": scores.discipline * 0.8 + scores.coherence * 0.2,
        "playful": scores.novelty * (1.0 - scores.maturity) * (1.0 - scores.tension),
        "brooding": scores.fragility * 0.6 + scores.internal_conflict * 0.4,
        "proud": scores.maturity * 0.5 + scores.identity_strength * 0.5,
        "anxious": scores.tension * 0.5 + scores.chaos * 0.5,
        "mysterious": (1.0 - scores.identity_strength) * 0.5 + scores.internal_conflict * 0.5,
    }
    temperament = build_distribution(raw_temperament)

    # 2. Visual tone
    size_norm = min(1.0, static.total_size_bytes / 50000.0) if static.total_size_bytes > 0 else 0.0
    file_norm = min(1.0, static.file_count / 50.0) if static.file_count > 0 else 0.0

    raw_visual_tone = {
        "luminous": scores.novelty * 0.4 + scores.coherence * 0.4 + (1.0 - scores.chaos) * 0.2,
        "austere": scores.discipline * 0.6 + (1.0 - scores.volatility) * 0.4,
        "dense": file_norm * 0.5 + scores.maturity * 0.5,
        "delicate": (1.0 - size_norm) * 0.5 + scores.fragility * 0.5,
        "monumental": scores.maturity * 0.5 + scores.identity_strength * 0.5,
        "fractured": scores.chaos * 0.6 + scores.internal_conflict * 0.4,
        "flowing": scores.volatility * 0.4 + scores.coherence * 0.6,
    }
    visual_tone = build_distribution(raw_visual_tone)

    # 3. Energy profile
    raw_energy_profile = {
        "static": (1.0 - scores.volatility) * 0.7 + (1.0 - scores.tension) * 0.3,
        "pulsing": scores.volatility * 0.5 + scores.coherence * 0.5,
        "coiled": scores.tension * 0.7 + scores.discipline * 0.3,
        "diffused": scores.chaos * 0.6 + (1.0 - scores.identity_strength) * 0.4,
        "turbulent": scores.volatility * 0.4 + scores.chaos * 0.3 + scores.tension * 0.3,
        "focused": scores.discipline * 0.5 + scores.coherence * 0.5,
    }
    energy_profile = build_distribution(raw_energy_profile)

    return EmotionalChoices(
        temperament=temperament,
        visual_tone=visual_tone,
        energy_profile=energy_profile,
    )
