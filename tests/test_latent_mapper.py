"""Tests for visual latent mapper module and facade."""

from __future__ import annotations

import pytest

from gitgeist.interpretation import evaluate_emotional_state
from gitgeist.mapping import map_emotional_to_latent
from gitgeist.schemas.emotional import (
    ChoiceDistribution,
    EmotionalChoices,
    EmotionalNouls,
    EmotionalScores,
    EmotionalState,
)
from gitgeist.schemas.visual_latent import VisualLatentAxes, VisualLatentProfile
from tests.fixtures.builder import create_clean_modular_repo


def create_sample_emotional_state(
    scores_override: dict[str, float] | None = None,
    nouls_override: dict[str, bool] | None = None,
    temperament_dominant: str = "disciplined",
    visual_tone_dominant: str = "austere",
    energy_profile_dominant: str = "focused",
) -> EmotionalState:
    """Helper to construct an EmotionalState for tests."""
    base_scores = {
        "coherence": 0.7,
        "maturity": 0.6,
        "volatility": 0.3,
        "fragility": 0.2,
        "novelty": 0.4,
        "discipline": 0.8,
        "tension": 0.3,
        "chaos": 0.2,
        "identity_strength": 0.7,
        "internal_conflict": 0.2,
    }
    if scores_override:
        base_scores.update(scores_override)

    base_nouls = {
        "appears_experimental": False,
        "feels_stable": True,
        "feels_overloaded": False,
        "feels_under_control": True,
        "feels_fragmented": False,
        "feels_unfinished": False,
        "feels_resilient": True,
    }
    if nouls_override:
        base_nouls.update(nouls_override)

    def make_choice(dominant: str, options: list[str]) -> ChoiceDistribution:
        weights = {}
        rem = 0.4 / (len(options) - 1) if len(options) > 1 else 0.0
        for opt in options:
            weights[opt] = 0.6 if opt == dominant else round(rem, 4)
        diff = 1.0 - sum(weights.values())
        weights[dominant] = round(weights[dominant] + diff, 4)
        return ChoiceDistribution(weights=weights, dominant=dominant)

    temperament = make_choice(
        temperament_dominant,
        ["calm", "restless", "disciplined", "playful", "brooding", "proud", "anxious", "mysterious"],
    )
    visual_tone = make_choice(
        visual_tone_dominant,
        ["luminous", "austere", "dense", "delicate", "monumental", "fractured", "flowing"],
    )
    energy_profile = make_choice(
        energy_profile_dominant,
        ["static", "pulsing", "coiled", "diffused", "turbulent", "focused"],
    )

    return EmotionalState(
        scores=EmotionalScores(**base_scores),
        nouls=EmotionalNouls(**base_nouls),
        choices=EmotionalChoices(
            temperament=temperament,
            visual_tone=visual_tone,
            energy_profile=energy_profile,
        ),
    )


def test_map_emotional_to_latent_basic() -> None:
    """Test standard mapping returns a valid VisualLatentProfile."""
    state = create_sample_emotional_state()
    profile = map_emotional_to_latent(state)

    assert isinstance(profile, VisualLatentProfile)
    # Check all continuous axes are within [0.0, 1.0]
    for field_name in VisualLatentAxes.model_fields:
        val = getattr(profile.axes, field_name)
        assert 0.0 <= val <= 1.0, f"Axis {field_name}={val} out of bounds"

    # Check materiality weights sum to 1.0
    total_materiality = sum(profile.materiality.weights.values())
    assert abs(total_materiality - 1.0) < 1e-4
    assert profile.materiality.dominant in profile.materiality.weights

    # Check dominant features
    assert len(profile.dominant_features) > 0


def test_map_emotional_to_latent_determinism() -> None:
    """Test that map_emotional_to_latent is strictly deterministic."""
    state = create_sample_emotional_state()
    p1 = map_emotional_to_latent(state)
    p2 = map_emotional_to_latent(state)

    assert p1.axes == p2.axes
    assert p1.materiality == p2.materiality
    assert p1.dominant_features == p2.dominant_features
    assert p1 == p2


def test_map_emotional_to_latent_invalid_type() -> None:
    """Test passing invalid type raises TypeError."""
    with pytest.raises(TypeError):
        map_emotional_to_latent("not an emotional state")  # type: ignore[arg-type]


def test_monotonic_and_directional_rules() -> None:
    """Test that key business rules govern axis movements."""
    # Chaos increases fragmentation
    low_chaos_state = create_sample_emotional_state(scores_override={"chaos": 0.1, "coherence": 0.8})
    high_chaos_state = create_sample_emotional_state(scores_override={"chaos": 0.9, "coherence": 0.2})
    p_low = map_emotional_to_latent(low_chaos_state)
    p_high = map_emotional_to_latent(high_chaos_state)

    assert p_high.axes.fragmentation > p_low.axes.fragmentation
    assert p_high.axes.symmetry < p_low.axes.symmetry

    # Discipline and coherence increase visual_rhythm
    low_disc = create_sample_emotional_state(scores_override={"discipline": 0.1, "coherence": 0.2})
    high_disc = create_sample_emotional_state(scores_override={"discipline": 0.9, "coherence": 0.9})
    p_disc_low = map_emotional_to_latent(low_disc)
    p_disc_high = map_emotional_to_latent(high_disc)

    assert p_disc_high.axes.visual_rhythm > p_disc_low.axes.visual_rhythm

    # Visual tone 'luminous' increases luminosity
    dark_state = create_sample_emotional_state(visual_tone_dominant="austere")
    luminous_state = create_sample_emotional_state(visual_tone_dominant="luminous")
    assert map_emotional_to_latent(luminous_state).axes.luminosity > map_emotional_to_latent(dark_state).axes.luminosity


def test_materiality_mapping_tendencies() -> None:
    """Test that materiality responds to state dimensions."""
    # High discipline + maturity -> mechanical
    mech_state = create_sample_emotional_state(
        scores_override={"discipline": 0.9, "maturity": 0.9, "novelty": 0.1},
        temperament_dominant="disciplined",
    )
    p_mech = map_emotional_to_latent(mech_state)
    assert p_mech.materiality.dominant == "mechanical"

    # High novelty + playful + appears_experimental -> organic
    organic_state = create_sample_emotional_state(
        scores_override={"novelty": 0.9, "discipline": 0.2, "maturity": 0.1},
        nouls_override={"appears_experimental": True},
        temperament_dominant="playful",
    )
    p_org = map_emotional_to_latent(organic_state)
    assert p_org.materiality.dominant == "organic"


def test_materiality_deterministic_tie_breaking() -> None:
    """Test that ties in materiality weights are deterministically resolved alphabetically."""
    from gitgeist.mapping.materiality import calculate_materiality

    # Perfectly balanced state to produce identical raw weights across all categories
    balanced_scores = EmotionalScores(**{k: 0.5 for k in EmotionalScores.model_fields})
    balanced_nouls = EmotionalNouls()
    balanced_choices = EmotionalChoices(
        temperament=ChoiceDistribution(
            weights={"calm": 0.125, "restless": 0.125, "disciplined": 0.125, "playful": 0.125,
                     "brooding": 0.125, "proud": 0.125, "anxious": 0.125, "mysterious": 0.125},
            dominant="anxious",
        ),
        visual_tone=ChoiceDistribution(
            weights={"luminous": 0.1429, "austere": 0.1429, "dense": 0.1428, "delicate": 0.1428,
                     "monumental": 0.1429, "fractured": 0.1428, "flowing": 0.1429},
            dominant="austere",
        ),
        energy_profile=ChoiceDistribution(
            weights={"static": 0.1667, "pulsing": 0.1667, "coiled": 0.1666,
                     "diffused": 0.1667, "turbulent": 0.1666, "focused": 0.1667},
            dominant="static",
        ),
    )
    axes = VisualLatentAxes(**{k: 0.5 for k in VisualLatentAxes.model_fields})
    dist = calculate_materiality(axes, balanced_scores, balanced_nouls, balanced_choices)

    assert dist.dominant in dist.weights
    assert dist.weights[dist.dominant] == max(dist.weights.values())
    # Verify no validation error occurs and dominant is the alphabetical winner among maximal weights
    max_w = max(dist.weights.values())
    tied = [k for k, w in dist.weights.items() if w == max_w]
    assert dist.dominant == min(tied)


def test_engine_version_handling() -> None:
    """Test default and overridden engine_version in map_emotional_to_latent."""
    state = create_sample_emotional_state()
    profile_default = map_emotional_to_latent(state)
    assert profile_default.engine_version == "0.1.0-beta.2"

    profile_custom = map_emotional_to_latent(state, engine_version="0.2.0")
    assert profile_custom.engine_version == "0.2.0"


def test_boundary_extremes() -> None:
    """Test stability at 0.0 and 1.0 boundary extremes."""
    zeros_scores = {k: 0.0 for k in EmotionalScores.model_fields}
    zeros_state = create_sample_emotional_state(scores_override=zeros_scores)
    p_zero = map_emotional_to_latent(zeros_state)
    for field_name in VisualLatentAxes.model_fields:
        val = getattr(p_zero.axes, field_name)
        assert 0.0 <= val <= 1.0

    ones_scores = {k: 1.0 for k in EmotionalScores.model_fields}
    ones_state = create_sample_emotional_state(scores_override=ones_scores)
    p_one = map_emotional_to_latent(ones_state)
    for field_name in VisualLatentAxes.model_fields:
        val = getattr(p_one.axes, field_name)
        assert 0.0 <= val <= 1.0


def test_end_to_end_integration(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Test full pipeline: features -> emotional_state -> visual_latent_profile."""
    from gitgeist.features import extract_features

    repo_dir = tmp_path_factory.mktemp("test_repo")
    create_clean_modular_repo(repo_dir)

    features = extract_features(repo_dir)
    emotional_state = evaluate_emotional_state(features)
    latent_profile = map_emotional_to_latent(emotional_state)

    assert isinstance(latent_profile, VisualLatentProfile)
    assert latent_profile.calculated_at == emotional_state.calculated_at
    assert latent_profile.source_commit == emotional_state.source_commit
