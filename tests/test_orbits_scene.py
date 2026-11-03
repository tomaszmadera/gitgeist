"""Tests for the HUD conclusions and hover details of the abstract orbits scene (spec O3, O4)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from gitgeist.features.extractor import extract_features
from gitgeist.ingest.identity import compute_identity_seed
from gitgeist.render.orbits import build_orbits_scene
from gitgeist.schemas.features import Hotspot
from gitgeist.schemas.live_state import OrbitsScene
from gitgeist.schemas.traits import TRAIT_NAMES
from gitgeist.visual import build_visual_spec, compute_traits
from tests.fixtures import builder
from tests.orbits_helpers import REFERENCE_TIME, make_features, make_scene, make_spec, with_traits

BUILDERS = {
    "single-script": builder.create_single_script_repo,
    "dormant-old": builder.create_dormant_old_repo,
    "big-team": builder.create_big_team_repo,
    "monorepo-single-author": builder.create_monorepo_single_author,
    "docs-only": builder.create_docs_only_repo,
    "fresh": builder.create_fresh_repo,
    "one-hotspot": builder.create_one_hotspot_repo,
    "deep-tree": builder.create_deep_tree_repo,
}
NEUTRAL = {name: 0.5 for name in TRAIT_NAMES}


@pytest.fixture(scope="module")
def portfolio_cache() -> dict:
    return {}


@pytest.fixture
def portfolio(tmp_path_factory: pytest.TempPathFactory, portfolio_cache: dict):
    if not portfolio_cache:
        root = tmp_path_factory.mktemp("orbits-portfolio")
        portfolio_cache.update({name: extract_features(factory(root / name)) for name, factory in BUILDERS.items()})
    return portfolio_cache


def _conclusions(**traits: float) -> list[str]:
    features = make_features()
    spec = with_traits(make_spec(features), **{**NEUTRAL, **traits})
    return build_orbits_scene(features, spec).conclusions


@pytest.mark.parametrize("name", BUILDERS)
def test_scene_for_golden_fixtures(portfolio, name: str) -> None:
    features = portfolio[name]
    traits = compute_traits(features, reference_time=REFERENCE_TIME)
    spec = build_visual_spec(features, traits, compute_identity_seed(Path(features.repository_path)), "abstract")

    scene = build_orbits_scene(features, spec, repository_name=name)

    assert scene.spec == spec
    assert scene.caption is True
    assert len(scene.conclusions) == 3 and all(scene.conclusions)
    assert [item.mass_index for item in scene.hover] == list(range(len(spec.masses)))
    assert OrbitsScene.model_validate_json(scene.model_dump_json()) == scene


def test_conclusions_pick_the_three_traits_farthest_from_half() -> None:
    # size 0.9 and alive 0.1 tie at 0.4: trait order puts size first. care is next at 0.2.
    assert _conclusions(size=0.9, alive=0.1, care=0.3) == [
        "large codebase (0.2 MB of code)",
        "last commit 10 days ago",
        "few tests (25% test files)",
    ]


def test_conclusions_break_ties_by_trait_order() -> None:
    # Every trait is equally extreme: the first three in trait order win.
    spec = with_traits(make_spec(make_features()), **{name: 1.0 for name in TRAIT_NAMES})
    scene = build_orbits_scene(make_features(), spec)
    assert scene.conclusions == [
        "large codebase (0.2 MB of code)",
        "6.0 years old",
        "active: last commit 10 days ago",
    ]


@pytest.mark.parametrize(
    ("trait", "value", "expected"),
    [
        ("size", 0.0, "small codebase (195 kB of code)"),
        ("size", 1.0, "large codebase (0.2 MB of code)"),
        ("age", 0.0, "young (2191 days of history)"),
        ("age", 1.0, "6.0 years old"),
        ("alive", 0.0, "last commit 10 days ago"),
        ("alive", 1.0, "active: last commit 10 days ago"),
        ("crowd", 0.0, "one main author (50%)"),
        ("crowd", 1.0, "5 authors"),
        ("focus", 0.0, "changes spread across the tree"),
        ("focus", 1.0, "changes concentrate in src/core.py"),
        ("care", 0.0, "few tests (25% test files)"),
        ("care", 1.0, "well tested (25% test files)"),
        ("sprawl", 0.0, "deep, narrow tree (3 top-level directories, depth 4)"),
        ("sprawl", 1.0, "wide, shallow tree (3 top-level directories, depth 4)"),
        ("prose", 0.0, "mostly code"),
        ("prose", 1.0, "text-heavy (25% documents)"),
        ("debt", 0.0, "few TODO markers"),
        ("debt", 1.0, "12 TODO markers per 1000 files"),
    ],
)
def test_one_phrase_per_trait_end(trait: str, value: float, expected: str) -> None:
    assert _conclusions(**{trait: value})[0] == expected


def test_value_exactly_half_reads_as_the_high_end() -> None:
    assert _conclusions(prose=0.5, size=0.5, alive=0.9)[0] == "active: last commit 10 days ago"
    spec = with_traits(make_spec(make_features()), **NEUTRAL)
    scene = build_orbits_scene(make_features(), spec)
    assert scene.conclusions[0] == "large codebase (0.2 MB of code)"


def test_no_history_drops_age_alive_and_crowd() -> None:
    features = make_features(
        commit_count=0, unique_authors_count=0, first_commit_date=None, last_commit_date=None,
        repository_age_days=0, hotspots=[], timeline_start=None, timeline=[], top_author_share=0.0,
    )
    spec = make_spec(features)
    # compute_traits sets age, alive and crowd to 0.0 here: they would be the most extreme.
    assert (spec.traits.age, spec.traits.alive, spec.traits.crowd) == (0.0, 0.0, 0.0)

    scene = build_orbits_scene(features, spec)

    assert len(scene.conclusions) == 3
    text = " | ".join(scene.conclusions)
    for fragment in ("history", "years old", "last commit", "author"):
        assert fragment not in text


def test_focus_without_a_knot_says_the_changes_are_spread() -> None:
    features = make_features(hotspots=[])
    spec = with_traits(make_spec(features), **{**NEUTRAL, "focus": 1.0})
    assert spec.knot is None
    assert build_orbits_scene(features, spec).conclusions[0] == "changes spread across the tree"


def test_hover_has_one_entry_per_mass_with_counts_and_hotspots() -> None:
    scene = make_scene()
    assert [(h.mass_index, h.label, h.file_count, h.file_share_percent, h.top_hotspot) for h in scene.hover] == [
        (0, "src", 40, 50, "src/core.py"),
        (1, "tests", 24, 30, "tests/test_core.py"),
        (2, ".", 8, 10, "README.md"),
        (3, "other (merged)", 8, 10, None),
    ]


def test_hover_shows_only_hotspots_among_the_top_three_and_the_best_per_mass() -> None:
    features = make_features(hotspots=[
        Hotspot(path="src/a.py", change_count=40, mass="src"),
        Hotspot(path="src/b.py", change_count=30, mass="src"),
        Hotspot(path="tests/t.py", change_count=20, mass="tests"),
        Hotspot(path="README.md", change_count=10, mass="."),
    ])
    hover = {h.label: h.top_hotspot for h in build_orbits_scene(features, make_spec(features)).hover}
    assert hover == {"src": "src/a.py", "tests": "tests/t.py", ".": None, "other (merged)": None}


def test_hover_gives_a_merged_hotspot_to_the_merged_mass() -> None:
    features = make_features(hotspots=[Hotspot(path="misc/x.py", change_count=9, mass="other")])
    hover = {h.label: h.top_hotspot for h in build_orbits_scene(features, make_spec(features)).hover}
    assert hover["other (merged)"] == "misc/x.py"


def test_caption_false_gives_empty_conclusions_and_hover_but_the_same_spec() -> None:
    quiet, loud = make_scene(caption=False), make_scene(caption=True)
    assert quiet.caption is False
    assert quiet.conclusions == [] and quiet.hover == []
    assert quiet.spec == loud.spec


def test_scene_is_deterministic() -> None:
    assert make_scene().model_dump_json() == make_scene().model_dump_json()


def test_scene_without_masses_has_no_hover() -> None:
    features = make_features()
    features = features.model_copy(update={"structure": features.structure.model_copy(update={"masses": []})})
    scene = build_orbits_scene(features, make_spec(features))
    assert scene.spec.masses == [] and scene.hover == []


def test_scene_records_engine_version_and_name() -> None:
    scene = make_scene(name=None)
    assert scene.repository_name is None
    assert scene.schema_version == "1" and scene.representation == "abstract"
    assert scene.engine_version


def test_character_spec_is_rejected() -> None:
    features = make_features()
    traits = compute_traits(features, reference_time=REFERENCE_TIME)
    from tests.orbits_helpers import IDENTITY

    character = build_visual_spec(features, traits, IDENTITY, "character")
    with pytest.raises(ValueError, match="abstract"):
        build_orbits_scene(features, character)


def test_other_style_is_rejected() -> None:
    features = make_features()
    spec = make_spec(features).model_copy(update={"style": "strata"})
    with pytest.raises(ValueError, match="orbits"):
        build_orbits_scene(features, spec)


def test_masses_must_match_features() -> None:
    features = make_features()
    spec = make_spec(features).model_copy(update={"masses": []})
    with pytest.raises(ValueError, match="masses"):
        build_orbits_scene(features, spec)


def test_wrong_types_raise_type_error() -> None:
    features = make_features()
    with pytest.raises(TypeError, match="RepositoryFeatures"):
        build_orbits_scene("features", make_spec(features))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="VisualSpec"):
        build_orbits_scene(features, "spec")  # type: ignore[arg-type]


def test_days_since_last_commit_never_negative() -> None:
    future = make_features(last_commit_date=datetime(2026, 5, 1, tzinfo=timezone.utc))
    spec = with_traits(make_spec(future), **{**NEUTRAL, "alive": 1.0})
    assert build_orbits_scene(future, spec).conclusions[0] == "active: last commit 0 days ago"
