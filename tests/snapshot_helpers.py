"""Snapshot comparison that is exact except for float literals (portable across platforms).

The live pages and scene JSON embed floats computed with ``math.sin``, ``math.cos`` and similar
functions of the C library. The C library of Windows and the one of Linux may differ in the last bit
of such a result (one unit in the last place), which changes the shortest repr of the float
(``-0.28930495508250503`` on Linux, ``-0.289304955082505`` on Windows CI). A golden file compared as
exact text is therefore byte-identical on Linux only.

``assert_matches_snapshot`` compares the text with every float literal replaced by a placeholder
(so every other character, including every integer, name and key, must be exactly equal) and then the
float literals one by one with ``math.isclose(rel_tol=1e-9, abs_tol=1e-12)``. A last-bit difference
passes; a changed constant, an extra or missing number, or any change of text fails.
"""

from __future__ import annotations

import math
import re

REL_TOL = 1e-9
ABS_TOL = 1e-12

# A float literal: digits with a decimal point and/or an exponent, not part of a word, a version string
# (0.11.0) or an integer. Integers (seeds, counts) are not matched: they stay in the compared text.
_FLOAT = re.compile(
    r"(?<![\w.])-?(?:\d+\.\d+(?:[eE][+-]?\d+)?(?![\d.])|\d+[eE][+-]?\d+(?![\w.]))"
)
_PLACEHOLDER = "<FLOAT>"


def _split(text: str) -> tuple[str, list[float]]:
    numbers: list[float] = []

    def take(match: re.Match[str]) -> str:
        numbers.append(float(match.group(0)))
        return _PLACEHOLDER

    return _FLOAT.sub(take, text), numbers


def snapshot_differences(actual: str, expected: str, *, rel_tol: float = REL_TOL, abs_tol: float = ABS_TOL) -> list[str]:
    """Return what differs between two texts, empty when they match exactly except within float tolerance."""
    if actual == expected:
        return []
    actual_text, actual_numbers = _split(actual)
    expected_text, expected_numbers = _split(expected)
    if actual_text != expected_text:
        for index, (a, b) in enumerate(zip(actual_text.splitlines(), expected_text.splitlines(), strict=False), start=1):
            if a != b:
                return [f"text differs at line {index} (floats masked): {a.strip()!r} != {b.strip()!r}"]
        return [f"text differs in length (floats masked): {len(actual_text.splitlines())} != {len(expected_text.splitlines())} lines"]
    return [
        f"float literal #{i}: {a!r} != {b!r}"
        for i, (a, b) in enumerate(zip(actual_numbers, expected_numbers, strict=True))
        if not math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)
    ]


def assert_matches_snapshot(actual: str, expected: str, *, rel_tol: float = REL_TOL, abs_tol: float = ABS_TOL) -> None:
    differences = snapshot_differences(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol)
    assert not differences, "snapshot mismatch: " + "; ".join(differences[:5]) + (
        f" (+{len(differences) - 5} more)" if len(differences) > 5 else ""
    )
