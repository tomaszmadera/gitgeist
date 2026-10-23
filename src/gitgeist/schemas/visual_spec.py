"""Renderer-neutral scene description, in unit-circle footprint coordinates."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gitgeist.schemas.traits import Traits, Unit

UserSeed = Annotated[int, Field(ge=0, le=2**63 - 1, strict=True)]
HashSeed = Annotated[int, Field(ge=0, le=2**64 - 1, strict=True)]
Finite = Annotated[float, Field(allow_inf_nan=False)]
Hue = Annotated[float, Field(ge=0, lt=360)]
Phase = Annotated[float, Field(ge=0, lt=1)]


class SpecPart(BaseModel):
    """Strict, frozen base for every scene part."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class SeedInfo(SpecPart):
    identity_seed: str = Field(pattern=r"^[0-9a-f]{64}$")
    user_seed: UserSeed | None
    style_seed: HashSeed
    effective_seed: HashSeed


class Footprint(SpecPart):
    coverage: float = Field(ge=0.25, le=0.85)
    element_count: int = Field(ge=40, le=600)


class SpecMass(SpecPart):
    name: str
    is_merged: bool
    file_share: Unit
    churn_share: Unit
    language: str | None
    hue: Hue | None
    x: Finite
    y: Finite
    radius: float = Field(ge=0, le=1)


class Rings(SpecPart):
    first_year: int | None
    thickness: list[Unit] = Field(max_length=40)


class Palette(SpecPart):
    mode: Literal["language"]
    saturation: float = Field(ge=0.10, le=0.85)
    hue_offset: float = Field(ge=-45, le=45)


class Knot(SpecPart):
    mass_index: int = Field(ge=0)
    path: str
    offset_x: Finite
    offset_y: Finite
    radius: float = Field(ge=0.15, le=0.50)
    flicker: Unit


class StrandPath(SpecPart):
    phase: Phase
    curvature: float = Field(ge=-1, le=1)


class Strands(SpecPart):
    count: int = Field(ge=1, le=12)
    paths: list[StrandPath]

    @model_validator(mode="after")
    def matching_count(self) -> "Strands":
        if len(self.paths) != self.count:
            raise ValueError("paths length must equal count")
        return self


class CrackMark(SpecPart):
    mass_index: int = Field(ge=0)
    u: Unit
    v: Phase
    angle: Hue


class Cracks(SpecPart):
    count: int = Field(ge=0, le=60)
    marks: list[CrackMark]

    @model_validator(mode="after")
    def matching_count(self) -> "Cracks":
        if len(self.marks) != self.count:
            raise ValueError("marks length must equal count")
        return self


class Hatching(SpecPart):
    coverage: float = Field(ge=0, le=0.60)


class Edge(SpecPart):
    blur_px: float = Field(ge=0, le=6)
    jitter: float = Field(ge=0, le=0.25)


class Topology(SpecPart):
    nesting_levels: int = Field(ge=0, le=3)


class Motion(SpecPart):
    speed_hz: float = Field(ge=0.05, le=1.2)
    loop_seconds: Literal[12.0]
    pulse: list[Unit]


class VisualSpec(SpecPart):
    schema_version: Literal["1"]
    representation: Literal["abstract", "character"]
    style: str
    style_requested: str
    variety: Literal["low", "medium", "high"]
    seeds: SeedInfo
    traits: Traits
    footprint: Footprint
    masses: list[SpecMass] = Field(max_length=8)
    rings: Rings
    palette: Palette
    knot: Knot | None
    strands: Strands
    cracks: Cracks
    hatching: Hatching
    edge: Edge
    topology: Topology
    motion: Motion

    @model_validator(mode="after")
    def scene_references(self) -> "VisualSpec":
        if self.knot is not None and self.knot.mass_index >= len(self.masses):
            raise ValueError("knot mass_index must point into masses")
        if any(mark.mass_index >= len(self.masses) for mark in self.cracks.marks):
            raise ValueError("crack mass_index must point into masses")
        maximum = {"low": 10, "medium": 25, "high": 45}[self.variety]
        if abs(self.palette.hue_offset) > maximum:
            raise ValueError("hue_offset exceeds variety maximum")
        return self
