"""Git-free features, specs and scenes for the character ``creature`` renderer tests."""

from __future__ import annotations

from gitgeist.render.creature import build_creature_scene
from gitgeist.schemas.features import Mass, RepositoryFeatures
from gitgeist.schemas.live_state import CreatureScene
from gitgeist.schemas.visual_spec import VisualSpec
from gitgeist.visual import build_visual_spec, compute_traits
from tests.orbits_helpers import IDENTITY, REFERENCE_TIME, make_features

__all__ = [
    "BUILDERS", "CORPUS_LIKE", "make_character_spec", "make_creature_scene", "make_features", "mass_table",
    "with_masses",
]

# The git-free golden fixtures of the stage 3 and stage 4 tests, as repository builders.
BUILDERS = {
    "single-script": "create_single_script_repo",
    "dormant-old": "create_dormant_old_repo",
    "big-team": "create_big_team_repo",
    "monorepo-single-author": "create_monorepo_single_author",
    "docs-only": "create_docs_only_repo",
    "fresh": "create_fresh_repo",
    "one-hotspot": "create_one_hotspot_repo",
    "deep-tree": "create_deep_tree_repo",
}

# (file share, churn share) of the 7-8 mass corpus repositories that stress the body plan (stage 5 baseline table).
CORPUS_LIKE = {
    "flask": [(0.37, 0.28), (0.26, 0.12), (0.18, 0.06), (0.11, 0.09), (0.04, 0.16), (0.04, 0.02), (0.01, 0.0), (0.0, 0.26)],
    "click": [(0.33, 0.16), (0.23, 0.19), (0.22, 0.05), (0.10, 0.17), (0.06, 0.03), (0.05, 0.2), (0.01, 0.0), (0.0, 0.21)],
    "zlib": [(0.6, 0.35), (0.18, 0.49), (0.05, 0.02), (0.03, 0.02), (0.03, 0.03), (0.03, 0.02), (0.02, 0.0), (0.06, 0.08)],
}


def mass_table(rows: list[tuple[float, float]]) -> list[Mass]:
    """Masses from (file share, churn share) rows; the last row is the merged mass."""
    return [
        Mass(name=f"d{i}" if i < len(rows) - 1 else "other", is_merged=i == len(rows) - 1, file_count=int(100 * share),
             file_share=share, churn_share=churn, dominant_language="Python")
        for i, (share, churn) in enumerate(rows)
    ]


def with_masses(features: RepositoryFeatures, masses: list[Mass]) -> RepositoryFeatures:
    """Copy of features with other directory masses (shares are used as given)."""
    return features.model_copy(update={"structure": features.structure.model_copy(update={"masses": masses})})


def make_character_spec(features: RepositoryFeatures | None = None, **trait_overrides: float) -> VisualSpec:
    features = features if features is not None else make_features()
    traits = compute_traits(features, reference_time=REFERENCE_TIME)
    if trait_overrides:
        traits = traits.model_copy(update=trait_overrides)
    return build_visual_spec(features, traits, IDENTITY, "character")


def make_creature_scene(
    features: RepositoryFeatures | None = None, *, caption: bool = True, name: str | None = "creature-demo",
    **trait_overrides: float,
) -> CreatureScene:
    features = features if features is not None else make_features()
    return build_creature_scene(
        features, make_character_spec(features, **trait_overrides), repository_name=name, caption=caption
    )
