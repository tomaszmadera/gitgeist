"""Unit tests for Visual Latent Profile schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gitgeist.schemas.visual_latent import (
    MaterialityDistribution,
    VisualLatentAxes,
    VisualLatentProfile,
)


def test_visual_latent_axes_valid() -> None:
    """Test creating VisualLatentAxes with valid boundary values."""
    axes = VisualLatentAxes(
        form_complexity=0.5,
        symmetry=0.8,
        fragmentation=0.2,
        tension_curvature=0.4,
        texture_density=0.6,
        luminosity=0.7,
        contrast=0.5,
        sharpness=0.9,
        visual_rhythm=0.75,
        compositional_balance=0.85,
        biological_vs_mechanical=0.65,
        ornamental_load=0.3,
        opacity=0.95,
        layering=0.7,
    )
    assert axes.form_complexity == 0.5
    assert axes.symmetry == 0.8
    assert axes.sharpness == 0.9


def test_visual_latent_axes_bounds() -> None:
    """Test that out-of-range values raise ValidationError."""
    valid_kwargs = {
        "form_complexity": 0.5,
        "symmetry": 0.5,
        "fragmentation": 0.5,
        "tension_curvature": 0.5,
        "texture_density": 0.5,
        "luminosity": 0.5,
        "contrast": 0.5,
        "sharpness": 0.5,
        "visual_rhythm": 0.5,
        "compositional_balance": 0.5,
        "biological_vs_mechanical": 0.5,
        "ornamental_load": 0.5,
        "opacity": 0.5,
        "layering": 0.5,
    }

    with pytest.raises(ValidationError):
        VisualLatentAxes(**{**valid_kwargs, "form_complexity": -0.1})

    with pytest.raises(ValidationError):
        VisualLatentAxes(**{**valid_kwargs, "symmetry": 1.1})


def test_visual_latent_axes_frozen() -> None:
    """Test that VisualLatentAxes is immutable."""
    axes = VisualLatentAxes(
        form_complexity=0.5,
        symmetry=0.5,
        fragmentation=0.5,
        tension_curvature=0.5,
        texture_density=0.5,
        luminosity=0.5,
        contrast=0.5,
        sharpness=0.5,
        visual_rhythm=0.5,
        compositional_balance=0.5,
        biological_vs_mechanical=0.5,
        ornamental_load=0.5,
        opacity=0.5,
        layering=0.5,
    )
    with pytest.raises(ValidationError):
        axes.form_complexity = 0.8  # type: ignore[misc]


def test_materiality_distribution_valid() -> None:
    """Test valid MaterialityDistribution with normalized weights."""
    dist = MaterialityDistribution(
        weights={
            "organic": 0.2,
            "mechanical": 0.5,
            "crystalline": 0.2,
            "ethereal": 0.1,
        },
        dominant="mechanical",
    )
    assert dist.dominant == "mechanical"
    assert dist.weights["mechanical"] == 0.5


def test_materiality_distribution_sum_validation() -> None:
    """Test that weights not summing to 1.0 raise ValidationError."""
    with pytest.raises(ValidationError):
        MaterialityDistribution(
            weights={
                "organic": 0.2,
                "mechanical": 0.4,
                "crystalline": 0.2,
                "ethereal": 0.1,
            },
            dominant="mechanical",
        )


def test_materiality_distribution_dominant_validation() -> None:
    """Test that dominant must match max weight."""
    with pytest.raises(ValidationError):
        MaterialityDistribution(
            weights={
                "organic": 0.6,
                "mechanical": 0.4,
            },
            dominant="mechanical",
        )


def test_visual_latent_profile_creation_and_frozen() -> None:
    """Test creating VisualLatentProfile and verifying immutability."""
    axes = VisualLatentAxes(
        form_complexity=0.3,
        symmetry=0.7,
        fragmentation=0.2,
        tension_curvature=0.4,
        texture_density=0.5,
        luminosity=0.6,
        contrast=0.5,
        sharpness=0.8,
        visual_rhythm=0.7,
        compositional_balance=0.8,
        biological_vs_mechanical=0.7,
        ornamental_load=0.2,
        opacity=0.9,
        layering=0.6,
    )
    materiality = MaterialityDistribution(
        weights={"organic": 0.1, "mechanical": 0.7, "crystalline": 0.1, "ethereal": 0.1},
        dominant="mechanical",
    )
    profile = VisualLatentProfile(
        axes=axes,
        materiality=materiality,
        dominant_features=["high sharpness", "high symmetry", "low fragmentation"],
    )
    assert profile.materiality.dominant == "mechanical"
    assert len(profile.dominant_features) == 3

    with pytest.raises(ValidationError):
        profile.dominant_features = ["other"]  # type: ignore[misc]


def test_materiality_distribution_edge_validations() -> None:
    """Test empty weights, out of range values, and missing dominant key."""
    # Empty weights
    with pytest.raises(ValidationError):
        MaterialityDistribution(weights={}, dominant="mechanical")

    # Weight out of range
    with pytest.raises(ValidationError):
        MaterialityDistribution(
            weights={"organic": -0.1, "mechanical": 1.1},
            dominant="mechanical",
        )

    # Dominant not in weights
    with pytest.raises(ValidationError):
        MaterialityDistribution(
            weights={"organic": 0.5, "mechanical": 0.5},
            dominant="crystalline",
        )


def test_visual_latent_profile_serialization_roundtrip() -> None:
    """Test JSON serialization and deserialization round-trip for VisualLatentProfile."""
    axes = VisualLatentAxes(
        form_complexity=0.4,
        symmetry=0.6,
        fragmentation=0.3,
        tension_curvature=0.5,
        texture_density=0.4,
        luminosity=0.7,
        contrast=0.6,
        sharpness=0.75,
        visual_rhythm=0.65,
        compositional_balance=0.7,
        biological_vs_mechanical=0.8,
        ornamental_load=0.25,
        opacity=0.85,
        layering=0.6,
    )
    materiality = MaterialityDistribution(
        weights={"organic": 0.2, "mechanical": 0.5, "crystalline": 0.2, "ethereal": 0.1},
        dominant="mechanical",
    )
    profile = VisualLatentProfile(
        axes=axes,
        materiality=materiality,
        dominant_features=["high sharpness", "high luminosity"],
    )

    json_str = profile.model_dump_json()
    restored = VisualLatentProfile.model_validate_json(json_str)

    assert restored == profile
    assert restored.axes == profile.axes
    assert restored.materiality == profile.materiality
    assert restored.dominant_features == profile.dominant_features
