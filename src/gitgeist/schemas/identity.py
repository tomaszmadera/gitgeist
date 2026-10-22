"""Repository identity seed schema."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IdentitySeed(BaseModel):
    """Stable identity of a repository, independent of its current commit.

    Written as ``identity-seed.json`` (product section 23, optional artifacts).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    identity_seed: str = Field(
        pattern=r"^[0-9a-f]{64}$",
        description=(
            "SHA-256 hex digest of the sorted root commit hashes joined by newlines, "
            "or of the directory name when the path is not a Git repository root with commits"
        ),
    )
    source: Literal["root-commits", "directory-name"] = Field(
        description="What the identity seed was derived from"
    )
    root_commits: list[str] = Field(
        default_factory=list,
        description="Sorted root commit hashes reachable from HEAD; empty for directory-name",
    )
