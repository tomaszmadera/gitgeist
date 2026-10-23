"""Seeded spiral packing in a unit-circle footprint."""

import math
from collections.abc import Sequence
from random import Random

from gitgeist.schemas.features import Mass
from gitgeist.visual.styles import variety_limits


def pack_masses(masses: Sequence[Mass], seed: int, variety: str) -> list[tuple[float, float, float]]:
    """Place masses on golden-angle rays, then fit the composition to radius 1.

    Each tuple is (x, y, radius). Only file shares, their order, the seed and
    variety affect packing; churn and portrait traits never move a mass.
    """
    _, jitter = variety_limits(variety)
    rng = Random(seed)
    start = rng.uniform(0, 2 * math.pi)
    placed: list[tuple[float, float, float]] = []
    for k, mass in enumerate(masses):
        radius = math.sqrt(mass.file_share)
        angle = start + math.radians(k * 137.508)
        step = 0
        while True:
            x, y = step * 0.01 * math.cos(angle), step * 0.01 * math.sin(angle)
            if all(math.hypot(x - px, y - py) >= radius + pr for px, py, pr in placed):
                break
            step += 1
        placed.append((x + rng.uniform(-jitter, jitter), y + rng.uniform(-jitter, jitter), radius))
    if not placed:
        return []
    extent = max(math.hypot(x, y) + r for x, y, r in placed)
    if extent == 0:
        raise ValueError("mass composition must have positive extent")
    return [(x / extent, y / extent, r / extent) for x, y, r in placed]
