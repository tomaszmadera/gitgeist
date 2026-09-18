"""Calculator for materiality distribution."""

from __future__ import annotations

from gitgeist.schemas.emotional import (
    EmotionalChoices,
    EmotionalNouls,
    EmotionalScores,
)
from gitgeist.schemas.visual_latent import MaterialityDistribution, VisualLatentAxes


def calculate_materiality(
    axes: VisualLatentAxes,
    scores: EmotionalScores,
    nouls: EmotionalNouls,
    choices: EmotionalChoices,
) -> MaterialityDistribution:
    """Compute normalized materiality distribution from visual axes and emotional state."""
    t_weights = choices.temperament.weights
    vt_weights = choices.visual_tone.weights

    # Base raw tendencies
    raw_organic = (
        (1.0 - axes.biological_vs_mechanical) * 0.45
        + 0.3 * scores.novelty
        + 0.2 * t_weights.get("playful", 0.0)
        + (0.1 if nouls.appears_experimental else 0.0)
    )

    raw_mechanical = (
        axes.biological_vs_mechanical * 0.45
        + 0.3 * scores.discipline
        + 0.25 * scores.maturity
    )

    raw_crystalline = (
        0.35 * scores.coherence
        + 0.35 * axes.sharpness
        + 0.3 * axes.symmetry
    )

    raw_ethereal = (
        0.35 * scores.fragility
        + 0.35 * (1.0 - axes.opacity)
        + 0.3 * vt_weights.get("delicate", 0.0)
    )

    raw_weights = {
        "organic": max(0.01, raw_organic + 0.05),
        "mechanical": max(0.01, raw_mechanical + 0.05),
        "crystalline": max(0.01, raw_crystalline + 0.05),
        "ethereal": max(0.01, raw_ethereal + 0.05),
    }

    total = sum(raw_weights.values())
    sorted_keys = sorted(raw_weights.keys())

    # Largest remainder method to guarantee sum == 1.0000 and consistent dominant
    scaled = {k: (raw_weights[k] / total) * 10000.0 for k in sorted_keys}
    base = {k: int(scaled[k]) for k in sorted_keys}
    remainder = {k: scaled[k] - base[k] for k in sorted_keys}

    unassigned = 10000 - sum(base.values())
    for k in sorted(sorted_keys, key=lambda k: (-remainder[k], k))[:unassigned]:
        base[k] += 1

    weights = {k: round(base[k] / 10000.0, 4) for k in sorted_keys}

    # Select dominant with deterministic alphabetical tie-breaking
    dominant = min(sorted_keys, key=lambda k: (-weights[k], k))

    return MaterialityDistribution(weights=weights, dominant=dominant)
