"""Deterministic prompt composer for the prompt_to_image generation mode."""

from __future__ import annotations

from typing import Literal

from gitgeist.schemas.emotional import EmotionalState
from gitgeist.schemas.visual_latent import VisualLatentProfile

RepresentationMode = Literal["abstract", "character"]

_SCORE_NAMES = (
    "coherence",
    "maturity",
    "volatility",
    "fragility",
    "novelty",
    "discipline",
    "tension",
    "chaos",
    "identity_strength",
    "internal_conflict",
)

_AXIS_NAMES = (
    "form_complexity",
    "symmetry",
    "fragmentation",
    "tension_curvature",
    "texture_density",
    "luminosity",
    "contrast",
    "sharpness",
    "visual_rhythm",
    "compositional_balance",
    "biological_vs_mechanical",
    "ornamental_load",
    "opacity",
    "layering",
)

_MODE_DESCRIPTIONS = {
    "character": (
        "Representation mode: character\n"
        "The portrait is a single emergent being whose silhouette, proportions, posture, "
        "surface and aura arise from the traits above."
    ),
    "abstract": (
        "Representation mode: abstract\n"
        "The portrait is an abstract composition whose masses, gradients, rhythm, "
        "texture and light arise from the traits above."
    ),
}


def _qualifier(value: float) -> str:
    if value <= 0.33:
        return "low"
    if value <= 0.66:
        return "medium"
    return "high"


def _validate_inputs(
    emotional_state: EmotionalState,
    profile: VisualLatentProfile,
    mode: str,
) -> None:
    if not isinstance(emotional_state, EmotionalState):
        raise TypeError(f"Expected EmotionalState, got {type(emotional_state).__name__}")
    if not isinstance(profile, VisualLatentProfile):
        raise TypeError(f"Expected VisualLatentProfile, got {type(profile).__name__}")
    if mode not in _MODE_DESCRIPTIONS:
        raise ValueError(
            f"Unsupported representation mode: {mode!r}. Must be 'abstract' or 'character'."
        )


def compose_prompt(
    emotional_state: EmotionalState,
    profile: VisualLatentProfile,
    mode: RepresentationMode = "abstract",
    repository_name: str | None = None,
) -> str:
    """Compose a deterministic image-generation prompt from repository profiles.

    Args:
        emotional_state: EmotionalState instance (Layer 2).
        profile: VisualLatentProfile instance (Layer 3).
        mode: Representation mode, either 'abstract' or 'character'.
        repository_name: Optional repository display name.

    Returns:
        The final prompt text. Identical inputs produce an identical prompt.

    Raises:
        TypeError: If emotional_state or profile have unexpected types.
        ValueError: If mode is not 'abstract' or 'character'.
    """
    _validate_inputs(emotional_state, profile, mode)

    lines: list[str] = []
    lines.append("Create a visual portrait of a software repository as an emergent form.")
    lines.append("Do not use cliched stereotypes or literal programmer symbols.")
    lines.append("")

    lines.append("Semantic identity:")
    if repository_name is not None:
        lines.append(f"- repository: {repository_name}")
    temperament = emotional_state.choices.temperament.dominant
    visual_tone = emotional_state.choices.visual_tone.dominant
    energy = emotional_state.choices.energy_profile.dominant
    lines.append(f"- temperament: {temperament}")
    lines.append(f"- visual tone: {visual_tone}")
    lines.append(f"- energy profile: {energy}")
    if profile.dominant_features:
        lines.append(f"- dominant features: {', '.join(profile.dominant_features)}")
    lines.append("")

    lines.append("Emotional state:")
    for name in _SCORE_NAMES:
        value = getattr(emotional_state.scores, name)
        lines.append(f"- {name}: {_qualifier(value)}")
    lines.append("")

    lines.append("Visual latent profile:")
    for name in _AXIS_NAMES:
        value = getattr(profile.axes, name)
        lines.append(f"- {name}: {_qualifier(value)}")
    lines.append(f"- dominant material: {profile.materiality.dominant}")
    lines.append("")

    lines.append(_MODE_DESCRIPTIONS[mode])
    lines.append("")

    lines.append("Consistency constraints:")
    lines.append("- The form must emerge from the combined traits, not from any single trait.")
    lines.append("- Keep proportions, rhythm and palette consistent with the stated profile.")
    lines.append("")

    lines.append("Negative constraints:")
    lines.append("- No literal programmer symbols such as code editors, terminals, logos or keyboards.")
    lines.append("- No mascot cliches, no text, no watermarks, no captions.")

    return "\n".join(lines)
