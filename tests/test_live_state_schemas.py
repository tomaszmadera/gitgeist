"""Tests for live state schemas (Pydantic v2)."""

import pytest
from pydantic import ValidationError

from gitgeist.schemas.live_state import (
    ColorPalette,
    GeometryParameters,
    LiveSimulationState,
    MotionDynamics,
)


def test_color_palette_valid():
    palette = ColorPalette(
        background="#0a0a0f",
        foreground="#f0f0f5",
        primary="#3b82f6",
        secondary="#8b5cf6",
        accent="#06b6d4",
        aura="rgba(6, 182, 212, 0.3)",
    )
    assert palette.background == "#0a0a0f"
    assert palette.foreground == "#f0f0f5"
    assert palette.primary == "#3b82f6"


def test_color_palette_invalid_color():
    with pytest.raises(ValidationError):
        ColorPalette(
            background="not-a-color",
            foreground="#ffffff",
            primary="#111111",
            secondary="#222222",
            accent="#333333",
            aura="#444444",
        )


def test_color_palette_frozen():
    palette = ColorPalette(
        background="#000000",
        foreground="#ffffff",
        primary="#111111",
        secondary="#222222",
        accent="#333333",
        aura="#444444",
    )
    with pytest.raises(ValidationError):
        palette.background = "#ffffff"  # type: ignore[misc]


def test_color_palette_rgba_alpha_formats():
    base = dict(
        background="#0a0a0f",
        foreground="#f0f0f5",
        primary="#3b82f6",
        secondary="#8b5cf6",
        accent="#06b6d4",
    )
    for aura in ("rgba(6, 182, 212, 1)", "rgba(6, 182, 212, 1.0)", "rgba(6, 182, 212, 1.00)", "rgba(6, 182, 212, 0.5)", "rgba(6, 182, 212, .5)"):
        palette = ColorPalette(aura=aura, **base)
        assert palette.aura == aura
    with pytest.raises(ValidationError):
        ColorPalette(aura="rgba(6, 182, 212, 1.5)", **base)


def test_motion_dynamics_valid():
    dyn = MotionDynamics(
        pulse_frequency=1.2,
        flow_speed=0.8,
        turbulence=0.4,
        breathing_amplitude=0.15,
    )
    assert dyn.pulse_frequency == 1.2
    assert dyn.flow_speed == 0.8


def test_motion_dynamics_negative_values():
    with pytest.raises(ValidationError):
        MotionDynamics(
            pulse_frequency=-0.5,
            flow_speed=0.8,
            turbulence=0.4,
            breathing_amplitude=0.15,
        )


def test_geometry_parameters_valid():
    geom = GeometryParameters(
        density=0.7,
        symmetry_order=4,
        fragmentation=0.2,
        sharpness=0.8,
        layer_count=3,
        curvature=0.5,
        organic_ratio=0.1,
    )
    assert geom.density == 0.7
    assert geom.symmetry_order == 4
    assert geom.layer_count == 3


def test_geometry_parameters_bounds():
    with pytest.raises(ValidationError):
        GeometryParameters(
            density=1.5,  # > 1.0
            symmetry_order=2,
            fragmentation=0.2,
            sharpness=0.8,
            layer_count=3,
            curvature=0.5,
            organic_ratio=0.1,
        )


def test_live_simulation_state_serialization():
    palette = ColorPalette(
        background="#0a0a0f",
        foreground="#f0f0f5",
        primary="#3b82f6",
        secondary="#8b5cf6",
        accent="#06b6d4",
        aura="rgba(6, 182, 212, 0.3)",
    )
    dyn = MotionDynamics(
        pulse_frequency=1.0,
        flow_speed=1.0,
        turbulence=0.3,
        breathing_amplitude=0.2,
    )
    geom = GeometryParameters(
        density=0.6,
        symmetry_order=2,
        fragmentation=0.3,
        sharpness=0.7,
        layer_count=4,
        curvature=0.4,
        organic_ratio=0.2,
    )
    state = LiveSimulationState(
        representation_mode="abstract",
        seed=123456,
        palette=palette,
        dynamics=dyn,
        geometry=geom,
        dominant_material="mechanical",
        engine_version="0.1.0-beta.3",
        repository_name="gitgeist",
    )
    assert state.representation_mode == "abstract"
    assert state.seed == 123456

    # Test serialization to dict and JSON
    d = state.model_dump()
    assert d["representation_mode"] == "abstract"
    assert d["palette"]["background"] == "#0a0a0f"

    json_str = state.model_dump_json()
    assert '"abstract"' in json_str
    assert '"#0a0a0f"' in json_str


def test_live_simulation_state_invalid_mode():
    palette = ColorPalette(
        background="#0a0a0f",
        foreground="#f0f0f5",
        primary="#3b82f6",
        secondary="#8b5cf6",
        accent="#06b6d4",
        aura="rgba(6, 182, 212, 0.3)",
    )
    dyn = MotionDynamics(
        pulse_frequency=1.0,
        flow_speed=1.0,
        turbulence=0.3,
        breathing_amplitude=0.2,
    )
    geom = GeometryParameters(
        density=0.6,
        symmetry_order=2,
        fragmentation=0.3,
        sharpness=0.7,
        layer_count=4,
        curvature=0.4,
        organic_ratio=0.2,
    )
    with pytest.raises(ValidationError):
        LiveSimulationState(
            representation_mode="invalid_mode",  # type: ignore[arg-type]
            seed=123,
            palette=palette,
            dynamics=dyn,
            geometry=geom,
            dominant_material="mechanical",
            engine_version="0.1.0-beta.3",
        )
