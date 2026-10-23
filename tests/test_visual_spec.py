"""Scene channels, factual structure, determinism and stable identity."""

import math
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from gitgeist.features.extractor import extract_features
from gitgeist.ingest.identity import compute_identity_seed
from gitgeist.schemas.features import Hotspot, Mass, StructureFeatures
from gitgeist.schemas.identity import IdentitySeed
from gitgeist.schemas.traits import TRAIT_NAMES, Traits
from gitgeist.schemas.visual_spec import VisualSpec
from gitgeist.visual.spec_builder import build_visual_spec
from gitgeist.visual.traits import compute_traits
from tests.fixtures.builder import _commit_at, create_emptied_repo

REF = datetime(2026, 4, 16, tzinfo=timezone.utc)
IDENTITY = IdentitySeed(identity_seed="a" * 64, source="directory-name")


def uniform_traits(value: float) -> Traits:
    return Traits(scale="absolute", table_version=None, reference_time=REF, **dict.fromkeys(TRAIT_NAMES, value))


def build(features, traits=None, **kwargs) -> VisualSpec:
    return build_visual_spec(features, traits or compute_traits(features, reference_time=REF), IDENTITY,
                             "abstract", **kwargs)


@pytest.mark.parametrize("trait,channels", [
    ("size", {"footprint"}), ("age", set()), ("alive", {"palette", "motion"}),
    ("crowd", {"strands"}), ("focus", {"knot"}), ("care", {"edge"}),
    ("sprawl", {"topology"}), ("prose", {"hatching"}), ("debt", {"cracks"}),
])
def test_channel_isolation(wide_repo: Path, trait: str, channels: set[str]) -> None:
    features = extract_features(wide_repo)
    low = build(features, uniform_traits(0.2)).model_dump()
    high = build(features, uniform_traits(0.2).model_copy(update={trait: 0.8})).model_dump()
    assert {name for name in low if low[name] != high[name]} == channels | {"traits"}
    assert low["masses"] == high["masses"]
    if trait == "alive":
        assert low["palette"]["hue_offset"] == high["palette"]["hue_offset"]
        assert low["motion"]["pulse"] == high["motion"]["pulse"]
    if trait == "focus":
        assert {k: v for k, v in low["knot"].items() if k != "radius"} == {
            k: v for k, v in high["knot"].items() if k != "radius"}


@pytest.mark.parametrize("value", [0.0, 1.0])
def test_channel_endpoints(wide_repo: Path, value: float) -> None:
    spec = build(extract_features(wide_repo), uniform_traits(value))
    assert spec.footprint.coverage == pytest.approx(0.25 + 0.60 * value)
    assert spec.footprint.element_count == 40 + 560 * value
    assert spec.palette.saturation == pytest.approx(0.10 + 0.75 * value)
    assert spec.motion.speed_hz == pytest.approx(0.05 + 1.15 * value)
    assert spec.strands.count == 1 + 11 * value
    assert spec.knot.radius == pytest.approx(0.15 + 0.35 * value)
    assert spec.edge.blur_px == 6 * (1 - value)
    assert spec.edge.jitter == 0.25 * (1 - value)
    assert spec.topology.nesting_levels == 3 * value
    assert spec.hatching.coverage == pytest.approx(0.60 * value)
    assert spec.cracks.count == 60 * value
    assert spec.motion.loop_seconds == 12.0


def test_timeline_rings_and_pulse(timeline_repo: Path) -> None:
    features = extract_features(timeline_repo)
    spec = build(features)
    assert spec.rings.first_year == 2025
    assert spec.rings.thickness == [2 / 3, 1.0]
    assert spec.motion.pulse == [1, 0, 0.5, 0, 1]
    history = features.history.model_copy(update={"timeline_start": "1980-01", "timeline": [1] * (45 * 12),
                                                  "repository_age_days": 45 * 365})
    older = build(features.model_copy(update={"history": history}))
    assert older.traits.age > spec.traits.age
    assert older.rings.first_year == 1980
    assert len(older.rings.thickness) == 40
    assert older.rings.thickness == [1.0] + [1 / 6] * 39


def test_knot_owns_top_hotspot(wide_repo: Path) -> None:
    spec = build(extract_features(wide_repo))
    assert spec.masses[spec.knot.mass_index].name == "a"
    assert spec.knot.path == "a/m0.py"
    assert spec.knot.flicker == 0.0952
    mass = spec.masses[spec.knot.mass_index]
    assert math.hypot(spec.knot.offset_x, spec.knot.offset_y) == pytest.approx(mass.radius / 2)


def test_empty_and_no_git(tmp_path: Path, non_git_dir: Path) -> None:
    emptied = build(extract_features(create_emptied_repo(tmp_path / "emptied")))
    assert emptied.masses == [] and emptied.knot is None
    assert emptied.cracks.count == 0
    no_git = build(extract_features(non_git_dir))
    assert no_git.rings.first_year is None and no_git.rings.thickness == []
    assert no_git.motion.pulse == [] and no_git.knot is None


def test_real_and_merged_other(wide_repo: Path) -> None:
    features = extract_features(wide_repo)
    masses = [Mass(name="other", is_merged=False, file_share=0.7),
              Mass(name="other", is_merged=True, file_share=0.3)]
    features = features.model_copy(update={
        "structure": StructureFeatures(masses=masses),
        "history": features.history.model_copy(update={"hotspots": [Hotspot(path="deleted/a.py", change_count=1,
                                                                           change_share=0.2, mass="other")]}),
    })
    assert build(features).knot.mass_index == 1
    missing = features.model_copy(update={"structure": StructureFeatures(masses=[Mass(name="a", file_share=1)])})
    assert build(missing).knot is None
    real = features.model_copy(update={"structure": StructureFeatures(masses=masses[:1])})
    assert build(real).knot.mass_index == 0


def test_determinism_roundtrip_and_free_seed_fields(wide_repo: Path) -> None:
    features = extract_features(wide_repo)
    traits = uniform_traits(0.5)
    a, b = build(features, traits, user_seed=1), build(features, traits, user_seed=2)
    assert a.model_dump_json() == build(features, traits, user_seed=1).model_dump_json()
    assert VisualSpec.model_validate_json(a.model_dump_json()) == a
    assert a.traits == traits and a.traits is not traits
    for field in ("traits", "rings", "footprint", "edge", "topology", "hatching", "motion"):
        assert getattr(a, field) == getattr(b, field)
    assert a.knot.radius == b.knot.radius
    assert a.palette.saturation == b.palette.saturation
    assert a.strands.count == b.strands.count and a.cracks.count == b.cracks.count
    for ma, mb in zip(a.masses, b.masses):
        for field in ("name", "is_merged", "file_share", "churn_share", "language"):
            assert getattr(ma, field) == getattr(mb, field)
    assert [(m.x, m.y) for m in a.masses] != [(m.x, m.y) for m in b.masses]
    assert a.strands.paths != b.strands.paths and a.cracks.marks != b.cracks.marks
    assert a.palette.hue_offset != b.palette.hue_offset


def test_one_file_commit_keeps_layout(wide_repo: Path) -> None:
    identity = compute_identity_seed(wide_repo)
    before = extract_features(wide_repo)
    (wide_repo / "a" / "m1.py").write_text("v = 999\n", encoding="utf-8", newline="\n")
    _commit_at(wide_repo, "change one file", "2026-04-07")
    after = extract_features(wide_repo)
    assert compute_identity_seed(wide_repo) == identity
    specs = [build_visual_spec(f, compute_traits(f, reference_time=REF), identity, "abstract") for f in (before, after)]
    assert all(math.hypot(a.x - b.x, a.y - b.y) <= 0.05 for a, b in zip(specs[0].masses, specs[1].masses))


@pytest.mark.parametrize("kwargs", [dict(style="unknown"), dict(style="creature"), dict(variety="bad"),
                                   dict(user_seed=-1), dict(user_seed=2**63)])
def test_invalid_options(wide_repo: Path, kwargs: dict) -> None:
    with pytest.raises(ValueError):
        build(extract_features(wide_repo), **kwargs)


def test_invalid_types_and_representation(wide_repo: Path) -> None:
    features = extract_features(wide_repo)
    with pytest.raises(TypeError, match="traits"):
        build_visual_spec(features, {}, IDENTITY, "abstract")
    with pytest.raises(TypeError, match="identity"):
        build_visual_spec(features, uniform_traits(0), "bad", "abstract")
    with pytest.raises(ValueError, match="representation"):
        build_visual_spec(features, uniform_traits(0), IDENTITY, "bad")


def test_scene_schema_rejects_invalid_references(wide_repo: Path) -> None:
    data = build(extract_features(wide_repo)).model_dump()
    data["knot"]["mass_index"] = len(data["masses"])
    with pytest.raises(ValidationError, match="mass_index"):
        VisualSpec.model_validate(data)
