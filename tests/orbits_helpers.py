"""Git-free features, specs and scenes for the abstract ``orbits`` renderer tests."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from gitgeist.render.orbits import build_orbits_scene
from gitgeist.schemas.features import (
    DocsSummaryFeatures,
    GitHistoryFeatures,
    Hotspot,
    Mass,
    RepositoryFeatures,
    StaticFeatures,
    StructureFeatures,
)
from gitgeist.schemas.identity import IdentitySeed
from gitgeist.schemas.live_state import OrbitsScene
from gitgeist.schemas.visual_spec import VisualSpec
from gitgeist.visual import build_visual_spec, compute_traits

REFERENCE_TIME = datetime(2026, 4, 16, tzinfo=timezone.utc)
IDENTITY = IdentitySeed(
    identity_seed=hashlib.sha256(b"orbits-root").hexdigest(), source="root-commits", root_commits=["orbits-root"]
)


def make_features(**history_overrides: object) -> RepositoryFeatures:
    """Three masses (src, tests, other), 80 files, 120 commits, a hotspot in each of two masses."""
    history = GitHistoryFeatures(
        is_git_repo=True,
        commit_count=120,
        unique_authors_count=5,
        first_commit_date=datetime(2020, 4, 16, tzinfo=timezone.utc),
        last_commit_date=datetime(2026, 4, 6, tzinfo=timezone.utc),
        repository_age_days=2191,
        velocity=1.5,
        hotspots=[
            Hotspot(path="src/core.py", change_count=40, change_share=0.4, mass="src"),
            Hotspot(path="tests/test_core.py", change_count=20, change_share=0.2, mass="tests"),
            Hotspot(path="README.md", change_count=10, change_share=0.1, mass="."),
        ],
        timeline_start="2020-04",
        timeline=[0, 3, 8, 1, 0, 0, 5, 9, 2, 0, 4, 6] * 6,
        active_months_ratio=0.6,
        top_author_share=0.5,
        top3_author_share=0.8,
    )
    history = history.model_copy(update=history_overrides)
    return RepositoryFeatures(
        repository_path="/virtual/orbits-demo",
        extracted_at=datetime(2026, 4, 16, 12, tzinfo=timezone.utc),
        static=StaticFeatures(
            file_count=80,
            directory_count=12,
            max_directory_depth=4,
            languages={"Python": 60, "Markdown": 20},
            total_size_bytes=300_000,
            code_bytes=200_000,
            code_file_count=60,
            test_file_count=15,
            test_ratio=0.25,
            doc_ratio=0.25,
            todo_density=12.0,
            todo_count=1,
            top_level_directory_count=3,
        ),
        history=history,
        docs=DocsSummaryFeatures(),
        structure=StructureFeatures(
            masses=[
                Mass(name="src", file_count=40, file_share=0.5, churn_share=0.6, dominant_language="Python"),
                Mass(name="tests", file_count=24, file_share=0.3, churn_share=0.3, dominant_language="Python"),
                Mass(name=".", file_count=8, file_share=0.1, churn_share=0.1, dominant_language="Markdown"),
                Mass(name="other", is_merged=True, file_count=8, file_share=0.1, churn_share=0.0),
            ],
            hotspot_concentration=0.4,
        ),
    )


def make_spec(features: RepositoryFeatures, identity: IdentitySeed = IDENTITY) -> VisualSpec:
    traits = compute_traits(features, reference_time=REFERENCE_TIME)
    return build_visual_spec(features, traits, identity, "abstract")


def make_scene(
    features: RepositoryFeatures | None = None, *, caption: bool = True, name: str | None = "orbits-demo"
) -> OrbitsScene:
    features = features if features is not None else make_features()
    return build_orbits_scene(features, make_spec(features), repository_name=name, caption=caption)


def with_traits(spec: VisualSpec, **values: float) -> VisualSpec:
    """Copy of spec with chosen trait values (no re-validation of derived channels)."""
    return spec.model_copy(update={"traits": spec.traits.model_copy(update=values)})
