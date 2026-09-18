"""Gitgeist package - emotional repository portrait system."""

from __future__ import annotations

import tomllib
from pathlib import Path

try:
    _pyproject_path = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    with open(_pyproject_path, "rb") as _f:
        __version__: str = tomllib.load(_f)["project"]["version"]
except Exception:  # pragma: no cover
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("gitgeist")
    except PackageNotFoundError:
        __version__ = "0.0.1"

from gitgeist.features.extractor import extract_features
from gitgeist.interpretation.emotional_model import evaluate_emotional_state
from gitgeist.schemas.emotional import (
    ChoiceDistribution,
    EmotionalChoices,
    EmotionalNouls,
    EmotionalScores,
    EmotionalState,
)
from gitgeist.schemas.features import (
    DocsSummaryFeatures,
    GitHistoryFeatures,
    Hotspot,
    RepositoryFeatures,
    StaticFeatures,
)

__all__ = [
    "ChoiceDistribution",
    "DocsSummaryFeatures",
    "EmotionalChoices",
    "EmotionalNouls",
    "EmotionalScores",
    "EmotionalState",
    "GitHistoryFeatures",
    "Hotspot",
    "RepositoryFeatures",
    "StaticFeatures",
    "__version__",
    "evaluate_emotional_state",
    "extract_features",
]
