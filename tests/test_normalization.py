"""Tests for the normalization module (absolute and corpus scale modes)."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from gitgeist.features.extractor import extract_features
from gitgeist.normalization import (
    INPUT_NAMES,
    NormalizedInputs,
    QuantileTable,
    load_quantile_table,
    normalize_features,
    percentile,
    raw_inputs,
    smoothstep,
)
from gitgeist.normalization import table as table_module
from gitgeist.normalization.inputs import INPUTS_BY_NAME, TABLE_INPUT_NAMES
from gitgeist.schemas.features import (
    DocsSummaryFeatures,
    GitHistoryFeatures,
    RepositoryFeatures,
    StaticFeatures,
    StructureFeatures,
)

REF = datetime(2026, 3, 16, 10, 0, 0, tzinfo=timezone.utc)
PROBABILITIES = [round(i * 0.05, 2) for i in range(21)]


def _features(**raw: float) -> RepositoryFeatures:
    """Features whose inputs have the given raw values (others at defaults)."""
    static: dict = {}
    history: dict = {"is_git_repo": True, "commit_count": 1, "last_commit_date": REF - timedelta(days=1)}
    structure: dict = {}
    for name, x in raw.items():
        if name == "code_size":
            static["code_bytes"] = x
        elif name == "age":
            history["repository_age_days"] = x
        elif name == "recency":
            history["last_commit_date"] = REF - timedelta(days=x)
        elif name == "authors":
            history["unique_authors_count"] = x
        elif name == "top_author_share":
            history["top_author_share"] = x
        elif name == "active_months":
            history["active_months_ratio"] = x
        elif name == "focus":
            structure["hotspot_concentration"] = x
        elif name == "test_ratio":
            static["test_ratio"] = x
        elif name == "doc_ratio":
            static["doc_ratio"] = x
        elif name == "debt":
            static["todo_density"] = x
        elif name == "top_level_dirs":
            static["top_level_directory_count"] = x
        elif name == "depth":
            static["max_directory_depth"] = x
        elif name == "ci":
            static["has_ci"] = bool(x)
        else:
            raise KeyError(name)
    return RepositoryFeatures(
        repository_path="/test",
        extracted_at=REF,
        static=StaticFeatures(**static),
        history=GitHistoryFeatures(**history),
        docs=DocsSummaryFeatures(),
        structure=StructureFeatures(**structure),
    )


def _test_table(table_version: str = "test") -> QuantileTable:
    """Every input has points u = 0.0, 0.2, ..., 4.0, so value = u / 4 inside the range."""
    return QuantileTable(
        table_version=table_version,
        probabilities=PROBABILITIES,
        reference_time=REF,
        corpus=[],
        inputs={name: [round(0.2 * i, 1) for i in range(21)] for name in TABLE_INPUT_NAMES},
    )


def test_smoothstep_values_and_clamping() -> None:
    assert smoothstep(0) == 0
    assert smoothstep(0.5) == 0.5
    assert smoothstep(1) == 1
    assert smoothstep(-0.5) == 0
    assert smoothstep(1.5) == 1


@pytest.mark.parametrize(
    ("name", "raw", "expected"),
    [
        ("authors", 31, 0.419417),
        ("age", 365, 0.590880),
        ("recency", 30, 0.645009),
        ("debt", 20, 0.610307),
        ("code_size", 1_000_000, 0.647950),
        ("top_level_dirs", 10, 0.402557),
        ("depth", 5, 0.542436),
        ("top_author_share", 0.62, 0.62),
        ("active_months", 0.375, 0.375),
        ("focus", 0.41, 0.41),
        ("test_ratio", 0.25, 0.25),
        ("doc_ratio", 0.083333, 0.083333),
    ],
)
def test_absolute_exact_values(name: str, raw: float, expected: float) -> None:
    result = normalize_features(_features(**{name: raw}), "absolute", reference_time=REF)

    assert round(result.inputs[name].value, 6) == expected
    assert result.inputs[name].raw == raw
    assert result.inputs[name].clipped is False


@pytest.mark.parametrize("name", ["top_author_share", "active_months", "focus", "test_ratio", "doc_ratio"])
@pytest.mark.parametrize(
    ("raw", "expected", "clipped"),
    [(0.0, 0.0, False), (1.0, 1.0, False), (-0.1, 0.0, True), (1.25, 1.0, True)],
)
def test_absolute_linear_bounds(name: str, raw: float, expected: float, clipped: bool) -> None:
    result = normalize_features(_features(**{name: raw}), "absolute", reference_time=REF).inputs[name]

    assert (result.value, result.raw, result.clipped) == (expected, raw, clipped)


def test_absolute_bounds_and_flag() -> None:
    assert normalize_features(_features(authors=1)).inputs["authors"].model_dump() == {
        "value": 0.0,
        "raw": 1.0,
        "clipped": False,
    }
    assert normalize_features(_features(authors=5000)).inputs["authors"].model_dump() == {
        "value": 1.0,
        "raw": 5000.0,
        "clipped": True,
    }
    assert normalize_features(_features(focus=-0.2)).inputs["focus"].model_dump() == {
        "value": 0.0,
        "raw": -0.2,
        "clipped": True,
    }
    for flag in (0.0, 1.0):
        for scale, table in (("absolute", None), ("corpus", _test_table())):
            ci = normalize_features(_features(ci=flag), scale, table=table).inputs["ci"]
            assert (ci.value, ci.raw, ci.clipped) == (flag, flag, False)


def test_absolute_result_shape() -> None:
    result = normalize_features(_features(authors=3))

    assert isinstance(result, NormalizedInputs)
    assert result.scale == "absolute"
    assert result.table_version is None
    assert result.reference_time == REF
    assert tuple(result.inputs) == INPUT_NAMES
    assert len(INPUT_NAMES) == 13


def test_percentile_interpolation_and_plateau() -> None:
    points, probabilities = [0, 10, 20], [0, 0.5, 1]

    assert percentile(15, points, probabilities) == 0.75
    assert percentile(-1, points, probabilities) == 0.0
    assert percentile(25, points, probabilities) == 1.0
    assert percentile(0, [0, 0, 0, 10, 20], [0, 0.25, 0.5, 0.75, 1]) == 0.25


def test_percentile_full_plateau() -> None:
    points = [3.0] * 21

    assert percentile(3.0, points, PROBABILITIES) == 0.5
    assert percentile(2.0, points, PROBABILITIES) == 0.0
    assert percentile(4.0, points, PROBABILITIES) == 1.0


def test_corpus_clipping() -> None:
    table = _test_table()

    below = normalize_features(_features(focus=-0.2), "corpus", table=table).inputs["focus"]
    above = normalize_features(_features(debt=20000), "corpus", table=table).inputs["debt"]

    assert (below.value, below.clipped) == (0.0, True)
    assert (above.value, above.clipped) == (1.0, True)


CORPUS_EXPECTED = {
    "minimal_repo": {
        "code_size": 0.454886,
        "age": 0.0,
        "recency": 0.531235,
        "authors": 0.075257,
        "top_author_share": 0.25,
        "active_months": 0.25,
        "focus": 0.0,
        "test_ratio": 0.0,
        "doc_ratio": 0.0,
        "debt": 0.0,
        "top_level_dirs": 0.0,
        "depth": 0.0,
        "ci": 0.0,
    },
    "legacy_chaotic_repo": {
        "code_size": 0.604989,
        "age": 0.174743,
        "recency": 0.730205,
        "authors": 0.075257,
        "top_author_share": 0.25,
        "active_months": 0.25,
        "focus": 0.0,
        "test_ratio": 0.0,
        "doc_ratio": 0.0,
        "debt": 0.750109,
        "top_level_dirs": 0.075257,
        "depth": 0.194538,
        "ci": 0.0,
    },
}


@pytest.mark.parametrize("fixture", sorted(CORPUS_EXPECTED))
def test_corpus_values_on_fixtures(fixture: str, request: pytest.FixtureRequest) -> None:
    features = extract_features(request.getfixturevalue(fixture))

    result = normalize_features(features, "corpus", reference_time=REF, table=_test_table())

    assert result.scale == "corpus"
    assert result.table_version == "test"
    assert {name: round(v.value, 6) for name, v in result.inputs.items()} == CORPUS_EXPECTED[fixture]
    assert not any(v.clipped for v in result.inputs.values())


def _grid(name: str) -> list[float]:
    """20 raw values from the low to the high anchor, evenly spaced in u."""
    spec = INPUTS_BY_NAME[name]
    if spec.transform == "linear":
        return [i / 19 for i in range(20)]
    low_u, high_u = math.log10(spec.low + 1), math.log10(spec.high + 1)
    values = [10 ** (low_u + (high_u - low_u) * i / 19) - 1 for i in range(20)]
    integer = name in {"code_size", "age", "authors", "top_level_dirs", "depth"}
    return [float(round(v)) if integer else round(v, 4) for v in values]


@pytest.mark.parametrize("scale", ["absolute", "corpus"])
@pytest.mark.parametrize("name", [n for n in INPUT_NAMES if n != "ci"])
def test_monotonic_in_raw_value(name: str, scale: str) -> None:
    table = _test_table() if scale == "corpus" else None
    grid = _grid(name)
    results = [normalize_features(_features(**{name: x}), scale, table=table).inputs[name] for x in grid]
    values = [-r.value if name == "recency" else r.value for r in results]

    assert all(b >= a for a, b in zip(values, values[1:]))
    assert values[-1] > values[0]
    for (xa, a, ra), (xb, b, rb) in zip(zip(grid, values, results), zip(grid[1:], values[1:], results[1:])):
        if xb > xa and not ra.clipped and not rb.clipped and (scale == "absolute" or 0 < abs(a) < 1):
            assert b > a, (name, xa, xb)


def test_values_are_finite_and_in_unit_interval(wide_repo: Path) -> None:
    features = extract_features(wide_repo)

    for result in (normalize_features(features), normalize_features(features, "corpus", table=_test_table())):
        assert all(math.isfinite(v.value) and 0.0 <= v.value <= 1.0 for v in result.inputs.values())


def test_non_git_dir_recency_has_no_raw_value(non_git_dir: Path) -> None:
    features = extract_features(non_git_dir)

    for scale, table in (("absolute", None), ("corpus", _test_table())):
        recency = normalize_features(features, scale, table=table).inputs["recency"]
        assert (recency.raw, recency.value, recency.clipped) == (None, 0.0, False)
    assert raw_inputs(features, REF)["recency"] is None


def test_last_commit_after_reference_time_is_clipped() -> None:
    features = _features(recency=-2)

    recency = normalize_features(features, reference_time=REF).inputs["recency"]

    assert (recency.raw, recency.value, recency.clipped) == (0.0, 1.0, True)


def test_reference_time_defaults_to_extracted_at() -> None:
    assert normalize_features(_features(recency=30)).reference_time == REF


def test_normalization_is_deterministic(clean_modular_repo: Path) -> None:
    features = extract_features(clean_modular_repo)

    assert normalize_features(features, "corpus", table=_test_table()) == normalize_features(
        features, "corpus", table=_test_table()
    )


def test_unsupported_scale_mode() -> None:
    with pytest.raises(ValueError, match="portfolio.*absolute, corpus"):
        normalize_features(_features(), "portfolio")  # type: ignore[arg-type]


def test_naive_reference_time() -> None:
    with pytest.raises(ValueError, match="timezone"):
        normalize_features(_features(), reference_time=datetime(2026, 3, 16, 10, 0, 0))


def _table_data() -> dict:
    return _test_table("v-bad").model_dump(mode="json")


def test_table_without_input_is_rejected() -> None:
    data = _table_data()
    del data["inputs"]["debt"]

    with pytest.raises(ValueError, match=r"'v-bad'.*inputs\.debt"):
        QuantileTable.model_validate(data)


def test_table_with_20_points_is_rejected() -> None:
    data = _table_data()
    data["inputs"]["age"] = data["inputs"]["age"][:20]

    with pytest.raises(ValueError, match=r"'v-bad'.*inputs\.age"):
        QuantileTable.model_validate(data)


def test_table_with_decreasing_values_is_rejected() -> None:
    data = _table_data()
    data["inputs"]["authors"][5] = -1.0

    with pytest.raises(ValueError, match=r"'v-bad'.*inputs\.authors"):
        QuantileTable.model_validate(data)


def test_table_with_non_finite_value_is_rejected() -> None:
    data = _table_data()
    data["inputs"]["depth"][20] = math.inf

    with pytest.raises(ValueError, match=r"'v-bad'.*inputs\.depth"):
        QuantileTable.model_validate(data)


def test_table_with_other_probabilities_is_rejected() -> None:
    data = _table_data()
    data["probabilities"] = [i / 20 + 0.01 for i in range(21)]

    with pytest.raises(ValueError, match=r"'v-bad'.*probabilities"):
        QuantileTable.model_validate(data)


def test_missing_package_table_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(table_module, "TABLE_RESOURCE", "missing.json")

    with pytest.raises(FileNotFoundError, match="missing.json"):
        normalize_features(_features(), "corpus")


def test_load_quantile_table_reads_package_table() -> None:
    table = load_quantile_table()

    assert table.table_version == "1"
    assert set(table.inputs) == set(INPUT_NAMES) - {"ci"}
    assert normalize_features(_features(), "corpus").table_version == "1"
