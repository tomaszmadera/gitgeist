"""Offline synthetic portfolio and explicit-update scene snapshots."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gitgeist.features.extractor import extract_features
from gitgeist.ingest.identity import compute_identity_seed
from gitgeist.schemas.traits import TRAIT_NAMES
from gitgeist.visual import build_visual_spec, compute_traits, spec_distance
from tests.fixtures import builder

REF = datetime(2026, 4, 16, tzinfo=timezone.utc)
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
# Floors of the first passing run, recorded in stage-3-golden-threshold.txt.
THRESHOLDS = {"abstract": 0.05, "character": 0.02}
GOLDEN = Path(__file__).parent / "golden" / "visual_spec"


@pytest.fixture(scope="module")
def golden_environment_sentinel():
    """Make construction before per-test isolation observable without secrets."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("GITGEIST_GOLDEN_ENV_SENTINEL", "safe-test-sentinel")
        yield


@pytest.fixture(scope="module")
def portfolio_cache():
    """Cache only the results; repository construction needs function isolation."""
    return {}


@pytest.fixture
def portfolio(tmp_path_factory: pytest.TempPathFactory, golden_environment_sentinel, portfolio_cache, isolated_environ):
    sentinel_visible = "GITGEIST_GOLDEN_ENV_SENTINEL" in os.environ
    assert not sentinel_visible, "portfolio builds outside per-test environment isolation"
    if not portfolio_cache:
        root = tmp_path_factory.mktemp("portfolio")
        portfolio_cache.update({name: extract_features(factory(root / name)) for name, factory in BUILDERS.items()})
    return portfolio_cache


def test_fixture_contracts(portfolio) -> None:
    assert portfolio["single-script"].static.file_count == 1
    assert portfolio["single-script"].history.commit_count == 3
    assert portfolio["single-script"].history.unique_authors_count == 1
    old = portfolio["dormant-old"].history
    assert old.commit_count == 10 and old.first_commit_date.year == 2012 and old.last_commit_date.year == 2016
    team = portfolio["big-team"]
    assert team.history.commit_count == 40 and team.history.unique_authors_count == 30
    assert team.static.has_ci
    mono = portfolio["monorepo-single-author"]
    assert mono.static.top_level_directory_count == 8 and len(mono.static.languages) == 2
    assert mono.history.commit_count == 60 and mono.history.unique_authors_count == 1
    assert set(portfolio["docs-only"].static.languages) == {"Markdown", "Text"}
    assert portfolio["fresh"].static.file_count == 3 and portfolio["fresh"].history.commit_count == 1
    hotspot = portfolio["one-hotspot"]
    assert hotspot.static.file_count == 20 and hotspot.history.commit_count == 30
    assert hotspot.history.hotspots[0].change_count == 25
    deep = portfolio["deep-tree"].static
    assert deep.max_directory_depth == 10 and deep.todo_count == 5


@pytest.mark.parametrize("representation", ["abstract", "character"])
def test_golden_diversity(portfolio, representation: str, update_golden: bool) -> None:
    specs = {}
    for name, features in portfolio.items():
        traits = compute_traits(features, reference_time=REF)
        spec = build_visual_spec(features, traits, compute_identity_seed(Path(features.repository_path)), representation)
        specs[name] = spec
        snapshot = GOLDEN / f"{name}-{representation}.json"
        if update_golden:
            GOLDEN.mkdir(parents=True, exist_ok=True)
            snapshot.write_text(spec.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
        assert snapshot.is_file(), f"missing snapshot: {snapshot.name}; set GITGEIST_UPDATE_GOLDEN=1 to write it"
        assert json.loads(snapshot.read_text(encoding="utf-8")) == spec.model_dump(mode="json")
    for name in TRAIT_NAMES:
        assert len({getattr(s.traits, name) for s in specs.values()}) > 1, name
    nearest = {name: min(spec_distance(spec, other) for key, other in specs.items() if key != name)
               for name, spec in specs.items()}
    minimum = min(nearest.values())
    print(f"{representation}: smallest nearest-neighbour distance = {minimum:.12f}")
    assert minimum >= THRESHOLDS[representation]
