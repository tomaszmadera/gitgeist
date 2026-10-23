"""Diversity distance over scene data, independent of pixels."""

import math

from gitgeist.schemas.traits import TRAIT_NAMES
from gitgeist.schemas.visual_spec import VisualSpec


def _mass_vector(spec: VisualSpec) -> list[float]:
    values = sorted((m.file_share for m in spec.masses), reverse=True)
    return values + [0.0] * (8 - len(values))


def _hues(spec: VisualSpec) -> list[float]:
    bins: list[list[float]] = [[] for _ in range(12)]
    for mass in spec.masses:
        if mass.hue is not None:
            bins[int(mass.hue // 30)].append(mass.file_share)
    return [math.fsum(weights) for weights in bins]


def spec_distance(a: VisualSpec, b: VisualSpec) -> float:
    """Mean of trait L1, mass EMD / 7, hue half-L1 and style mismatch.

    The final clamp protects the [0, 1] contract against four-place rounding
    of factual file shares. Neutral masses contribute no hue weight.
    """
    traits = sum(abs(getattr(a.traits, name) - getattr(b.traits, name)) for name in TRAIT_NAMES) / 9
    cumulative = 0.0
    transport = 0.0
    # Eight slots have seven transport boundaries. Rounded shares can leave
    # a tiny residual, which must not add a fictitious eighth boundary.
    for x, y in zip(_mass_vector(a)[:-1], _mass_vector(b)[:-1]):
        cumulative += x - y
        transport += abs(cumulative)
    hue = 0.5 * sum(abs(x - y) for x, y in zip(_hues(a), _hues(b)))
    return min(1.0, max(0.0, (traits + transport / 7 + hue + (a.style != b.style)) / 4))
