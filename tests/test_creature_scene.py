"""Tests for the character ``creature`` scene: builder, validators, shared HUD text, errors (stage 5 spec)."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitgeist.features.extractor import extract_features
from gitgeist.ingest.identity import compute_identity_seed
from gitgeist.render.creature import build_creature_scene
from gitgeist.render.orbits import build_orbits_scene
from gitgeist.schemas.live_state import CreatureScene
from gitgeist.visual import build_visual_spec, compute_traits
from tests.creature_helpers import BUILDERS, make_character_spec, make_creature_scene, make_features
from tests.fixtures import builder
from tests.orbits_helpers import IDENTITY, REFERENCE_TIME, make_spec

SNAPSHOT = Path(__file__).parent / "golden" / "live" / "creature-0.11.0-live-state.json"


@pytest.fixture(scope="module")
def portfolio(tmp_path_factory: pytest.TempPathFactory) -> dict:
    root = tmp_path_factory.mktemp("creature-portfolio")
    return {name: extract_features(getattr(builder, factory)(root / name)) for name, factory in BUILDERS.items()}


@pytest.mark.parametrize("name", list(BUILDERS))
def test_scene_for_golden_fixtures(portfolio: dict, name: str) -> None:
    features = portfolio[name]
    traits = compute_traits(features, reference_time=REFERENCE_TIME)
    spec = build_visual_spec(features, traits, compute_identity_seed(Path(features.repository_path)), "character")

    scene = build_creature_scene(features, spec, repository_name=name)

    assert scene.spec == spec and scene.caption is True
    assert len(scene.conclusions) == 3 and all(scene.conclusions)
    assert [item.mass_index for item in scene.hover] == list(range(len(spec.masses)))
    assert CreatureScene.model_validate_json(scene.model_dump_json()) == scene
    parts = ([scene.body.torso.mass_index] if scene.body.torso else []) + [limb.mass_index for limb in scene.body.limbs]
    assert sorted(parts) == list(range(len(spec.masses)))
    assert all(len(limb.segments) == 1 + spec.topology.nesting_levels for limb in scene.body.limbs)


def test_conclusions_and_hover_equal_the_orbits_ones_for_the_same_traits() -> None:
    features = make_features()
    creature = make_creature_scene(features)
    traits = creature.spec.traits
    orbits_spec = make_spec(features).model_copy(update={"traits": traits})
    orbits = build_orbits_scene(features, orbits_spec)
    assert creature.conclusions == orbits.conclusions
    assert creature.hover == orbits.hover


def test_caption_off_gives_empty_conclusions_and_hover_and_the_same_body() -> None:
    on, off = make_creature_scene(), make_creature_scene(caption=False)
    assert off.caption is False and off.conclusions == [] and off.hover == []
    assert on.body == off.body and on.spec == off.spec


def test_scene_is_deterministic_and_carries_the_repository_name() -> None:
    assert make_creature_scene() == make_creature_scene()
    assert make_creature_scene(name="demo").repository_name == "demo"
    assert make_creature_scene(name=None).repository_name is None


def test_builder_errors() -> None:
    features = make_features()
    spec = make_character_spec(features)
    with pytest.raises(TypeError, match="RepositoryFeatures"):
        build_creature_scene("features", spec)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="VisualSpec"):
        build_creature_scene(features, "spec")  # type: ignore[arg-type]
    abstract = build_visual_spec(features, compute_traits(features, reference_time=REFERENCE_TIME), IDENTITY, "abstract")
    with pytest.raises(ValueError, match="character"):
        build_creature_scene(features, abstract)
    with pytest.raises(ValueError, match="style"):
        build_creature_scene(features, spec.model_copy(update={"style": "orbits"}))
    other = features.model_copy(update={"structure": features.structure.model_copy(update={"masses": features.structure.masses[:2]})})
    with pytest.raises(ValueError, match="masses"):
        build_creature_scene(other, spec)


def test_creature_scene_matches_the_0_11_0_snapshot() -> None:
    """Regression anchor: the scene of ``make_creature_scene()`` at 0.11.0, engine version masked."""
    from gitgeist._version import current_engine_version

    state = make_creature_scene().model_dump_json(indent=2).replace(current_engine_version(), "<ENGINE_VERSION>")
    assert state == SNAPSHOT.read_text(encoding="utf-8")
