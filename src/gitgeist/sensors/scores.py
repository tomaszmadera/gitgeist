"""Continuous emotional scores calculation from repository features."""

from __future__ import annotations

from gitgeist.schemas.emotional import EmotionalScores
from gitgeist.schemas.features import RepositoryFeatures


def _clamp(val: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, round(val, 4)))


def calculate_scores(features: RepositoryFeatures) -> EmotionalScores:
    """Calculate normalized emotional metric scores [0.0, 1.0] from RepositoryFeatures."""
    static = features.static
    history = features.history
    docs = features.docs

    # 1. Coherence
    # High modularity, documentation presence, and dominant language share promote coherence
    total_lang_files = sum(static.languages.values()) if static.languages else 0
    lang_coherence = (max(static.languages.values()) / max(1, total_lang_files)) if total_lang_files > 0 else 0.5
    doc_coherence = (0.2 if docs.has_readme else 0.0) + (0.1 if static.has_documentation else 0.0)
    struct_coherence = 0.35 if static.directory_count > 0 else 0.15
    if static.file_count > 5 and static.directory_count == 0:
        struct_coherence = 0.05
    coherence = _clamp(0.15 + 0.3 * lang_coherence + struct_coherence + doc_coherence)

    # 2. Maturity
    # Age in days, commit count, tests, license, and CI indicate project maturity
    age_factor = min(1.0, history.repository_age_days / 180.0) * 0.25
    commit_factor = min(1.0, history.commit_count / 30.0) * 0.2
    test_factor = 0.25 if static.has_tests else 0.0
    license_factor = 0.15 if docs.license_type else 0.0
    ci_factor = 0.15 if static.has_ci else 0.0
    maturity = _clamp(age_factor + commit_factor + test_factor + license_factor + ci_factor)

    # 3. Volatility
    # Rapid changes, velocity, and churn relative to project size
    if not history.is_git_repo or history.commit_count <= 1:
        volatility = 0.1
    else:
        velocity_norm = min(1.0, history.velocity / 5.0)
        total_churn = history.total_lines_added + history.total_lines_deleted
        churn_norm = min(1.0, total_churn / max(100.0, static.total_size_bytes / 10.0))
        volatility = _clamp(0.6 * velocity_norm + 0.4 * churn_norm)

    # 4. Fragility
    # Hotspot concentration in few files, lack of tests, high TODO/FIXME count
    hotspot_risk = 0.0
    if history.hotspots and history.commit_count > 0:
        top_hotspot_changes = history.hotspots[0].change_count
        hotspot_risk = min(0.4, (top_hotspot_changes / history.commit_count) * 0.5)
    test_risk = 0.35 if not static.has_tests else 0.05
    todo_risk = min(0.3, static.todo_count * 0.05)
    fragility = _clamp(0.1 + hotspot_risk + test_risk + todo_risk)

    # 5. Novelty
    # Freshness, recent creations, low repository age
    if not history.is_git_repo:
        novelty = 0.5
    else:
        freshness = 1.0 - min(1.0, history.repository_age_days / 90.0)
        novelty = _clamp(0.25 + 0.5 * freshness + (0.25 if history.commit_count < 10 else 0.0))

    # 6. Discipline
    # Structural hygiene, test presence, CI configuration, documentation, low TODOs
    discipline = 0.0
    if static.has_ci:
        discipline += 0.3
    if static.has_tests:
        discipline += 0.3
    if docs.has_readme:
        discipline += 0.15
    if docs.license_type:
        discipline += 0.1
    if static.directory_count > 0:
        discipline += 0.15
    discipline -= min(0.2, static.todo_count * 0.03)
    discipline = _clamp(discipline)

    # 7. Tension
    # Active modification friction, hotspot churn, author collisions
    hotspot_intensity = 0.0
    if history.hotspots and history.commit_count > 0:
        hotspot_intensity = min(0.5, history.hotspots[0].change_count / history.commit_count)
    velocity_tension = min(0.3, history.velocity / 10.0)
    author_factor = min(0.2, (history.unique_authors_count - 1) * 0.05) if history.unique_authors_count > 1 else 0.0
    tension = _clamp(0.1 + hotspot_intensity + velocity_tension + author_factor)

    # 8. Chaos
    # Flat root structure, missing tests and CI, high TODO counts
    chaos = 0.05
    if static.directory_count == 0 and static.file_count > 3:
        chaos += 0.35
    elif static.directory_count == 0 and static.file_count > 1:
        chaos += 0.15
    if not static.has_tests:
        chaos += 0.2
    if not docs.has_readme:
        chaos += 0.15
    if not static.has_ci:
        chaos += 0.1
    chaos += min(0.2, static.todo_count * 0.03)
    if static.has_tests and static.has_ci and static.directory_count > 0:
        chaos = max(0.05, chaos - 0.35)
    chaos = _clamp(chaos)

    # 9. Identity strength
    # Detailed README, clear license, well-defined languages, established history
    readme_score = min(0.4, docs.readme_length_chars / 500.0) if docs.has_readme else 0.0
    license_score = 0.2 if docs.license_type else 0.0
    lang_score = 0.2 if static.languages else 0.0
    commit_score = min(0.2, history.commit_count / 10.0)
    identity_strength = _clamp(0.1 + readme_score + license_score + lang_score + commit_score)

    # 10. Internal conflict
    # Contradictory signals: high velocity with zero tests, chaotic root with CI, etc.
    conflict = 0.05
    if not static.has_tests and history.velocity > 2.0:
        conflict += 0.3
    if static.directory_count == 0 and static.file_count > 5:
        conflict += 0.25
    if static.todo_count > 5 and static.has_ci:
        conflict += 0.2
    if len(static.languages) > 3:
        conflict += 0.2
    internal_conflict = _clamp(conflict)

    return EmotionalScores(
        coherence=coherence,
        maturity=maturity,
        volatility=volatility,
        fragility=fragility,
        novelty=novelty,
        discipline=discipline,
        tension=tension,
        chaos=chaos,
        identity_strength=identity_strength,
        internal_conflict=internal_conflict,
    )
