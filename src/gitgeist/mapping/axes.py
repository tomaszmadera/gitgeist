"""Calculators for continuous visual latent axes."""

from __future__ import annotations

from gitgeist.schemas.emotional import (
    EmotionalChoices,
    EmotionalNouls,
    EmotionalScores,
)
from gitgeist.schemas.visual_latent import VisualLatentAxes


def _clamp(val: float) -> float:
    """Clamp value to range [0.0, 1.0] and round to 4 decimal places."""
    return round(min(1.0, max(0.0, float(val))), 4)


def calculate_visual_axes(
    scores: EmotionalScores,
    nouls: EmotionalNouls,
    choices: EmotionalChoices,
) -> VisualLatentAxes:
    """Compute normalized visual latent axes from emotional scores, nouls, and choices."""
    t_weights = choices.temperament.weights
    vt_weights = choices.visual_tone.weights
    ep_weights = choices.energy_profile.weights

    # Form complexity: novelty, conflict, experimental vs control
    raw_complexity = (
        0.2
        + 0.35 * scores.novelty
        + 0.25 * scores.internal_conflict
        + (0.15 if nouls.appears_experimental else 0.0)
        - (0.15 if nouls.feels_under_control else 0.0)
        + 0.1 * t_weights.get("playful", 0.0)
    )

    # Symmetry: discipline, coherence, control vs chaos
    raw_symmetry = (
        0.3
        + 0.4 * scores.discipline
        + 0.35 * scores.coherence
        + (0.1 if nouls.feels_under_control else 0.0)
        - 0.45 * scores.chaos
    )

    # Fragmentation: chaos, fragility, overloaded, fragmented vs coherence
    raw_fragmentation = (
        0.1
        + 0.45 * scores.chaos
        + 0.25 * scores.fragility
        + (0.15 if nouls.feels_fragmented else 0.0)
        + (0.1 if nouls.feels_overloaded else 0.0)
        - 0.35 * scores.coherence
    )

    # Tension curvature: tension, conflict, volatility, coiled/turbulent
    raw_tension_curvature = (
        0.1
        + 0.45 * scores.tension
        + 0.3 * scores.internal_conflict
        + 0.25 * scores.volatility
        + 0.1 * ep_weights.get("coiled", 0.0)
        + 0.1 * ep_weights.get("turbulent", 0.0)
    )

    # Texture density: tension, volatility, dense tone, turbulent energy
    raw_texture_density = (
        0.15
        + 0.3 * scores.tension
        + 0.25 * scores.volatility
        + 0.25 * vt_weights.get("dense", 0.0)
        + 0.15 * ep_weights.get("turbulent", 0.0)
    )

    # Luminosity: novelty, resilient, luminous tone vs austere/brooding tone
    raw_luminosity = (
        0.35
        + 0.25 * scores.novelty
        + (0.15 if nouls.feels_resilient else 0.0)
        + 0.4 * vt_weights.get("luminous", 0.0)
        - 0.2 * vt_weights.get("austere", 0.0)
        - 0.15 * t_weights.get("brooding", 0.0)
    )

    # Contrast: identity strength, tension, turbulent/coiled energy
    raw_contrast = (
        0.2
        + 0.35 * scores.identity_strength
        + 0.3 * scores.tension
        + 0.15 * ep_weights.get("turbulent", 0.0)
        + 0.1 * ep_weights.get("coiled", 0.0)
    )

    # Sharpness: discipline, maturity, austere tone vs diffused energy
    raw_sharpness = (
        0.2
        + 0.35 * scores.discipline
        + 0.3 * scores.maturity
        + 0.2 * vt_weights.get("austere", 0.0)
        - 0.25 * ep_weights.get("diffused", 0.0)
    )

    # Visual rhythm: discipline, coherence, focused/static energy vs chaos
    raw_visual_rhythm = (
        0.25
        + 0.4 * scores.discipline
        + 0.35 * scores.coherence
        + 0.15 * ep_weights.get("focused", 0.0)
        + 0.1 * ep_weights.get("static", 0.0)
        - 0.45 * scores.chaos
    )

    # Compositional balance: coherence, maturity, stable vs volatility
    raw_compositional_balance = (
        0.2
        + 0.4 * scores.coherence
        + 0.35 * scores.maturity
        + (0.15 if nouls.feels_stable else 0.0)
        - 0.3 * scores.volatility
    )

    # Biological vs mechanical (0.0 = bio/organic, 1.0 = mechanical)
    raw_bio_vs_mech = (
        0.35
        + 0.4 * scores.discipline
        + 0.3 * scores.maturity
        - 0.25 * scores.novelty
        - (0.15 if nouls.appears_experimental else 0.0)
        - 0.15 * t_weights.get("playful", 0.0)
    )

    # Ornamental load: novelty, playful vs discipline
    raw_ornamental_load = (
        0.25
        + 0.3 * scores.novelty
        + 0.25 * t_weights.get("playful", 0.0)
        - 0.35 * scores.discipline
    )

    # Opacity: maturity, identity strength vs fragility, delicate tone
    raw_opacity = (
        0.3
        + 0.35 * scores.maturity
        + 0.35 * scores.identity_strength
        - 0.3 * scores.fragility
        - 0.2 * vt_weights.get("delicate", 0.0)
    )

    # Layering: maturity, coherence, dense/monumental tone
    raw_layering = (
        0.2
        + 0.35 * scores.maturity
        + 0.3 * scores.coherence
        + 0.15 * vt_weights.get("dense", 0.0)
        + 0.15 * vt_weights.get("monumental", 0.0)
    )

    return VisualLatentAxes(
        form_complexity=_clamp(raw_complexity),
        symmetry=_clamp(raw_symmetry),
        fragmentation=_clamp(raw_fragmentation),
        tension_curvature=_clamp(raw_tension_curvature),
        texture_density=_clamp(raw_texture_density),
        luminosity=_clamp(raw_luminosity),
        contrast=_clamp(raw_contrast),
        sharpness=_clamp(raw_sharpness),
        visual_rhythm=_clamp(raw_visual_rhythm),
        compositional_balance=_clamp(raw_compositional_balance),
        biological_vs_mechanical=_clamp(raw_bio_vs_mech),
        ornamental_load=_clamp(raw_ornamental_load),
        opacity=_clamp(raw_opacity),
        layering=_clamp(raw_layering),
    )
