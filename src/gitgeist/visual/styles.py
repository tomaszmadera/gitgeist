"""Style registry and variety limits."""

from dataclasses import dataclass
from collections.abc import Callable
from random import Random

from gitgeist.schemas.features import RepositoryFeatures

VARIETY_LIMITS = {"low": (10, 0.02), "medium": (25, 0.05), "high": (45, 0.10)}
REPRESENTATIONS = ("abstract", "character")


@dataclass(frozen=True)
class Style:
    """Representation and factual fit rule of a registered style."""

    representation: str
    fits: Callable[[RepositoryFeatures], bool]


STYLES = {"orbits": Style("abstract", lambda features: True),
          "creature": Style("character", lambda features: True)}


def registered_styles(representation: str) -> tuple[str, ...]:
    """Return registered names in their deterministic selection order."""
    if representation not in REPRESENTATIONS:
        raise ValueError(f"unknown representation {representation!r}; supported: {REPRESENTATIONS}")
    return tuple(sorted(name for name, entry in STYLES.items() if entry.representation == representation))


def select_style(features: RepositoryFeatures, representation: str, style: str, variety: str, seed: int) -> str:
    """Resolve an explicit name or choose from the fitting variety pool."""
    names = registered_styles(representation)
    variety_limits(variety)
    if style != "auto":
        if style not in names:
            raise ValueError(f"style {style!r} is not registered for {representation}; registered: {names}")
        return style
    candidates = [name for name in names if STYLES[name].fits(features)]
    limit = {"low": 1, "medium": 3, "high": len(candidates)}[variety]
    pool = candidates[:limit]
    if not pool:
        raise ValueError(f"no fitting styles for {representation}")
    return Random(seed).choice(pool)


def variety_limits(variety: str) -> tuple[int, float]:
    """Maximum hue offset in degrees and layout jitter in footprint units."""
    if variety not in VARIETY_LIMITS:
        raise ValueError(f"unknown variety {variety!r}; supported: {tuple(VARIETY_LIMITS)}")
    return VARIETY_LIMITS[variety]
