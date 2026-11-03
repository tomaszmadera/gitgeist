"""Tests for the creature body plan (stage 5 spec, "Body plan"): pure functions of the VisualSpec, no browser."""

from __future__ import annotations

import hashlib
import math

import pytest

from gitgeist.render.creature import build_creature_body, rest_pose_extent
from gitgeist.schemas.identity import IdentitySeed
from gitgeist.schemas.live_state import CreatureBody, CreatureLimb
from gitgeist.visual import build_visual_spec, compute_traits
from tests.creature_helpers import CORPUS_LIKE, make_character_spec, make_features, mass_table, with_masses
from tests.orbits_helpers import IDENTITY, REFERENCE_TIME


def _body(rows: list[tuple[float, float]], **traits: float) -> CreatureBody:
    features = with_masses(make_features(), mass_table(rows))
    return build_creature_body(make_character_spec(features, **traits))


def _tip(limb: CreatureLimb) -> tuple[float, float]:
    x, y, heading = limb.root_x, limb.root_y, limb.root_angle_deg
    for segment in limb.segments:
        heading += segment.bend_deg
        x += segment.length * math.cos(math.radians(heading))
        y += segment.length * math.sin(math.radians(heading))
    return x, y


def test_torso_is_the_mass_with_the_largest_file_share() -> None:
    body = _body([(0.2, 0.1), (0.5, 0.1), (0.3, 0.1)])
    assert body.torso is not None and body.torso.mass_index == 1
    assert sorted(limb.mass_index for limb in body.limbs) == [0, 2]


def test_torso_ties_go_to_the_lowest_index() -> None:
    body = _body([(0.3, 0.1), (0.4, 0.1), (0.4, 0.1), (0.1, 0.1)])
    assert body.torso is not None and body.torso.mass_index == 1


def test_torso_is_upright_and_elongated_by_one_fifth() -> None:
    body = _body([(0.5, 0.1), (0.3, 0.1), (0.2, 0.1)])
    assert body.torso is not None
    assert body.torso.rotation_deg == 270.0
    assert body.torso.rx / body.torso.ry == pytest.approx(1.2, abs=1e-4)


def test_one_limb_per_other_mass_in_factual_order() -> None:
    body = _body([(0.4, 0.2), (0.3, 0.2), (0.2, 0.2), (0.1, 0.2)])
    assert [limb.mass_index for limb in body.limbs] == [1, 2, 3]


def test_one_mass_gives_no_limbs_and_no_masses_give_no_torso() -> None:
    single = _body([(1.0, 1.0)])
    assert single.torso is not None and single.limbs == []
    empty = build_creature_body(make_character_spec(with_masses(make_features(), [])))
    assert empty.torso is None and empty.limbs == []


@pytest.mark.parametrize("nesting", [0, 1, 2, 3])
def test_segments_are_one_plus_nesting_levels(nesting: int) -> None:
    features = with_masses(make_features(), mass_table([(0.5, 0.2), (0.3, 0.2), (0.2, 0.2)]))
    spec = make_character_spec(features)
    spec = spec.model_copy(update={"topology": spec.topology.model_copy(update={"nesting_levels": nesting})})
    body = build_creature_body(spec)
    assert all(len(limb.segments) == 1 + nesting for limb in body.limbs)


def test_pad_radius_and_reach_follow_the_formulas() -> None:
    rows = [(0.5, 0.1), (0.2, 0.05), (0.1, 0.4), (0.04, 0.0)]
    body = _body(rows)
    assert body.torso is not None
    unit = body.torso.ry  # R after the fit
    for limb in body.limbs:
        share, churn = rows[limb.mass_index]
        pad = max(0.12, 0.8 * math.sqrt(share / 0.5))
        assert limb.pad_radius / unit == pytest.approx(pad, abs=1e-3)
        reach = sum(segment.length for segment in limb.segments)
        assert reach / unit == pytest.approx(max(0.8 + 1.6 * math.sqrt(churn), pad + 0.35), abs=1e-3)


def test_a_larger_churn_share_reaches_farther() -> None:
    body = _body([(0.4, 0.1), (0.2, 0.05), (0.2, 0.6), (0.2, 0.2)])
    reach = {limb.mass_index: sum(s.length for s in limb.segments) for limb in body.limbs}
    assert reach[2] > reach[3] > reach[1]


def test_segment_half_width_tapers_from_half_to_three_tenths_of_the_pad() -> None:
    features = with_masses(make_features(), mass_table([(0.5, 0.2), (0.3, 0.2), (0.2, 0.2)]))
    spec = make_character_spec(features)
    spec = spec.model_copy(update={"topology": spec.topology.model_copy(update={"nesting_levels": 2})})
    for limb in build_creature_body(spec).limbs:
        widths = [segment.half_width / limb.pad_radius for segment in limb.segments]
        assert widths[0] == pytest.approx(0.5, abs=1e-3) and widths[-1] == pytest.approx(0.3, abs=1e-3)
        assert widths == sorted(widths, reverse=True)


@pytest.mark.parametrize("nesting", [0, 1, 3])
def test_posture_is_monotone_in_alive_and_the_total_turn_is_capped(nesting: int) -> None:
    features = with_masses(make_features(), mass_table([(0.5, 0.2), (0.3, 0.2), (0.2, 0.2)]))
    previous = math.inf
    for alive in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        spec = make_character_spec(features, alive=alive)
        spec = spec.model_copy(update={"topology": spec.topology.model_copy(update={"nesting_levels": nesting})})
        limbs = build_creature_body(spec).limbs
        bends = {abs(segment.bend_deg) for limb in limbs for segment in limb.segments}
        assert len(bends) == 1
        bend = bends.pop()
        assert bend <= previous + 1e-9
        previous = bend
        for limb in limbs:
            assert abs(sum(segment.bend_deg for segment in limb.segments)) <= 100 + 1e-6
    # An active creature is nearly straight, a dormant one curls.
    straight = abs(build_creature_body(make_character_spec(features, alive=1.0)).limbs[0].segments[0].bend_deg)
    curled = abs(build_creature_body(make_character_spec(features, alive=0.0)).limbs[0].segments[0].bend_deg)
    assert straight == pytest.approx(10.0) and curled > straight


def test_sway_grows_with_alive_and_phases_are_fractions() -> None:
    rows = [(0.4, 0.2), (0.3, 0.2), (0.2, 0.2), (0.1, 0.2)]
    low, high = _body(rows, alive=0.0), _body(rows, alive=1.0)
    assert {limb.sway_amplitude_deg for limb in low.limbs} == {2.0}
    assert {limb.sway_amplitude_deg for limb in high.limbs} == {12.0}
    assert all(0 <= limb.sway_phase < 1 for limb in high.limbs)
    assert len({limb.sway_phase for limb in high.limbs}) == len(high.limbs)


def test_limbs_of_a_pair_are_on_opposite_sides_of_the_body() -> None:
    body = _body([(0.3, 0.2), (0.2, 0.2), (0.2, 0.1), (0.1, 0.2), (0.1, 0.1), (0.1, 0.1)])
    assert body.torso is not None and len(body.limbs) == 5
    sides = [math.copysign(1, limb.root_x - body.torso.x) for limb in body.limbs]
    for first, second in zip(sides[0::2], sides[1::2], strict=False):
        assert first == -second
    assert abs(sides[0] + sides[2] + sides[4]) in (1, 3)  # every pair starts on the side of the mirror flag


def test_pairs_sit_along_the_torso_from_head_to_tail() -> None:
    body = _body([(0.3, 0.2), (0.2, 0.2), (0.2, 0.1), (0.1, 0.2), (0.1, 0.1), (0.1, 0.1)])
    assert body.torso is not None
    heights = [limb.root_y for limb in body.limbs[0::2]]
    assert heights == sorted(heights, reverse=True) or heights == sorted(heights)
    assert body.limbs[0].root_y == pytest.approx(body.limbs[1].root_y)
    assert heights[0] < heights[-1]  # canvas y grows downward: the first pair is near the head (the top)


def test_two_limbs_of_equal_masses_are_mirror_images() -> None:
    body = _body([(0.4, 0.1), (0.2, 0.3), (0.2, 0.3), (0.1, 0.1), (0.1, 0.1)])
    assert body.torso is not None
    left, right = body.limbs[0], body.limbs[1]
    assert left.pad_radius == right.pad_radius
    assert left.root_y == pytest.approx(right.root_y)
    assert left.root_x - body.torso.x == pytest.approx(-(right.root_x - body.torso.x))
    assert (left.root_angle_deg + right.root_angle_deg) % 360 == pytest.approx(180.0, abs=1e-4)
    for a, b in zip(left.segments, right.segments, strict=True):
        assert a.length == b.length and a.half_width == b.half_width and a.bend_deg == -b.bend_deg
    (lx, ly), (rx, ry) = _tip(left), _tip(right)
    assert ly == pytest.approx(ry, abs=1e-5) and lx - body.torso.x == pytest.approx(-(rx - body.torso.x), abs=1e-5)


def test_other_identity_gives_the_same_plan_up_to_mirror_and_sway_phase() -> None:
    features = with_masses(make_features(), mass_table(CORPUS_LIKE["flask"]))
    traits = compute_traits(features, reference_time=REFERENCE_TIME)
    other = IdentitySeed(identity_seed=hashlib.sha256(b"other").hexdigest(), source="root-commits", root_commits=["o"])
    one = build_creature_body(build_visual_spec(features, traits, IDENTITY, "character"))
    two = build_creature_body(build_visual_spec(features, traits, other, "character"))
    assert one != two  # the stream changes the mirror flag or the phases
    assert one.torso is not None and two.torso is not None
    assert (one.torso.mass_index, one.torso.rx, one.torso.ry) == (two.torso.mass_index, two.torso.rx, two.torso.ry)
    for a, b in zip(one.limbs, two.limbs, strict=True):
        assert a.mass_index == b.mass_index and a.pad_radius == b.pad_radius and a.segments[0].length == b.segments[0].length
        assert abs(a.root_x - one.torso.x) == pytest.approx(abs(b.root_x - two.torso.x), abs=1e-5)
        assert a.root_y == pytest.approx(b.root_y, abs=1e-5)


def test_body_stream_does_not_change_the_other_streams() -> None:
    # sub_seed(.., "body") is an independent stream: building a body leaves the spec's channels untouched.
    features = with_masses(make_features(), mass_table(CORPUS_LIKE["click"]))
    spec = make_character_spec(features)
    snapshot = spec.model_dump_json()
    build_creature_body(spec)
    assert spec.model_dump_json() == snapshot
    assert make_character_spec(features).model_dump_json() == snapshot


def test_body_is_deterministic() -> None:
    features = with_masses(make_features(), mass_table(CORPUS_LIKE["flask"]))
    assert build_creature_body(make_character_spec(features)) == build_creature_body(make_character_spec(features))


@pytest.mark.parametrize("alive", [0.0, 0.5, 1.0])
@pytest.mark.parametrize("name", list(CORPUS_LIKE))
def test_rest_pose_fits_the_unit_circle(name: str, alive: float) -> None:
    body = _body(CORPUS_LIKE[name], alive=alive)
    assert 0.5 < rest_pose_extent(body) <= 1.0 + 1e-5


@pytest.mark.parametrize("nesting", [0, 3])
def test_rest_pose_fits_with_every_segment_count(nesting: int) -> None:
    features = with_masses(make_features(), mass_table(CORPUS_LIKE["click"]))
    spec = make_character_spec(features)
    spec = spec.model_copy(update={"topology": spec.topology.model_copy(update={"nesting_levels": nesting})})
    assert rest_pose_extent(build_creature_body(spec)) <= 1.0 + 1e-5


@pytest.mark.parametrize("name", list(CORPUS_LIKE))
def test_pads_do_not_overlap_by_more_than_a_quarter_at_full_alive(name: str) -> None:
    body = _body(CORPUS_LIKE[name], alive=1.0)
    pads = [(*_tip(limb), limb.pad_radius) for limb in body.limbs]
    assert len(pads) == 7
    for i, (x1, y1, r1) in enumerate(pads):
        for x2, y2, r2 in pads[i + 1 :]:
            overlap = r1 + r2 - math.hypot(x1 - x2, y1 - y2)
            assert overlap <= 0.25 * min(r1, r2) + 1e-9


def test_a_mass_without_files_keeps_a_visible_limb() -> None:
    body = _body([(0.6, 0.2), (0.4, 0.2), (0.0, 0.0)])
    assert body.torso is not None
    limb = body.limbs[1]
    assert limb.pad_radius / body.torso.ry == pytest.approx(0.12, abs=1e-3)
    assert sum(s.length for s in limb.segments) > 0


def test_all_masses_empty_does_not_divide_by_zero() -> None:
    body = _body([(0.0, 0.0), (0.0, 0.0)])
    assert body.torso is not None and len(body.limbs) == 1
    assert rest_pose_extent(body) <= 1.0 + 1e-5
