"""Git history feature calculator."""

from __future__ import annotations

from gitgeist.ingest.git_history import RawGitHistory
from gitgeist.schemas.features import GitHistoryFeatures, Hotspot


def compute_history_features(raw: RawGitHistory) -> GitHistoryFeatures:
    """Compute GitHistoryFeatures model from raw Git log extraction."""
    if not raw.is_git_repo or raw.commit_count == 0:
        return GitHistoryFeatures(
            is_git_repo=raw.is_git_repo,
            commit_count=0,
            unique_authors_count=0,
            first_commit_date=None,
            last_commit_date=None,
            repository_age_days=0,
            velocity=0.0,
            total_lines_added=0,
            total_lines_deleted=0,
            hotspots=[],
        )

    unique_authors = set(raw.authors)
    age_days = 0
    if raw.first_commit_date and raw.last_commit_date:
        delta = raw.last_commit_date - raw.first_commit_date
        age_days = max(0, delta.days)

    if age_days > 0:
        velocity = round(raw.commit_count / (age_days / 7.0), 2)
    else:
        velocity = float(raw.commit_count)

    sorted_hotspots = sorted(raw.file_changes.items(), key=lambda item: (-item[1], item[0]))
    hotspots = [
        Hotspot(path=path, change_count=count)
        for path, count in sorted_hotspots[:10]
    ]

    return GitHistoryFeatures(
        is_git_repo=True,
        commit_count=raw.commit_count,
        unique_authors_count=len(unique_authors),
        first_commit_date=raw.first_commit_date,
        last_commit_date=raw.last_commit_date,
        repository_age_days=age_days,
        velocity=velocity,
        total_lines_added=raw.total_added,
        total_lines_deleted=raw.total_deleted,
        hotspots=hotspots,
    )
