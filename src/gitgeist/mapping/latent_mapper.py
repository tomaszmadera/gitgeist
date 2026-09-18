"""Facade and orchestrator for visual latent profile mapping."""

from __future__ import annotations

from gitgeist.mapping.axes import calculate_visual_axes
from gitgeist.mapping.dominant_features import extract_dominant_features
from gitgeist.mapping.materiality import calculate_materiality
from gitgeist.schemas.emotional import EmotionalState
from gitgeist.schemas.visual_latent import VisualLatentProfile


def map_emotional_to_latent(
    state: EmotionalState,
    engine_version: str | None = None,
) -> VisualLatentProfile:
    """Translate an EmotionalState into a deterministic VisualLatentProfile."""
    if not isinstance(state, EmotionalState):
        raise TypeError(f"Expected EmotionalState, got {type(state).__name__}")

    axes = calculate_visual_axes(state.scores, state.nouls, state.choices)
    materiality = calculate_materiality(axes, state.scores, state.nouls, state.choices)
    dominant_features = extract_dominant_features(axes)

    kwargs = {
        "axes": axes,
        "materiality": materiality,
        "dominant_features": dominant_features,
        "calculated_at": state.calculated_at,
        "source_commit": state.source_commit,
    }
    if engine_version is not None:
        kwargs["engine_version"] = engine_version

    return VisualLatentProfile(**kwargs)
