"""Scaling of raw inputs to [0, 1] in the absolute and corpus modes."""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict

from gitgeist.normalization.inputs import INPUTS, InputSpec, raw_inputs, transformed
from gitgeist.normalization.table import QuantileTable, load_quantile_table
from gitgeist.schemas.features import RepositoryFeatures

ScaleMode = Literal["absolute", "corpus"]
SCALE_MODES: tuple[str, ...] = get_args(ScaleMode)


class NormalizedValue(BaseModel):
    """Scaled value in [0, 1], the raw x before the transform, and whether x was clipped."""

    model_config = ConfigDict(frozen=True)

    value: float
    raw: float | None
    clipped: bool


class NormalizedInputs(BaseModel):
    """All normalized inputs of one repository, keyed by INPUT_NAMES."""

    model_config = ConfigDict(frozen=True)

    scale: ScaleMode
    table_version: str | None
    reference_time: datetime
    inputs: dict[str, NormalizedValue]


def _clamp(t: float) -> float:
    return min(1.0, max(0.0, t))


def smoothstep(t: float) -> float:
    """3t^2 - 2t^3 of t clamped to [0, 1]."""
    t = _clamp(t)
    return 3 * t * t - 2 * t * t * t


def anchor_position(value: float, low: float, high: float) -> float:
    """Position of value between log anchors low (0) and high (1), before clamping."""
    low_u = math.log10(low + 1)
    return (math.log10(value + 1) - low_u) / (math.log10(high + 1) - low_u)


def percentile(u: float, points: Sequence[float], probabilities: Sequence[float]) -> float:
    """Probability of u against non-decreasing quantile points.

    Below the first point gives 0.0, above the last 1.0; u equal to one or more
    consecutive points gives the mean of their probabilities; otherwise linear
    interpolation between the neighbouring points.
    """
    if u < points[0]:
        return 0.0
    if u > points[-1]:
        return 1.0
    equal = [p for x, p in zip(points, probabilities) if x == u]
    if equal:
        return statistics.fmean(equal)
    for i in range(len(points) - 1):
        x0, x1 = points[i], points[i + 1]
        if x0 < u < x1:
            p0, p1 = probabilities[i], probabilities[i + 1]
            return p0 + (u - x0) / (x1 - x0) * (p1 - p0)
    raise ValueError(f"cannot place {u} between the quantile points")


def _normalize(spec: InputSpec, raw: float | None, scale: ScaleMode, table: QuantileTable | None) -> NormalizedValue:
    if raw is None:
        return NormalizedValue(value=0.0, raw=None, clipped=False)
    if spec.transform == "flag":
        return NormalizedValue(value=raw, raw=raw, clipped=False)
    if scale == "absolute":
        if spec.transform == "log":
            value = smoothstep(anchor_position(raw, spec.low, spec.high))
            clipped = raw < spec.low or raw > spec.high
        else:
            value = _clamp(raw)
            clipped = raw < 0 or raw > 1
    else:
        assert table is not None
        points = table.inputs[spec.name]
        u = transformed(spec, raw)
        value = percentile(u, points, table.probabilities)
        clipped = u < points[0] or u > points[-1]
    if spec.inverted:
        value = 1.0 - value
    return NormalizedValue(value=value, raw=raw, clipped=clipped)


def normalize_features(
    features: RepositoryFeatures,
    scale: ScaleMode = "absolute",
    *,
    reference_time: datetime | None = None,
    table: QuantileTable | None = None,
) -> NormalizedInputs:
    """Scale every input to [0, 1]; corpus mode uses table or the package table."""
    if scale not in SCALE_MODES:
        raise ValueError(f"unsupported scale mode {scale!r}; supported: {', '.join(SCALE_MODES)}")
    reference = features.extracted_at if reference_time is None else reference_time
    if reference.utcoffset() is None:
        raise ValueError("reference_time must be timezone-aware")
    if scale == "corpus" and table is None:
        table = load_quantile_table()
    used_table = table if scale == "corpus" else None
    raw = raw_inputs(features, reference)
    return NormalizedInputs(
        scale=scale,
        table_version=used_table.table_version if used_table else None,
        reference_time=reference,
        inputs={spec.name: _normalize(spec, raw[spec.name], scale, used_table) for spec in INPUTS},
    )
