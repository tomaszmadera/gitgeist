"""Tests for the repository identity seed (plan stage 1, item 4)."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from gitgeist.ingest.identity import compute_identity_seed
from gitgeist.render.abstract_renderer import generate_abstract_simulation
from gitgeist.render.character_renderer import generate_character_simulation
from gitgeist.schemas.identity import IdentitySeed
from gitgeist.schemas.visual_latent import (
    MaterialityDistribution,
    VisualLatentAxes,
    VisualLatentProfile,
)


def _git(repo: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Seed Author",
        "GIT_AUTHOR_EMAIL": "seed@test.local",
        "GIT_COMMITTER_NAME": "Seed Author",
        "GIT_COMMITTER_EMAIL": "seed@test.local",
        "GIT_AUTHOR_DATE": "2026-04-01T10:00:00Z",
        "GIT_COMMITTER_DATE": "2026-04-01T10:00:00Z",
    }
    return subprocess.run(
        ["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True
    ).stdout.strip()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _profile(axis_value: float) -> VisualLatentProfile:
    return VisualLatentProfile(
        axes=VisualLatentAxes(**{name: axis_value for name in VisualLatentAxes.model_fields}),
        materiality=MaterialityDistribution(
            weights={"organic": 0.25, "mechanical": 0.25, "crystalline": 0.25, "ethereal": 0.25},
            dominant="organic",
        ),
        dominant_features=["sharpness"],
    )


def test_identity_seed_hashes_the_root_commit(clean_modular_repo: Path) -> None:
    root = _git(clean_modular_repo, "rev-list", "--max-parents=0", "HEAD")

    identity = compute_identity_seed(clean_modular_repo)

    assert identity == IdentitySeed(
        identity_seed=_sha256(root), source="root-commits", root_commits=[root]
    )


def test_identity_seed_is_stable_across_commits_and_clones(
    clean_modular_repo: Path, tmp_path: Path
) -> None:
    before = compute_identity_seed(clean_modular_repo)
    (clean_modular_repo / "README.md").write_text("# Changed\n", encoding="utf-8")
    _git(clean_modular_repo, "commit", "-am", "docs: change README")
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", str(clean_modular_repo), str(clone))

    assert compute_identity_seed(clean_modular_repo) == before
    assert compute_identity_seed(clone) == before


def test_identity_seed_differs_for_different_roots(
    minimal_repo: Path, clean_modular_repo: Path
) -> None:
    assert (
        compute_identity_seed(minimal_repo).identity_seed
        != compute_identity_seed(clean_modular_repo).identity_seed
    )


def test_identity_seed_uses_all_roots_sorted(minimal_repo: Path) -> None:
    first_root = _git(minimal_repo, "rev-list", "--max-parents=0", "HEAD")
    _git(minimal_repo, "checkout", "-q", "--orphan", "other")
    _git(minimal_repo, "rm", "-rq", "--cached", ".")
    (minimal_repo / "other.txt").write_text("other history\n", encoding="utf-8")
    _git(minimal_repo, "add", "other.txt")
    _git(minimal_repo, "commit", "-m", "unrelated root")
    second_root = _git(minimal_repo, "rev-parse", "HEAD")
    _git(minimal_repo, "checkout", "-q", "-f", "main")
    _git(minimal_repo, "merge", "-q", "--allow-unrelated-histories", "-m", "merge", "other")
    roots = sorted([first_root, second_root])

    identity = compute_identity_seed(minimal_repo)

    assert identity.root_commits == roots
    assert identity.identity_seed == _sha256("\n".join(roots))


def test_identity_seed_without_git_uses_directory_name(non_git_dir: Path) -> None:
    identity = compute_identity_seed(non_git_dir)

    assert identity == IdentitySeed(
        identity_seed=_sha256(non_git_dir.name), source="directory-name", root_commits=[]
    )


def test_identity_seed_for_repository_without_commits_uses_directory_name(tmp_path: Path) -> None:
    repo = tmp_path / "empty-repo"
    repo.mkdir()
    _git(repo, "init", "-q")

    assert compute_identity_seed(repo).source == "directory-name"


def test_identity_seed_for_subdirectory_of_repository_uses_directory_name(
    clean_modular_repo: Path,
) -> None:
    # Same rule as ingest/git_history.py: only a repository root counts as a repository.
    identity = compute_identity_seed(clean_modular_repo / "src")

    assert identity == IdentitySeed(
        identity_seed=_sha256("src"), source="directory-name", root_commits=[]
    )


@pytest.mark.parametrize(
    "generator", [generate_abstract_simulation, generate_character_simulation]
)
def test_live_seed_depends_on_identity_not_profile(generator) -> None:
    identity = _sha256("root")

    seed_a = generator(_profile(0.2), identity_seed=identity).seed
    seed_b = generator(_profile(0.9), identity_seed=identity).seed
    seed_other = generator(_profile(0.2), identity_seed=_sha256("other-root")).seed

    assert seed_a == seed_b
    assert seed_a != seed_other


def test_live_seed_differs_between_representation_modes() -> None:
    identity = _sha256("root")

    abstract = generate_abstract_simulation(_profile(0.5), identity_seed=identity)
    character = generate_character_simulation(_profile(0.5), identity_seed=identity)

    assert abstract.seed != character.seed
