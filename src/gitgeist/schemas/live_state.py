"""Pydantic v2 schemas for live simulation state and render artifacts."""

import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from gitgeist._version import current_engine_version

COLOR_REGEX = re.compile(
    r"^(?:#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*(?:0(?:\.\d+)?|1(?:\.0+)?|\.\d+)\s*)?\))$"
)


class ColorPalette(BaseModel):
    """Harmonized color palette for live rendering."""

    model_config = ConfigDict(frozen=True)

    background: str = Field(description="Background canvas color")
    foreground: str = Field(description="Main foreground/stroke color")
    primary: str = Field(description="Primary element color")
    secondary: str = Field(description="Secondary element color")
    accent: str = Field(description="High-contrast accent color")
    aura: str = Field(description="Ambient glow or aura color")

    @field_validator("background", "foreground", "primary", "secondary", "accent", "aura")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if not COLOR_REGEX.match(value.strip()):
            raise ValueError(f"Invalid CSS color format: {value}")
        return value.strip()


class MotionDynamics(BaseModel):
    """Physical and time-based dynamics for live simulation animation."""

    model_config = ConfigDict(frozen=True)

    pulse_frequency: float = Field(ge=0.0, description="Base rhythm and pulse cycles per second")
    flow_speed: float = Field(ge=0.0, description="Rate of particle flow or movement drift")
    turbulence: float = Field(ge=0.0, description="Chaos and perturbation factor")
    breathing_amplitude: float = Field(ge=0.0, description="Scale amplitude of expansion/contraction")


class GeometryParameters(BaseModel):
    """Geometric structure and segmentation parameters."""

    model_config = ConfigDict(frozen=True)

    density: float = Field(ge=0.0, le=1.0, description="Element density or particle count factor")
    symmetry_order: int = Field(ge=1, description="Order of radial or rotational symmetry")
    fragmentation: float = Field(ge=0.0, le=1.0, description="Degree of dispersion and particle breakdown")
    sharpness: float = Field(ge=0.0, le=1.0, description="Edge sharpness vs blur/softness")
    layer_count: int = Field(ge=1, description="Number of visual or structural layers")
    curvature: float = Field(ge=0.0, le=1.0, description="Line curvature vs angular segments")
    organic_ratio: float = Field(ge=0.0, le=1.0, description="Organic curved forms (1.0) vs mechanical polygons (0.0)")


class LiveSimulationState(BaseModel):
    """Top-level immutable state specification for live rendering."""

    model_config = ConfigDict(frozen=True)

    representation_mode: Literal["abstract", "character"] = Field(
        description="Active representation mode"
    )
    seed: int = Field(description="Deterministic integer seed for pseudo-random visual features")
    palette: ColorPalette = Field(description="Color palette")
    dynamics: MotionDynamics = Field(description="Motion and rhythm parameters")
    geometry: GeometryParameters = Field(description="Geometric distribution parameters")
    dominant_material: str = Field(description="Dominant materiality identifier")
    engine_version: str = Field(
        default_factory=current_engine_version,
        description="Gitgeist engine version",
    )
    repository_name: str | None = Field(default=None, description="Analyzed repository name")
