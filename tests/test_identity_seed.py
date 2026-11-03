"""Tests for the repository identity seed (plan stage 1, item 4)."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from gitgeist.ingest.identity import compute_identity_seed
from gitgeist.schemas.identity import IdentitySeed


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


@pytest.mark.parametrize("representation", ["abstract", "character"])
def test_scene_seed_depends_on_identity_not_features(representation: str) -> None:
    from gitgeist.visual import build_visual_spec, compute_traits
    from tests.orbits_helpers import IDENTITY, REFERENCE_TIME, make_features

    def seed(features, identity) -> int:
        traits = compute_traits(features, reference_time=REFERENCE_TIME)
        return build_visual_spec(features, traits, identity, representation).seeds.effective_seed

    other = IdentitySeed(identity_seed=_sha256("other-root"), source="root-commits", root_commits=["other-root"])
    assert seed(make_features(), IDENTITY) == seed(make_features(commit_count=500, unique_authors_count=9), IDENTITY)
    assert seed(make_features(), IDENTITY) != seed(make_features(), other)


def test_live_seed_differs_between_representation_modes() -> None:
    from gitgeist.visual import build_visual_spec, compute_traits
    from tests.orbits_helpers import IDENTITY, REFERENCE_TIME, make_features

    features = make_features()
    traits = compute_traits(features, reference_time=REFERENCE_TIME)
    abstract = build_visual_spec(features, traits, IDENTITY, "abstract").seeds.effective_seed
    character = build_visual_spec(features, traits, IDENTITY, "character").seeds.effective_seed

    assert abstract != character
