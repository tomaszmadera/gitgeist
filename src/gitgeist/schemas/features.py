"""Pydantic schemas for repository features."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class Hotspot(BaseModel):
    """File identified as a modification hotspot."""

    model_config = ConfigDict(frozen=True)

    path: str
    change_count: int


class StaticFeatures(BaseModel):
    """Static structural characteristics of the repository file tree."""

    model_config = ConfigDict(frozen=True)

    file_count: int = 0
    directory_count: int = 0
    max_directory_depth: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    total_size_bytes: int = 0
    avg_file_size_bytes: float = 0.0
    has_tests: bool = False
    has_documentation: bool = False
    has_ci: bool = False
    todo_count: int = 0


class GitHistoryFeatures(BaseModel):
    """Historical signals extracted from Git commit log."""

    model_config = ConfigDict(frozen=True)

    is_git_repo: bool = False
    commit_count: int = 0
    unique_authors_count: int = 0
    first_commit_date: datetime | None = None
    last_commit_date: datetime | None = None
    repository_age_days: int = 0
    velocity: float = 0.0
    total_lines_added: int = 0
    total_lines_deleted: int = 0
    hotspots: list[Hotspot] = Field(default_factory=list)


class DocsSummaryFeatures(BaseModel):
    """Signals extracted from repository documentation and metadata."""

    model_config = ConfigDict(frozen=True)

    has_readme: bool = False
    readme_length_chars: int = 0
    readme_snippet: str = ""
    license_type: str | None = None


class RepositoryFeatures(BaseModel):
    """Aggregated repository feature profile (Layer 1 in Gitgeist architecture)."""

    model_config = ConfigDict(frozen=True)

    repository_path: str
    extracted_at: datetime
    static: StaticFeatures
    history: GitHistoryFeatures
    docs: DocsSummaryFeatures
