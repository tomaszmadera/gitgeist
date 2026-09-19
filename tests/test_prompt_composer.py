"""Tests for the deterministic prompt composer."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from gitgeist.schemas.emotional import (
    ChoiceDistribution,
    EmotionalChoices,
    EmotionalNouls,
    EmotionalScores,
    EmotionalState,
)
from gitgeist.schemas.visual_latent import (
    MaterialityDistribution,
    VisualLatentAxes,
    VisualLatentProfile,
)
from gitgeist.render.prompt_composer import compose_prompt


def make_emotional_state() -> EmotionalState:
    scores = EmotionalScores(
        coherence=0.81,
        maturity=0.72,
        volatility=0.25,
        fragility=0.2,
        novelty=0.5,
        discipline=0.77,
        tension=0.3,
        chaos=0.15,
        identity_strength=0.69,
        internal_conflict=0.31,
    )
    choices = EmotionalChoices(
        temperament=ChoiceDistribution(
            weights={"calm": 0.4, "restless": 0.2, "proud": 0.2, "anxious": 0.2},
            dominant="calm",
        ),
        visual_tone=ChoiceDistribution(
            weights={"luminous": 0.5, "austere": 0.3, "dense": 0.2},
            dominant="luminous",
        ),
        energy_profile=ChoiceDistribution(
            weights={"focused": 0.6, "static": 0.4},
            dominant="focused",
        ),
    )
    return EmotionalState(scores=scores, nouls=EmotionalNouls(), choices=choices)


def make_profile() -> VisualLatentProfile:
    axes = VisualLatentAxes(
        form_complexity=0.7,
        symmetry=0.6,
        fragmentation=0.3,
        tension_curvature=0.4,
        texture_density=0.5,
        luminosity=0.6,
        contrast=0.7,
        sharpness=0.8,
        visual_rhythm=0.75,
        compositional_balance=0.8,
        biological_vs_mechanical=0.7,
        ornamental_load=0.2,
        opacity=0.85,
        layering=0.6,
    )
    materiality = MaterialityDistribution(
        weights={"organic": 0.1, "mechanical": 0.6, "crystalline": 0.2, "ethereal": 0.1},
        dominant="mechanical",
    )
    return VisualLatentProfile(
        axes=axes,
        materiality=materiality,
        dominant_features=["sharpness", "compositional_balance"],
    )


def test_compose_prompt_determinism():
    state = make_emotional_state()
    profile = make_profile()
    prompt1 = compose_prompt(state, profile, mode="character")
    prompt2 = compose_prompt(state, profile, mode="character")
    assert prompt1 == prompt2
    assert len(prompt1) > 0


def test_compose_prompt_excludes_timestamps():
    state_a = make_emotional_state()
    state_b = state_a.model_copy(
        update={"calculated_at": datetime(2000, 1, 1, tzinfo=timezone.utc)}
    )
    profile = make_profile()
    assert compose_prompt(state_a, profile) == compose_prompt(state_b, profile)


def test_compose_prompt_axis_qualifiers():
    state = make_emotional_state()
    profile = make_profile()
    prompt = compose_prompt(state, profile, mode="character")
    assert "coherence: high" in prompt
    assert "volatility: low" in prompt
    assert "novelty: medium" in prompt
    assert "form_complexity: high" in prompt
    assert "ornamental_load: low" in prompt


def test_compose_prompt_modes_differ():
    state = make_emotional_state()
    profile = make_profile()
    character_prompt = compose_prompt(state, profile, mode="character")
    abstract_prompt = compose_prompt(state, profile, mode="abstract")
    assert character_prompt != abstract_prompt
    assert "character" in character_prompt
    assert "abstract" in abstract_prompt


def test_compose_prompt_materiality_and_choices_verbal():
    state = make_emotional_state()
    profile = make_profile()
    prompt = compose_prompt(state, profile)
    assert "mechanical" in prompt
    assert "calm" in prompt
    assert "luminous" in prompt
    assert "focused" in prompt
    assert "0.6" not in prompt
    assert "0.4" not in prompt


def test_compose_prompt_negative_constraints():
    state = make_emotional_state()
    profile = make_profile()
    prompt = compose_prompt(state, profile)
    assert "programmer symbols" in prompt
    assert "mascot" in prompt


def test_compose_prompt_consistency_constraints():
    state = make_emotional_state()
    profile = make_profile()
    prompt = compose_prompt(state, profile)
    assert "Consistency constraints:" in prompt
    assert "emerge from the combined traits" in prompt


def test_compose_prompt_axis_change_changes_prompt():
    state = make_emotional_state()
    profile = make_profile()
    changed_axes = profile.axes.model_copy(update={"fragmentation": 0.9})
    changed_profile = profile.model_copy(update={"axes": changed_axes})
    assert compose_prompt(state, profile) != compose_prompt(state, changed_profile)


def test_compose_prompt_optional_fields():
    state = make_emotional_state()
    axes = VisualLatentAxes(
        form_complexity=0.0,
        symmetry=1.0,
        fragmentation=0.0,
        tension_curvature=1.0,
        texture_density=0.0,
        luminosity=1.0,
        contrast=0.0,
        sharpness=1.0,
        visual_rhythm=0.0,
        compositional_balance=1.0,
        biological_vs_mechanical=0.0,
        ornamental_load=1.0,
        opacity=0.0,
        layering=1.0,
    )
    profile = VisualLatentProfile(
        axes=axes,
        materiality=MaterialityDistribution(weights={"ethereal": 1.0}, dominant="ethereal"),
        dominant_features=[],
    )
    prompt = compose_prompt(state, profile, repository_name=None)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "ethereal" in prompt


def test_compose_prompt_rejects_wrong_types():
    profile = make_profile()
    state = make_emotional_state()
    with pytest.raises(TypeError):
        compose_prompt("not-a-state", profile)
    with pytest.raises(TypeError):
        compose_prompt(state, "not-a-profile")


def test_compose_prompt_rejects_unknown_mode():
    state = make_emotional_state()
    profile = make_profile()
    with pytest.raises(ValueError):
        compose_prompt(state, profile, mode="surreal")
