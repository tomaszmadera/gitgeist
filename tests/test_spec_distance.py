"""The four equally weighted distance components."""

import pytest

from gitgeist.schemas.features import Mass, StructureFeatures
from gitgeist.visual.distance import spec_distance
from tests.test_normalization import _features
from tests.test_visual_spec import build, uniform_traits


def base_spec():
    features = _features().model_copy(update={"structure": StructureFeatures(masses=[
        Mass(name=".", file_share=1, dominant_language="Python")])})
    return build(features, uniform_traits(0))


def test_identical_is_zero() -> None:
    a = base_spec()
    assert spec_distance(a, a) == 0


@pytest.mark.parametrize("part,expected", [("traits", 0.25), ("masses", 0.125), ("hue", 0.25), ("style", 0.25)])
def test_each_component_in_isolation(part: str, expected: float) -> None:
    a = base_spec()
    if part == "traits":
        b = a.model_copy(update={"traits": uniform_traits(1)})
    elif part == "masses":
        b = a.model_copy(update={"masses": [a.masses[0].model_copy(update={"file_share": 1 / 8}) for _ in range(8)]})
    elif part == "hue":
        b = a.model_copy(update={"masses": [a.masses[0].model_copy(update={"hue": 15})]})
    else:
        b = a.model_copy(update={"style": "creature"})
    assert spec_distance(a, b) == pytest.approx(expected)
    assert spec_distance(a, b) == spec_distance(b, a)
    assert 0 <= spec_distance(a, b) <= 1


def test_mass_distance_sorts_and_pads_and_hue_skips_neutral() -> None:
    a = base_spec()
    neutral = a.masses[0].model_copy(update={"language": None, "hue": None})
    b = a.model_copy(update={"masses": [neutral]})
    assert spec_distance(a, b) == pytest.approx(0.125)
    masses = [a.masses[0].model_copy(update={"file_share": share}) for share in (0.6, 0.3, 0.1)]
    c = a.model_copy(update={"masses": masses})
    d = a.model_copy(update={"masses": list(reversed(masses))})
    assert spec_distance(c, d) == 0


def test_mass_transport_has_seven_boundaries_for_eight_slots() -> None:
    a = base_spec()
    neutral = a.masses[0].model_copy(update={"language": None, "hue": None})
    a = a.model_copy(update={"masses": [neutral]})
    b = a.model_copy(update={"masses": [neutral.model_copy(update={"file_share": 0.3333}) for _ in range(3)]})
    assert spec_distance(a, b) == pytest.approx((0.6667 + 0.3334 + 5 * 0.0001) / 7 / 4, abs=1e-15)
