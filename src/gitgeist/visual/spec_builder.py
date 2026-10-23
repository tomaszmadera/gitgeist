"""Assemble the renderer-neutral scene from traits, structure and seeds."""

import math
from random import Random
from typing import Literal

from gitgeist.schemas.features import GitHistoryFeatures, RepositoryFeatures
from gitgeist.schemas.identity import IdentitySeed
from gitgeist.schemas.traits import Traits
from gitgeist.schemas.visual_spec import (
    CrackMark, Cracks, Edge, Footprint, Hatching, Knot, Motion, Palette, Rings,
    SeedInfo, SpecMass, StrandPath, Strands, Topology, VisualSpec,
)
from gitgeist.visual.layout import pack_masses
from gitgeist.visual.palette import hue_offset, language_hue
from gitgeist.visual.seeds import effective_seed, style_seed, sub_seed
from gitgeist.visual.styles import select_style


def _rings(history: GitHistoryFeatures) -> Rings:
    if not history.commit_count or not history.timeline or history.timeline_start is None:
        return Rings(first_year=None, thickness=[])
    year, month = map(int, history.timeline_start.split("-"))
    years = [0] * ((month - 1 + len(history.timeline) - 1) // 12 + 1)
    for index, count in enumerate(history.timeline):
        years[(month - 1 + index) // 12] += count
    if len(years) > 40:
        years = [sum(years[:-39]), *years[-39:]]
    maximum = max(years)
    return Rings(first_year=year, thickness=[count / maximum if maximum else 0.0 for count in years])


def _knot(features: RepositoryFeatures, masses: list[SpecMass], traits: Traits, layout_seed: int) -> Knot | None:
    if not features.history.commit_count or not features.history.hotspots:
        return None
    top = min(features.history.hotspots, key=lambda item: (-item.change_count, item.path))
    candidates = [i for i, mass in enumerate(masses) if mass.name == top.mass]
    if not candidates:
        return None
    # A merged "other" owns paths outside named masses, even if a real
    # directory has the same name. This follows the stage 2 hotspot contract.
    index = next((i for i in candidates if masses[i].is_merged), candidates[0])
    mass = masses[index]
    angle = Random(layout_seed).uniform(0, 2 * math.pi)
    return Knot(mass_index=index, path=top.path, offset_x=0.5 * mass.radius * math.cos(angle),
                offset_y=0.5 * mass.radius * math.sin(angle), radius=0.15 + 0.35 * traits.focus,
                flicker=top.change_share)


def build_visual_spec(
    features: RepositoryFeatures,
    traits: Traits,
    identity: IdentitySeed,
    representation: Literal["abstract", "character"],
    *,
    style: str = "auto",
    user_seed: int | None = None,
    variety: Literal["low", "medium", "high"] = "medium",
) -> VisualSpec:
    """Build a deterministic scene without reading Git, files or the clock."""
    if not isinstance(traits, Traits):
        raise TypeError("traits must be a Traits instance")
    if not isinstance(identity, IdentitySeed):
        raise TypeError("identity must be an IdentitySeed instance")
    selection_seed = style_seed(identity.identity_seed, user_seed)
    chosen = select_style(features, representation, style, variety, selection_seed)
    effective = effective_seed(identity.identity_seed, user_seed, chosen)
    layout_seed = sub_seed(effective, "layout")
    offset = hue_offset(sub_seed(effective, "hue"), variety)
    positions = pack_masses(features.structure.masses, layout_seed, variety)
    masses = [SpecMass(name=m.name, is_merged=m.is_merged, file_share=m.file_share, churn_share=m.churn_share,
                       language=m.dominant_language, hue=language_hue(m.dominant_language, offset),
                       x=x, y=y, radius=radius)
              for m, (x, y, radius) in zip(features.structure.masses, positions)]
    strand_rng = Random(sub_seed(effective, "strands"))
    strand_count = round(1 + 11 * traits.crowd)
    strands = Strands(count=strand_count, paths=[StrandPath(phase=strand_rng.random(),
                      curvature=strand_rng.uniform(-1, 1)) for _ in range(strand_count)])
    crack_rng = Random(sub_seed(effective, "cracks"))
    crack_count = round(60 * traits.debt) if masses else 0
    cracks = Cracks(count=crack_count, marks=[CrackMark(mass_index=crack_rng.randrange(len(masses)),
                    u=crack_rng.random(), v=crack_rng.random(), angle=crack_rng.uniform(0, 360))
                    for _ in range(crack_count)])
    timeline = features.history.timeline if features.history.commit_count else []
    maximum = max(timeline, default=0)
    return VisualSpec(
        schema_version="1", representation=representation, style=chosen, style_requested=style, variety=variety,
        seeds=SeedInfo(identity_seed=identity.identity_seed, user_seed=user_seed, style_seed=selection_seed,
                       effective_seed=effective), traits=traits.model_copy(deep=True),
        footprint=Footprint(coverage=0.25 + 0.60 * traits.size, element_count=round(40 + 560 * traits.size)),
        masses=masses, rings=_rings(features.history),
        palette=Palette(mode="language", saturation=0.10 + 0.75 * traits.alive, hue_offset=offset),
        knot=_knot(features, masses, traits, layout_seed), strands=strands, cracks=cracks,
        hatching=Hatching(coverage=0.60 * traits.prose),
        edge=Edge(blur_px=6 * (1 - traits.care), jitter=0.25 * (1 - traits.care)),
        topology=Topology(nesting_levels=round(3 * traits.sprawl)),
        motion=Motion(speed_hz=0.05 + 1.15 * traits.alive, loop_seconds=12.0,
                      pulse=[count / maximum if maximum else 0.0 for count in timeline]),
    )
