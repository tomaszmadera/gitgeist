"""Regression tests: engine_version defaults resolve to the real package version.

Defect: LiveSimulationState, EmotionalState and VisualLatentProfile carried
hardcoded defaults ("0.1.0-beta.1/2/3"), so the live HTML preview rendered
"Engine: Gitgeist v0.1.0-beta.3" regardless of the installed version.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest

import gitgeist
from gitgeist._version import current_engine_version
from gitgeist.features.extractor import extract_features
from gitgeist.interpretation.emotional_model import evaluate_emotional_state
from gitgeist.schemas.emotional import EmotionalState
from gitgeist.schemas.live_state import LiveSimulationState
from gitgeist.schemas.visual_latent import VisualLatentProfile

_MODELS_WITH_ENGINE_VERSION = (EmotionalState, VisualLatentProfile, LiveSimulationState)


@pytest.mark.parametrize("model", _MODELS_WITH_ENGINE_VERSION)
def test_schema_engine_version_default_follows_installed_version(
    model: type[EmotionalState] | type[VisualLatentProfile] | type[LiveSimulationState],
) -> None:
    factory = model.model_fields["engine_version"].default_factory
    assert factory is not None, f"{model.__name__} must define a default_factory"
    assert factory() == current_engine_version()


def test_schema_engine_version_defaults_match_package_version() -> None:
    assert current_engine_version() == gitgeist.__version__


def test_evaluate_emotional_state_defaults_to_installed_version(
    clean_modular_repo: Path,
) -> None:
    features = extract_features(clean_modular_repo)
    state = evaluate_emotional_state(features)
    assert state.engine_version == current_engine_version()


def test_evaluate_emotional_state_explicit_version_wins(clean_modular_repo: Path) -> None:
    features = extract_features(clean_modular_repo)
    state = evaluate_emotional_state(features, engine_version="9.9.9")
    assert state.engine_version == "9.9.9"


def test_current_engine_version_falls_back_to_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gitgeist import _version

    def raise_package_not_found(name: str) -> str:
        raise PackageNotFoundError(name)

    monkeypatch.setattr(_version, "version", raise_package_not_found)
    monkeypatch.setattr(
        _version,
        "_PYPROJECT_PATH",
        Path("/nonexistent/pyproject.toml"),
    )
    assert _version.current_engine_version() == "unknown"
