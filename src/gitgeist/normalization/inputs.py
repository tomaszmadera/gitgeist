"""Normalized inputs: sources, transforms and absolute anchors."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from gitgeist.features.history import days_since_last_commit
from gitgeist.schemas.features import RepositoryFeatures

Transform = Literal["log", "linear", "flag"]


@dataclass(frozen=True)
class InputSpec:
    """One normalized input; low and high are the absolute anchors (value 0 and 1)."""

    name: str
    transform: Transform
    low: float = 0.0
    high: float = 1.0
    inverted: bool = False


INPUTS: tuple[InputSpec, ...] = (
    InputSpec("code_size", "log", 1_000, 100_000_000),
    InputSpec("age", "log", 7, 7300),
    InputSpec("recency", "log", 1, 1825, inverted=True),
    InputSpec("authors", "log", 1, 1000),
    InputSpec("top_author_share", "linear"),
    InputSpec("active_months", "linear"),
    InputSpec("focus", "linear"),
    InputSpec("test_ratio", "linear"),
    InputSpec("doc_ratio", "linear"),
    InputSpec("debt", "log", 0, 200),
    InputSpec("top_level_dirs", "log", 1, 100),
    InputSpec("depth", "log", 1, 15),
    InputSpec("ci", "flag"),
)

INPUT_NAMES: tuple[str, ...] = tuple(spec.name for spec in INPUTS)
INPUTS_BY_NAME: dict[str, InputSpec] = {spec.name: spec for spec in INPUTS}
# Inputs with a quantile row in the table: every input except the "ci" flag.
TABLE_INPUT_NAMES: tuple[str, ...] = tuple(spec.name for spec in INPUTS if spec.transform != "flag")


def transformed(spec: InputSpec, raw: float) -> float:
    """u: log10(x + 1) for log inputs, x otherwise."""
    return math.log10(raw + 1) if spec.transform == "log" else raw


def raw_inputs(features: RepositoryFeatures, reference_time: datetime) -> dict[str, float | None]:
    """Raw value x of every input, keyed by INPUT_NAMES; recency is None without history."""
    static, history = features.static, features.history
    return {
        "code_size": float(static.code_bytes),
        "age": float(history.repository_age_days),
        "recency": days_since_last_commit(history, reference_time),
        "authors": float(history.unique_authors_count),
        "top_author_share": history.top_author_share,
        "active_months": history.active_months_ratio,
        "focus": features.structure.hotspot_concentration,
        "test_ratio": static.test_ratio,
        "doc_ratio": static.doc_ratio,
        "debt": static.todo_density,
        "top_level_dirs": float(static.top_level_directory_count),
        "depth": float(static.max_directory_depth),
        "ci": 1.0 if static.has_ci else 0.0,
    }
