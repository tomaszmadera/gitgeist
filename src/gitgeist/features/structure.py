"""Structure feature calculator: directory masses and change concentration."""

from __future__ import annotations

from collections import Counter

from gitgeist.ingest.git_history import RawGitHistory
from gitgeist.ingest.repository import CODE_LANGUAGES, FileScanResult, ScannedFile, is_test_path
from gitgeist.schemas.features import Hotspot, Mass, StructureFeatures

MAX_MASSES = 8
ROOT_MASS = "."
MERGED_MASS = "other"
CONCENTRATION_TOP = 10


def _segment(path: str) -> str:
    """First path segment, "." for files in the repository root."""
    head, sep, _ = path.partition("/")
    return head if sep else ROOT_MASS


def _mass(
    name: str,
    files: list[ScannedFile],
    changes: int,
    total_files: int,
    total_changes: int,
    is_merged: bool = False,
) -> Mass:
    languages = Counter(f.language for f in files if f.language is not None)
    dominant = min(languages.items(), key=lambda item: (-item[1], item[0]))[0] if languages else None
    code_files = [f for f in files if f.language in CODE_LANGUAGES]
    test_files = sum(1 for f in code_files if is_test_path(f.path))
    return Mass(
        name=name,
        is_merged=is_merged,
        file_count=len(files),
        file_share=round(len(files) / total_files, 4),
        churn_share=round(changes / total_changes, 4) if total_changes else 0.0,
        dominant_language=dominant,
        test_file_share=round(test_files / len(code_files), 4) if code_files else 0.0,
    )


def _masses(scan: FileScanResult, raw: RawGitHistory) -> list[Mass]:
    files_by_segment: dict[str, list[ScannedFile]] = {}
    for scanned in scan.files:
        files_by_segment.setdefault(_segment(scanned.path), []).append(scanned)
    if not files_by_segment:
        return []

    candidates = sorted(files_by_segment, key=lambda name: (-len(files_by_segment[name]), name))
    changes_by_segment: Counter[str] = Counter()
    for path, count in raw.file_changes.items():
        changes_by_segment[_segment(path)] += count
    total_changes = sum(changes_by_segment.values())
    outside_changes = sum(c for s, c in changes_by_segment.items() if s not in files_by_segment)

    def named(name: str) -> Mass:
        return _mass(name, files_by_segment[name], changes_by_segment[name], scan.file_count, total_changes)

    if len(candidates) <= MAX_MASSES and outside_changes == 0:
        return [named(name) for name in candidates]

    kept, merged = candidates[: MAX_MASSES - 1], candidates[MAX_MASSES - 1 :]
    merged_files = [f for name in merged for f in files_by_segment[name]]
    merged_changes = outside_changes + sum(changes_by_segment[name] for name in merged)
    other = _mass(MERGED_MASS, merged_files, merged_changes, scan.file_count, total_changes, is_merged=True)
    return [*(named(name) for name in kept), other]


def _hotspot_concentration(scan: FileScanResult, raw: RawGitHistory) -> float:
    total_changes = sum(raw.file_changes.values())
    if scan.file_count == 0 or total_changes == 0:
        return 0.0
    counts = sorted(raw.file_changes.values(), reverse=True)
    top_share = sum(counts[:CONCENTRATION_TOP]) / total_changes
    return round(top_share - min(1.0, CONCENTRATION_TOP / scan.file_count), 4)


def compute_structure_features(scan: FileScanResult, raw: RawGitHistory) -> StructureFeatures:
    """Compute directory masses and size-adjusted hotspot concentration."""
    return StructureFeatures(
        masses=_masses(scan, raw),
        hotspot_concentration=_hotspot_concentration(scan, raw),
    )


def assign_hotspot_masses(hotspots: list[Hotspot], masses: list[Mass]) -> list[Hotspot]:
    """Set Hotspot.mass to the named mass of the path's first segment, otherwise "other"."""
    named = {mass.name for mass in masses if not mass.is_merged}
    return [
        hotspot.model_copy(
            update={"mass": segment if (segment := _segment(hotspot.path)) in named else MERGED_MASS}
        )
        for hotspot in hotspots
    ]
