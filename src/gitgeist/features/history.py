"""Git history feature calculator."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from gitgeist.ingest.git_history import RawGitHistory
from gitgeist.schemas.features import GitHistoryFeatures, Hotspot


def _month_index(moment: datetime) -> int:
    return moment.year * 12 + moment.month - 1


def _timeline(commit_dates: list[datetime]) -> tuple[str | None, list[int]]:
    """Commits per UTC calendar month from the first to the last commit month."""
    if not commit_dates:
        return None, []
    first = min(commit_dates)
    start = _month_index(first)
    counts = [0] * (_month_index(max(commit_dates)) - start + 1)
    for moment in commit_dates:
        counts[_month_index(moment) - start] += 1
    return f"{first.year:04d}-{first.month:02d}", counts


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

    total_changes = sum(raw.file_changes.values())
    sorted_hotspots = sorted(raw.file_changes.items(), key=lambda item: (-item[1], item[0]))
    hotspots = [
        Hotspot(path=path, change_count=count, change_share=round(count / total_changes, 4))
        for path, count in sorted_hotspots[:10]
    ]

    timeline_start, timeline = _timeline(raw.commit_dates)
    active_months_ratio = round(sum(1 for c in timeline if c) / len(timeline), 4) if timeline else 0.0
    author_counts = sorted(Counter(raw.authors).values(), reverse=True)

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
        timeline_start=timeline_start,
        timeline=timeline,
        active_months_ratio=active_months_ratio,
        top_author_share=round(sum(author_counts[:1]) / raw.commit_count, 4),
        top3_author_share=round(sum(author_counts[:3]) / raw.commit_count, 4),
    )


def days_since_last_commit(history: GitHistoryFeatures, reference_time: datetime) -> float | None:
    """Days from the last commit to reference_time, rounded to 4 places, at least 0.0.

    None when the history has no last commit. Raises ValueError for a naive reference_time.
    """
    if reference_time.tzinfo is None or reference_time.utcoffset() is None:
        raise ValueError("reference_time must be timezone-aware")
    if history.last_commit_date is None:
        return None
    days = (reference_time - history.last_commit_date).total_seconds() / 86400
    return round(max(0.0, days), 4)
