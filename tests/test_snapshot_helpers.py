"""The snapshot comparison passes last-bit float differences and fails every real change."""

from __future__ import annotations

import pytest

from tests.snapshot_helpers import assert_matches_snapshot, snapshot_differences

BASE = '{\n  "x": -0.28930495508250503,\n  "y": -0.4667265889053966,\n  "n": 42,\n  "seed": 4294967295,\n  "v": "0.11.0"\n}\n'


def test_equal_text_matches() -> None:
    assert_matches_snapshot(BASE, BASE)


def test_last_bit_float_difference_matches() -> None:
    # The Windows CI value of the stage 5 failure: the neighbouring double, a shorter repr.
    assert_matches_snapshot(BASE.replace("-0.28930495508250503", "-0.289304955082505"), BASE)
    assert_matches_snapshot(BASE.replace("-0.4667265889053966", "-0.46672658890539665"), BASE)
    assert_matches_snapshot(BASE.replace("-0.28930495508250503", "-2.8930495508250503e-01"), BASE)


@pytest.mark.parametrize(
    "changed",
    [
        BASE.replace("-0.28930495508250503", "-0.2893049"),  # 1e-7 relative: a real change of a float
        BASE.replace("-0.4667265889053966", "-0.4667265889053966 "),  # whitespace
        BASE.replace("-0.4667265889053966", "0.4667265889053966"),  # sign
        BASE.replace("42", "43"),  # integers are exact
        BASE.replace("4294967295", "4294967294"),  # a seed one off
        BASE.replace('"x"', '"z"'),  # a key
        BASE.replace('"0.11.0"', '"0.11.1"'),  # a version string is not a float
        BASE.replace("0.28930495508250503", "0.28930495508250503, 0.5"),  # an extra number
        BASE.replace("  \"y\": -0.4667265889053966,\n", ""),  # a missing line
        BASE + "\n",
    ],
)
def test_real_changes_fail(changed: str) -> None:
    assert snapshot_differences(changed, BASE) != []
    with pytest.raises(AssertionError, match="snapshot mismatch"):
        assert_matches_snapshot(changed, BASE)


def test_tolerance_is_tight() -> None:
    assert snapshot_differences(BASE.replace("-0.28930495508250503", "-0.2893049561"), BASE) != []  # 4e-9 relative
    assert snapshot_differences(BASE.replace("-0.28930495508250503", "-0.2893049551"), BASE) == []  # 3e-11 relative
