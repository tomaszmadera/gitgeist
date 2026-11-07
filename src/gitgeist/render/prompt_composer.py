"""Deterministic prompt composer for prompt-to-image portraits.

The prompt is a function of a ``VisualSpec``. It names visible facts and does not
list trait scores, paths, or the repository name unless asked.
"""

from __future__ import annotations

import math
import random

from gitgeist.schemas.traits import TRAIT_NAMES
from gitgeist.schemas.visual_spec import VisualSpec

_COUNT_WORDS = ("one", "two", "three", "four", "five", "six", "seven", "eight")
_GROUND = "#121218"
_MEDIA = {
    "orbits": (
        "ink on dark paper",
        "cut paper",
        "carved and painted stone relief",
        "a macro photograph of a physical model",
    ),
    "creature": (
        "ink drawing",
        "painted clay",
        "carved wood",
        "a studio photograph of a sculpture",
    ),
}
_LIGHTNESS = 0.45


def _round_half_up(value: float) -> int:
    """Round half away from zero to an integer."""
    if value >= 0:
        return math.floor(value + 0.5)
    return math.ceil(value - 0.5)


def _fixed(value: float, digits: int) -> str:
    scale = 10 ** digits
    return f"{_round_half_up(value * scale) / scale:.{digits}f}"


def _mass_hex(hue: float | None, saturation: float) -> str:
    """CSS HSL at lightness 45, half-up rounded to a six-digit hex.

    ``hue is None`` is grey (saturation 0). ``saturation`` is the palette
    fraction; the percent is half-up rounded before the conversion.
    """
    sat = 0.0 if hue is None else _round_half_up(saturation * 100) / 100
    hue_deg = 0.0 if hue is None else hue
    amplitude = sat * min(_LIGHTNESS, 1 - _LIGHTNESS)

    def channel(n: float) -> int:
        k = (n + hue_deg / 30) % 12
        value = _LIGHTNESS - amplitude * max(-1, min(k - 3, 9 - k, 1))
        return _round_half_up(value * 255)

    red, green, blue = channel(0), channel(8), channel(4)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _selected_traits(spec: VisualSpec) -> list[str]:
    values = {name: float(getattr(spec.traits, name)) for name in TRAIT_NAMES}

    def distance(name: str) -> float:
        return abs(values[name] - 0.5)

    selected = [
        name for name in TRAIT_NAMES if values[name] <= 0.33 or values[name] > 0.66
    ]
    while len(selected) > 7:
        victim = min(
            selected,
            key=lambda name: (distance(name), -TRAIT_NAMES.index(name)),
        )
        selected.remove(victim)
    while len(selected) < 5:
        remaining = [name for name in TRAIT_NAMES if name not in selected]
        selected.append(
            max(remaining, key=lambda name: (distance(name), -TRAIT_NAMES.index(name)))
        )
    return [name for name in TRAIT_NAMES if name in selected]


def _placement(spec: VisualSpec) -> str:
    total = sum(mass.radius for mass in spec.masses)
    if not spec.masses or total == 0:
        return "centered"
    wx = sum(mass.radius * mass.x for mass in spec.masses) / total
    wy = sum(mass.radius * mass.y for mass in spec.masses) / total
    horizontal = "left" if wx <= -0.15 else "right" if wx >= 0.15 else None
    vertical = "top" if wy <= -0.15 else "bottom" if wy >= 0.15 else None
    if horizontal and vertical:
        return f"off-center to the {horizontal} and toward the {vertical}"
    if horizontal:
        return f"off-center to the {horizontal}"
    if vertical:
        return f"off-center toward the {vertical}"
    return "centered"


def _bodies_phrase(spec: VisualSpec) -> str:
    if not spec.masses:
        return "no bodies"
    peak = max(mass.radius for mass in spec.masses)
    groups: dict[str, int] = {"large": 0, "medium": 0, "small": 0}
    for mass in spec.masses:
        if mass.radius >= 0.66 * peak:
            groups["large"] += 1
        elif mass.radius <= 0.33 * peak:
            groups["small"] += 1
        else:
            groups["medium"] += 1
    phrases = []
    for size in ("large", "medium", "small"):
        count = groups[size]
        if count == 0:
            continue
        word = _COUNT_WORDS[count - 1]
        noun = "body" if count == 1 else "bodies"
        phrases.append(f"{word} {size} {noun}")
    if len(phrases) == 1:
        return phrases[0]
    if len(phrases) == 2:
        return f"{phrases[0]} and {phrases[1]}"
    return ", ".join(phrases[:-1]) + " and " + phrases[-1]


def _subject(spec: VisualSpec) -> str:
    if spec.style == "creature" and not spec.masses:
        return "A creature with no bodies, centered, on a dark ground."
    if spec.style not in _MEDIA:
        raise ValueError(f"unsupported style: {spec.style}")
    bodies = _bodies_phrase(spec)
    placement = _placement(spec)
    if spec.style == "orbits":
        return f"An abstract composition of {bodies}, {placement}, on a dark ground."
    limb_count = len(spec.masses) - 1
    if limb_count == 0:
        anatomy = "a single torso with no separate limbs"
    elif limb_count == 1:
        anatomy = "the largest body as its torso and one separate limb"
    else:
        limbs = _COUNT_WORDS[limb_count - 1]
        anatomy = f"the largest body as its torso and {limbs} separate limbs"
    return (
        f"A creature built from {bodies}, with {anatomy}, "
        f"{placement}, on a dark ground. {_directive('alive', spec)}"
    )


def _rings(spec: VisualSpec) -> str:
    thickness = spec.rings.thickness
    count = len(thickness)
    if count == 0:
        return "No growth rings."
    if count == 1:
        return "One growth ring."
    thickest = thickness.index(max(thickness)) + 1
    return f"{count} growth rings, thickest at ring {thickest}."


def _nesting(spec: VisualSpec) -> str:
    count = len(spec.masses)
    if count == 0:
        phrase = "No bodies"
    elif count == 1:
        phrase = "One body"
    else:
        phrase = f"{_COUNT_WORDS[count - 1].capitalize()} bodies"
    levels = spec.topology.nesting_levels
    if levels == 0:
        return f"{phrase} with no nested shapes."
    if levels == 1:
        return f"{phrase} with 1 level of nested shapes."
    return f"{phrase} with {levels} levels of nested shapes."


def _directive(name: str, spec: VisualSpec) -> str:
    value = float(getattr(spec.traits, name))
    if name == "size":
        coverage = _round_half_up(spec.footprint.coverage * 100)
        return (
            f"The form covers {coverage}% of the frame and contains "
            f"{spec.footprint.element_count} small marks."
        )
    if name == "age":
        return _rings(spec)
    if name == "alive":
        speed = _fixed(spec.motion.speed_hz, 2)
        quality = "Vivid" if value >= 0.5 else "Faded"
        return f"{quality}, moving at {speed} Hz."
    if name == "crowd":
        count = spec.strands.count
        if count == 1:
            return "One strand crosses the form."
        return f"{count} strands cross the form."
    if name == "focus":
        if spec.knot is None:
            return "No focal knot; change is spread across the form."
        return f"A bright knot sits on body {spec.knot.mass_index + 1}."
    if name == "care":
        blur = _fixed(spec.edge.blur_px, 1)
        jitter = _fixed(spec.edge.jitter, 2)
        quality = "Crisp" if value >= 0.5 else "Frayed"
        return f"{quality} edges, blur {blur} px, jitter {jitter}."
    if name == "sprawl":
        return _nesting(spec)
    if name == "prose":
        coverage = _round_half_up(spec.hatching.coverage * 100)
        return f"Fine hatching covers {coverage}% of each body."
    if name == "debt":
        count = spec.cracks.count
        if count == 0:
            return "No cracks."
        if count == 1:
            return "One crack."
        return f"{count} cracks."
    raise ValueError(f"unknown trait {name!r}")


def _palette_line(spec: VisualSpec) -> str:
    hexes: list[str] = []
    for mass in spec.masses:
        color = _mass_hex(mass.hue, spec.palette.saturation)
        if color not in hexes:
            hexes.append(color)
    colors = f"{', '.join(hexes)} " if hexes else ""
    return f"Palette: {colors}on {_GROUND}."


def _medium_name(spec: VisualSpec) -> str:
    table = _MEDIA[spec.style]
    index = random.Random(spec.seeds.effective_seed).randrange(len(table))
    return table[index]


def compose_prompt(
    spec: VisualSpec,
    *,
    include_name: bool = False,
    repository_name: str | None = None,
) -> str:
    """Compose a deterministic image prompt from a ``VisualSpec``.

    Identical inputs return identical text. The result has no blank line, and
    the last line ends with one newline.

    Raises:
        TypeError: If ``spec`` is not a ``VisualSpec``.
        ValueError: If the style is unknown, or ``include_name`` is set without
            a repository name.
    """
    if not isinstance(spec, VisualSpec):
        raise TypeError(f"Expected VisualSpec, got {type(spec).__name__}")
    if include_name and (repository_name is None or repository_name == ""):
        raise ValueError("include_name requires a non-empty repository_name")

    lines = [_subject(spec)]
    if include_name:
        lines.append(f"Repository: {repository_name}.")
    for name in _selected_traits(spec):
        lines.append(f"- {_directive(name, spec)}")
    lines.append(_palette_line(spec))
    lines.append(f"Medium: {_medium_name(spec)}.")
    lines.append("No text, no letters, no logos, no code, no screens, no mascots.")
    lines.append("No watermarks and no captions inside the picture.")
    return "\n".join(lines) + "\n"
