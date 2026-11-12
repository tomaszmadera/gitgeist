"""Pydantic v2 schemas of the live scenes: the abstract ``orbits``, the character ``creature`` and ``anatomy``."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gitgeist._version import current_engine_version
from gitgeist.schemas.anatomy import LanguageFacts
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


Radius = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class AnatomyLibraryVersions(BaseModel):
    """Installed versions of the layout libraries; the scene is byte-identical only for the same versions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    networkx: str
    numpy: str


class AnatomyCounts(BaseModel):
    """Raw counts shown by the HUD. No share, score or ranking is stored."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    files: int = Field(ge=0, description="Scanned files")
    edges: int = Field(ge=0, description="Internal dependency edges of the scan, foreign files included")
    bodies: int = Field(ge=0)
    organs_in_largest_body: int = Field(ge=0, description="Organs of bodies[0]; 0 without bodies")
    dust: int = Field(ge=0)
    cysts: int = Field(ge=0)
    lines: int = Field(ge=0, description="Lines of all scanned files")
    foreign_lines: int = Field(ge=0, description="Lines of foreign files")
    unblamed: int = Field(ge=0, description="Files without line_years (binary)")


class AnatomyBlameYears(BaseModel):
    """First and last author year seen by blame over all scanned files."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    first: int
    last: int

    @model_validator(mode="after")
    def ordered(self) -> "AnatomyBlameYears":
        if self.first > self.last:
            raise ValueError("first blame year must not be after the last")
        return self


class AnatomyFileState(BaseModel):
    """Raw facts of one own file, the data its cell or dust speck is drawn from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    r: Radius = Field(description="Cell radius in layout units: 0.55 * sqrt(max(lines, 4))")
    lines: int = Field(ge=1)
    changes: int = Field(ge=0)
    line_years: dict[int, int] = Field(description="Blamed lines per author year, ascending years")
    test: bool
    edges: int = Field(ge=0, description="Scan edges touching the file, edges to foreign files included")
    test_edges: int = Field(ge=0, description="Test files with an edge to this file")
    facts: LanguageFacts


class AnatomyCell(AnatomyFileState):
    """A cell of an organ; x and y are absolute layout coordinates of its centre."""

    x: Finite
    y: Finite


class AnatomyOrgan(BaseModel):
    """A dependency community of one body; cells sorted by lines descending, then path."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    x: Finite
    y: Finite
    r: Radius = Field(description="1.15 * sqrt(sum of cell radii squared) + 2")
    cells: list[AnatomyCell] = Field(min_length=1)


class AnatomyBody(BaseModel):
    """A connected component of two or more own files; organs sorted by lines descending, then first path."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    x: Finite
    y: Finite
    r: Radius = Field(description="Extent from the body centre that encloses every organ and cell")
    organs: list[AnatomyOrgan] = Field(min_length=1)


class AnatomyTendon(BaseModel):
    """Dependencies between two organs of one body."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    body: int = Field(ge=0, description="Index into bodies")
    source: int = Field(ge=0, description="Organ index within the body, below target")
    target: int = Field(ge=0)
    edges: int = Field(ge=1, description="Dependency edges between the two organs")
    width: Radius = Field(description="log1p(edges), layout units")

    @model_validator(mode="after")
    def ordered_organs(self) -> "AnatomyTendon":
        if not self.source < self.target:
            raise ValueError("tendon source organ must be below target")
        return self


class AnatomyDust(AnatomyFileState):
    """A file with no internal dependency among own files.

    x and y are fractions of the frame side measured from the frame centre, derived only from the
    SHA-1 of the path, so a speck never moves when other files change.
    """

    x: float = Field(ge=-0.5, le=0.5)
    y: float = Field(ge=-0.5, le=0.5)


class AnatomyCystFile(BaseModel):
    """A foreign file inside a cyst."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    lines: int = Field(ge=1)


class AnatomyCyst(BaseModel):
    """Foreign files grouped by their first three path segments."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(description="First three path segments joined with '/'")
    x: Finite
    y: Finite
    r: Radius = Field(description="1.1 * sqrt(sum of cell radii squared) + 2")
    files: list[AnatomyCystFile] = Field(min_length=1, description="Sorted by lines descending, then path")


class AnatomyScene(BaseModel):
    """Anatomy live portrait: the repository drawn one to one from its raw structure (ADR 0003)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1"]
    representation: Literal["anatomy"]
    repository_name: str | None
    engine_version: str = Field(default_factory=current_engine_version)
    caption: bool
    library_versions: AnatomyLibraryVersions
    counts: AnatomyCounts
    blame_years: AnatomyBlameYears | None = Field(description="None when no file has line_years")
    bodies: list[AnatomyBody]
    tendons: list[AnatomyTendon]
    dust: list[AnatomyDust]
    cysts: list[AnatomyCyst]
    unresolved_references: int = Field(ge=0)

    @model_validator(mode="after")
    def consistent(self) -> "AnatomyScene":
        paths = [cell.path for body in self.bodies for organ in body.organs for cell in organ.cells]
        paths += [speck.path for speck in self.dust]
        paths += [file.path for cyst in self.cysts for file in cyst.files]
        if len(paths) != len(set(paths)):
            raise ValueError("every scanned file must appear exactly once in the scene")
        if len(paths) != self.counts.files:
            raise ValueError("counts.files must equal the number of files in the scene")
        if (self.counts.bodies, self.counts.dust, self.counts.cysts) != (
            len(self.bodies),
            len(self.dust),
            len(self.cysts),
        ):
            raise ValueError("counts.bodies, counts.dust and counts.cysts must match the scene")
        largest = len(self.bodies[0].organs) if self.bodies else 0
        if self.counts.organs_in_largest_body != largest:
            raise ValueError("counts.organs_in_largest_body must equal the organs of bodies[0]")
        for tendon in self.tendons:
            if tendon.body >= len(self.bodies) or tendon.target >= len(self.bodies[tendon.body].organs):
                raise ValueError("a tendon names a body or an organ that does not exist")
        keys = [(t.body, t.source, t.target) for t in self.tendons]
        if keys != sorted(set(keys)):
            raise ValueError("tendons must be unique and sorted by (body, source, target)")
        return self
