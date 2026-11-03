"""Tests for the live scene schemas (Pydantic v2): the creature body plan and its scene validators."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from gitgeist.schemas.live_state import (
    CreatureBody,
    CreatureLimb,
    CreatureScene,
    CreatureSegment,
    CreatureTorso,
    HoverDetail,
)
from tests.creature_helpers import make_creature_scene


def _segment(**overrides: float) -> CreatureSegment:
    return CreatureSegment(**{"length": 0.2, "half_width": 0.05, "bend_deg": 10.0, **overrides})


def test_scene_roundtrips_through_json() -> None:
    scene = make_creature_scene()
    assert CreatureScene.model_validate_json(scene.model_dump_json()) == scene
    assert CreatureScene.model_validate(json.loads(scene.model_dump_json(indent=2))) == scene


def test_scene_models_are_frozen_and_forbid_extra_fields() -> None:
    scene = make_creature_scene()
    with pytest.raises(ValidationError):
        scene.caption = False  # type: ignore[misc]
    with pytest.raises(ValidationError):
        CreatureSegment(length=0.2, half_width=0.05, bend_deg=0.0, extra=1)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        scene.body.torso.rx = 2.0  # type: ignore[misc, union-attr]


@pytest.mark.parametrize("field,value", [("length", 0.0), ("half_width", -0.1), ("bend_deg", float("nan")),
                                         ("length", float("inf"))])
def test_segment_rejects_non_positive_sizes_and_non_finite_numbers(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        _segment(**{field: value})


def test_torso_major_axis_comes_first() -> None:
    CreatureTorso(mass_index=0, x=0, y=0, rx=0.5, ry=0.4, rotation_deg=270)
    with pytest.raises(ValidationError, match="major"):
        CreatureTorso(mass_index=0, x=0, y=0, rx=0.3, ry=0.4, rotation_deg=270)


def test_limb_has_one_to_four_segments_and_a_phase_below_one() -> None:
    common = dict(mass_index=1, root_x=0.1, root_y=0.1, root_angle_deg=0, pad_radius=0.1,
                  sway_phase=0.5, sway_amplitude_deg=3)
    CreatureLimb(segments=[_segment()] * 4, **common)
    with pytest.raises(ValidationError):
        CreatureLimb(segments=[], **common)
    with pytest.raises(ValidationError):
        CreatureLimb(segments=[_segment()] * 5, **common)
    with pytest.raises(ValidationError):
        CreatureLimb(segments=[_segment()], **{**common, "sway_phase": 1.0})


def test_scene_requires_every_mass_exactly_once() -> None:
    scene = make_creature_scene()
    body = scene.body
    assert len(body.limbs) >= 2
    missing = CreatureBody(torso=body.torso, limbs=body.limbs[:-1])
    with pytest.raises(ValidationError, match="exactly once"):
        CreatureScene.model_validate({**scene.model_dump(), "body": missing.model_dump()})
    twice = CreatureBody(torso=body.torso, limbs=[*body.limbs, body.limbs[0]])
    with pytest.raises(ValidationError, match="exactly once"):
        CreatureScene.model_validate({**scene.model_dump(), "body": twice.model_dump()})
    with pytest.raises(ValidationError, match="exactly once"):
        CreatureScene.model_validate({**scene.model_dump(), "body": CreatureBody(torso=None, limbs=[]).model_dump()})


def test_scene_requires_the_segment_count_of_the_topology() -> None:
    scene = make_creature_scene()
    limb = scene.body.limbs[0]
    count = 1 if len(limb.segments) > 1 else 2
    wrong = limb.model_copy(update={"segments": [limb.segments[0]] * count})
    body = CreatureBody(torso=scene.body.torso, limbs=[wrong, *scene.body.limbs[1:]])
    with pytest.raises(ValidationError, match="segments"):
        CreatureScene.model_validate({**scene.model_dump(), "body": body.model_dump()})


def test_scene_rejects_an_abstract_spec_and_a_wrong_schema_version() -> None:
    scene = make_creature_scene()
    with pytest.raises(ValidationError):
        CreatureScene.model_validate({**scene.model_dump(), "schema_version": "2"})
    with pytest.raises(ValidationError):
        CreatureScene.model_validate({**scene.model_dump(), "representation": "abstract"})
    orbit_spec = {**scene.spec.model_dump(), "style": "orbits"}
    with pytest.raises(ValidationError):
        CreatureScene.model_validate({**scene.model_dump(), "spec": orbit_spec})
    with pytest.raises(ValidationError):
        CreatureScene.model_validate({**scene.model_dump(), "conclusions": ["a", "b", "c", "d"]})


def test_hover_detail_bounds() -> None:
    HoverDetail(mass_index=0, label=".", file_count=0, file_share_percent=100, top_hotspot=None)
    with pytest.raises(ValidationError):
        HoverDetail(mass_index=0, label=".", file_count=0, file_share_percent=101, top_hotspot=None)
