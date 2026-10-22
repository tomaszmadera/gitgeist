"""Quantile table model and loader for the corpus scale mode."""

from __future__ import annotations

import math
from datetime import datetime
from importlib.resources import files

from pydantic import BaseModel, ConfigDict, model_validator

from gitgeist.normalization.inputs import TABLE_INPUT_NAMES

QUANTILE_PROBABILITIES: tuple[float, ...] = tuple(round(i * 0.05, 2) for i in range(21))
TABLE_PACKAGE = "gitgeist.normalization"
TABLE_RESOURCE = "quantiles-v1.json"


class CorpusEntry(BaseModel):
    """Repository the table was built from, pinned to a full commit SHA."""

    model_config = ConfigDict(frozen=True)

    name: str
    url: str
    commit: str


class QuantileTable(BaseModel):
    """Values u of every input at the probabilities 0.00, 0.05, ..., 1.00."""

    model_config = ConfigDict(frozen=True)

    table_version: str
    probabilities: list[float]
    reference_time: datetime
    corpus: list[CorpusEntry]
    inputs: dict[str, list[float]]

    @model_validator(mode="after")
    def _check_points(self) -> QuantileTable:
        prefix = f"quantile table {self.table_version!r}"
        if len(self.probabilities) != len(QUANTILE_PROBABILITIES) or any(
            not math.isclose(p, q, abs_tol=1e-9) for p, q in zip(self.probabilities, QUANTILE_PROBABILITIES)
        ):
            raise ValueError(f"{prefix}: probabilities must be 0.00, 0.05, ..., 1.00 (21 values)")
        if self.reference_time.utcoffset() is None:
            raise ValueError(f"{prefix}: reference_time must be timezone-aware")
        for name in TABLE_INPUT_NAMES:
            if name not in self.inputs:
                raise ValueError(f"{prefix}: inputs.{name} is missing")
        for name, points in self.inputs.items():
            if name not in TABLE_INPUT_NAMES:
                raise ValueError(f"{prefix}: inputs.{name} is not a table input")
            if len(points) != len(QUANTILE_PROBABILITIES):
                raise ValueError(f"{prefix}: inputs.{name} must have 21 points, got {len(points)}")
            if not all(math.isfinite(p) for p in points):
                raise ValueError(f"{prefix}: inputs.{name} has a non-finite value")
            if any(b < a for a, b in zip(points, points[1:])):
                raise ValueError(f"{prefix}: inputs.{name} is decreasing")
        return self


def load_quantile_table() -> QuantileTable:
    """Read and validate the quantile table shipped in the package."""
    resource = files(TABLE_PACKAGE).joinpath("data").joinpath(TABLE_RESOURCE)
    if not resource.is_file():
        raise FileNotFoundError(f"quantile table resource not found: {TABLE_PACKAGE}/data/{TABLE_RESOURCE}")
    return QuantileTable.model_validate_json(resource.read_text(encoding="utf-8"))
