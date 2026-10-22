"""Deterministic normalization of repository features to values in [0, 1]."""

from gitgeist.normalization.inputs import INPUT_NAMES, raw_inputs
from gitgeist.normalization.scale import (
    NormalizedInputs,
    NormalizedValue,
    ScaleMode,
    anchor_position,
    normalize_features,
    percentile,
    smoothstep,
)
from gitgeist.normalization.table import CorpusEntry, QuantileTable, load_quantile_table

__all__ = [
    "INPUT_NAMES",
    "CorpusEntry",
    "NormalizedInputs",
    "NormalizedValue",
    "QuantileTable",
    "ScaleMode",
    "anchor_position",
    "load_quantile_table",
    "normalize_features",
    "percentile",
    "raw_inputs",
    "smoothstep",
]
