"""Exact trait values, scaling, isolation and monotonicity."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from gitgeist.features.extractor import extract_features
from gitgeist.normalization import normalize_features
from gitgeist.schemas.traits import TRAIT_NAMES
from gitgeist.visual.traits import compute_traits
from tests.test_normalization import _features, _test_table

REF = datetime(2026, 4, 16, tzinfo=timezone.utc)


@pytest.mark.parametrize("fixture,expected", [
    ("timeline_repo", dict(size=0.0, age=0.333624, alive=0.590964, crowd=0.329394,
                           focus=0.0, care=0.0, sprawl=0.0, prose=0.0, debt=0.0)),
    ("wide_repo", dict(alive=0.924992, crowd=0.0, focus=0.0754, sprawl=1.0, prose=0.0179)),
    ("clean_modular_repo", dict(age=0.023946, alive=0.750103, crowd=0.172755,
                                care=0.625, sprawl=0.582136, prose=0.2857)),
])
def test_exact_fixture_traits(fixture: str, expected: dict, request: pytest.FixtureRequest) -> None:
    traits = compute_traits(extract_features(request.getfixturevalue(fixture)), reference_time=REF)
    assert {name: getattr(traits, name) for name in expected} == expected


def test_default_reference_uses_utc_day() -> None:
    features = _features().model_copy(update={"extracted_at": REF + timedelta(hours=19)})
    assert compute_traits(features).reference_time == REF
    assert compute_traits(features, reference_time=REF + timedelta(hours=3)).reference_time == REF + timedelta(hours=3)


def test_no_history(non_git_dir: Path) -> None:
    traits = compute_traits(extract_features(non_git_dir), reference_time=REF)
    assert (traits.age, traits.alive, traits.crowd) == (0.0, 0.0, 0.0)


def test_corpus_uses_supplied_table() -> None:
    traits = compute_traits(_features(code_size=10000), "corpus", reference_time=REF, table=_test_table())
    assert traits.table_version == "test"
    assert traits.scale == "corpus"
    assert all(0 <= getattr(traits, name) <= 1 for name in TRAIT_NAMES)


@pytest.mark.parametrize("input_name,trait,maximum,inverted", [
    ("code_size", "size", 100_000_000, False), ("age", "age", 7300, False),
    ("recency", "alive", 1825, True), ("active_months", "alive", 1, False),
    ("authors", "crowd", 1000, False), ("top_author_share", "crowd", 1, True),
    ("focus", "focus", 1, False), ("test_ratio", "care", 1, False), ("ci", "care", 1, False),
    ("top_level_dirs", "sprawl", 100, False), ("depth", "sprawl", 15, True),
    ("doc_ratio", "prose", 1, False), ("debt", "debt", 200, False),
])
@pytest.mark.parametrize("scale", ["absolute", "corpus"])
def test_input_isolation_and_monotonicity(input_name: str, trait: str, maximum: float,
                                         inverted: bool, scale: str) -> None:
    integer_inputs = {"code_size", "age", "authors", "top_level_dirs", "depth", "ci"}
    grid = [int(maximum * i / 19) if input_name in integer_inputs else maximum * i / 19 for i in range(20)]
    # sprawl is a share of breadth: depth only moves it when there is breadth to compare with
    base = {"top_level_dirs": 10} if input_name == "depth" else {}
    results = [compute_traits(_features(**base, **{input_name: value}), scale,
                              reference_time=REF, table=_test_table()) for value in grid]
    values = [getattr(t, trait) for t in results]
    assert values == sorted(values, reverse=inverted)
    assert values[0] != values[-1]
    for name in TRAIT_NAMES:
        if name != trait:
            assert len({getattr(t, name) for t in results}) == 1


@pytest.mark.parametrize("scale", ["absolute", "corpus"])
@pytest.mark.parametrize("dirs,depth", [(0, 0), (1, 1), (2, 1), (6, 4), (6, 7), (11, 4), (40, 2), (3, 12)])
def test_sprawl_is_the_share_of_breadth(dirs: int, depth: int, scale: str) -> None:
    """GITGEIST-12 (O14): sprawl = top_level_dirs / (top_level_dirs + depth) of the normalized inputs."""
    features = _features(top_level_dirs=dirs, depth=depth)
    normalized = normalize_features(features, scale, reference_time=REF, table=_test_table()).inputs
    breadth, nesting = normalized["top_level_dirs"].value, normalized["depth"].value
    expected = 0.0 if breadth + nesting == 0 else breadth / (breadth + nesting)
    assert compute_traits(features, scale, reference_time=REF, table=_test_table()).sprawl == round(expected, 6)


def test_sprawl_extremes_in_the_absolute_scale() -> None:
    def sprawl(**raw: int) -> float:
        return compute_traits(_features(**raw), reference_time=REF).sprawl

    assert sprawl(top_level_dirs=0, depth=0) == 0.0
    assert sprawl(top_level_dirs=1, depth=1) == 0.0
    assert sprawl(top_level_dirs=10, depth=1) == 1.0
    assert sprawl(top_level_dirs=1, depth=15) == 0.0
    assert 0.0 < sprawl(top_level_dirs=6, depth=4) < 1.0


def test_sprawl_does_not_grow_with_scale() -> None:
    """The same shape at a larger scale (more code, tests and CI) keeps sprawl: it is a ratio of two inputs."""
    small = compute_traits(_features(top_level_dirs=6, depth=4), reference_time=REF)
    large = compute_traits(_features(top_level_dirs=6, depth=4, code_size=50_000_000, test_ratio=0.5, ci=1),
                           reference_time=REF)
    assert large.size > small.size and large.care > small.care
    assert large.sprawl == small.sprawl


def test_trait_errors_propagate() -> None:
    with pytest.raises(ValueError, match="scale"):
        compute_traits(_features(), "portfolio", reference_time=REF)
    with pytest.raises(ValueError, match="timezone-aware"):
        compute_traits(_features(), reference_time=datetime(2026, 4, 16))
