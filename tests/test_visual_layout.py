"""Packing order, footprint bounds, seed stability and spiral placement."""

import math
from random import Random

import pytest

from gitgeist.schemas.features import Mass
from gitgeist.visual.layout import pack_masses


def test_empty_and_one_mass() -> None:
    assert pack_masses([], 1, "medium") == []
    x, y, radius = pack_masses([Mass(name=".", file_share=1)], 1, "low")[0]
    assert math.hypot(x, y) + radius == pytest.approx(1)
    assert abs(x) <= 0.02 and abs(y) <= 0.02
    assert radius > 0.97


def test_packing_is_deterministic_and_in_unit_circle() -> None:
    masses = [Mass(name=str(i), file_share=share) for i, share in enumerate([0.5, 0.3, 0.2])]
    packed = pack_masses(masses, 456, "medium")
    assert packed == pack_masses(masses, 456, "medium")
    assert packed != pack_masses(masses, 789, "medium")
    assert all(math.hypot(x, y) + r <= 1 + 1e-12 for x, y, r in packed)
    assert [r / packed[0][2] for x, y, r in packed] == pytest.approx([math.sqrt(s / 0.5) for s in [0.5, 0.3, 0.2]])
    changed_churn = [m.model_copy(update={"churn_share": 0.9}) for m in masses]
    assert pack_masses(changed_churn, 456, "medium") == packed


def test_two_mass_spiral_matches_step_search() -> None:
    masses = [Mass(name="a", file_share=0.6), Mass(name="b", file_share=0.4)]
    rng = Random(123)
    start = rng.uniform(0, 2 * math.pi)
    first = (rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02), math.sqrt(0.6))
    angle = start + math.radians(137.508)
    radius = math.sqrt(0.4)
    step = 0
    while math.hypot(step * 0.01 * math.cos(angle) - first[0],
                     step * 0.01 * math.sin(angle) - first[1]) < first[2] + radius:
        step += 1
    second = (step * 0.01 * math.cos(angle) + rng.uniform(-0.02, 0.02),
              step * 0.01 * math.sin(angle) + rng.uniform(-0.02, 0.02), radius)
    extent = max(math.hypot(x, y) + r for x, y, r in [first, second])
    assert pack_masses(masses, 123, "low") == pytest.approx([tuple(v / extent for v in p) for p in [first, second]])
