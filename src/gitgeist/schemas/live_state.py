"""Pydantic v2 schemas of the live scenes: the abstract ``orbits`` and the character ``creature``."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gitgeist._version import current_engine_version
from gitgeist.schemas.visual_spec import VisualSpec

Finite = Annotated[float, Field(allow_inf_nan=False)]


class HoverDetail(BaseModel):
    """Text shown when the pointer is over one mass of the abstract portrait."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mass_index: int = Field(ge=0, description="Index into scene.spec.masses")
    label: str = Field(description='"." for root files, the directory name, or "other (merged)"')
    file_count: int = Field(ge=0)
    file_share_percent: int = Field(ge=0, le=100)
    top_hotspot: str | None = Field(description="Path of the top hotspot when it belongs to this mass")


class OrbitsScene(BaseModel):
    """Abstract live portrait in the ``orbits`` style: the VisualSpec plus HUD and hover text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1"]
    representation: Literal["abstract"]
    repository_name: str | None
    engine_version: str = Field(default_factory=current_engine_version)
    caption: bool
    conclusions: list[str] = Field(max_length=3, description="Plain HUD phrases; empty when caption is False")
    hover: list[HoverDetail] = Field(description="One entry per mass; empty when caption is False")
    spec: VisualSpec


class CreatureTorso(BaseModel):
    """The torso: the largest mass, an upright ellipse (footprint units, rest pose)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mass_index: int = Field(ge=0, description="Index into scene.spec.masses")
    x: Finite
    y: Finite
    rx: float = Field(gt=0, allow_inf_nan=False, description="Major semi-axis")
    ry: float = Field(gt=0, allow_inf_nan=False, description="Minor semi-axis")
    rotation_deg: Finite = Field(description="Direction of the major axis; 270 is upright, head up")

    @model_validator(mode="after")
    def major_axis_first(self) -> "CreatureTorso":
        if self.rx < self.ry:
            raise ValueError("rx is the major semi-axis and must be at least ry")
        return self


class CreatureSegment(BaseModel):
    """One limb segment, drawn from the end of the previous one."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    length: float = Field(gt=0, allow_inf_nan=False)
    half_width: float = Field(gt=0, allow_inf_nan=False)
    bend_deg: Finite = Field(description="Joint bend at the start of the segment, at rest")


class CreatureLimb(BaseModel):
    """A limb: a chain of segments ending in a round pad, which is the mass's body."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mass_index: int = Field(ge=0)
    root_x: Finite
    root_y: Finite
    root_angle_deg: Finite = Field(description="Direction of the first segment before its bend, world frame")
    segments: list[CreatureSegment] = Field(min_length=1, max_length=4)
    pad_radius: float = Field(gt=0, allow_inf_nan=False)
    sway_phase: float = Field(ge=0, lt=1)
    sway_amplitude_deg: float = Field(ge=0, allow_inf_nan=False)


class CreatureBody(BaseModel):
    """Body plan of the creature in footprint units: the torso and one limb per other mass."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    torso: CreatureTorso | None = Field(description="None when the repository has no masses")
    limbs: list[CreatureLimb]


class CreatureScene(BaseModel):
    """Character live portrait in the ``creature`` style: the VisualSpec, the body plan, HUD and hover text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1"]
    representation: Literal["character"]
    repository_name: str | None
    engine_version: str = Field(default_factory=current_engine_version)
    caption: bool
    conclusions: list[str] = Field(max_length=3, description="Plain HUD phrases; empty when caption is False")
    hover: list[HoverDetail] = Field(description="One entry per mass; empty when caption is False")
    body: CreatureBody
    spec: VisualSpec

    @model_validator(mode="after")
    def body_matches_spec(self) -> "CreatureScene":
        if self.spec.style != "creature":
            raise ValueError("a creature scene needs a spec in the creature style")
        masses = len(self.spec.masses)
        parts = ([self.body.torso.mass_index] if self.body.torso is not None else []) + [
            limb.mass_index for limb in self.body.limbs
        ]
        if sorted(parts) != list(range(masses)):
            raise ValueError("every mass of the spec must appear exactly once in the body (torso or one limb)")
        segments = 1 + self.spec.topology.nesting_levels
        if any(len(limb.segments) != segments for limb in self.body.limbs):
            raise ValueError("every limb must have 1 + spec.topology.nesting_levels segments")
        return self
