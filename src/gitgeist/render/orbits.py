"""Python half of the abstract ``orbits`` renderer: HUD conclusions and hover text.

The browser draws only from ``VisualSpec``. Everything it needs that the spec does
not carry (three plain conclusions about the repository and one hover entry per
mass) is computed here from the extracted features (spec O3, O4).
"""

from gitgeist.schemas.features import Hotspot, RepositoryFeatures
from gitgeist.schemas.live_state import HoverDetail, OrbitsScene
from gitgeist.schemas.traits import TRAIT_NAMES
from gitgeist.schemas.visual_spec import VisualSpec

CONCLUSION_COUNT = 3
HISTORY_TRAITS = frozenset({"age", "alive", "crowd"})
HOTSPOT_RANK = 3
MERGED_LABEL = "other (merged)"
DAYS_PER_YEAR = 365.25


def _top_hotspots(features: RepositoryFeatures, count: int) -> list[Hotspot]:
    return sorted(features.history.hotspots, key=lambda item: (-item.change_count, item.path))[:count]


def _days_since_last_commit(features: RepositoryFeatures, spec: VisualSpec) -> int:
    last = features.history.last_commit_date
    if last is None:
        return 0
    if last.utcoffset() is None:
        raise ValueError("last_commit_date must be timezone-aware")
    return max(0, round((spec.traits.reference_time - last).total_seconds() / 86400))


def _phrase(trait: str, high: bool, features: RepositoryFeatures, spec: VisualSpec) -> str:
    static, history = features.static, features.history
    if trait == "size":
        if high:
            return f"large codebase ({static.code_bytes / 1024 ** 2:.1f} MB of code)"
        return f"small codebase ({round(static.code_bytes / 1024)} kB of code)"
    if trait == "age":
        if high:
            return f"{history.repository_age_days / DAYS_PER_YEAR:.1f} years old"
        return f"young ({history.repository_age_days} days of history)"
    if trait == "alive":
        days = _days_since_last_commit(features, spec)
        return f"active: last commit {days} days ago" if high else f"last commit {days} days ago"
    if trait == "crowd":
        if high:
            return f"{history.unique_authors_count} authors"
        return f"one main author ({round(history.top_author_share * 100)}%)"
    if trait == "focus":
        top = _top_hotspots(features, 1)
        if high and spec.knot is not None and top:
            return f"changes concentrate in {top[0].path}"
        return "changes spread across the tree"
    if trait == "care":
        label = "well tested" if high else "few tests"
        return f"{label} ({round(static.test_ratio * 100)}% test files)"
    if trait == "sprawl":
        if static.top_level_directory_count == 0:
            return "flat tree, all files at the root"
        label = "wide, shallow tree" if high else "deep, narrow tree"
        return f"{label} ({static.top_level_directory_count} top-level directories, depth {static.max_directory_depth})"
    if trait == "prose":
        return f"text-heavy ({round(static.doc_ratio * 100)}% documents)" if high else "mostly code"
    if trait == "debt":
        if high:
            return f"{round(static.todo_density)} TODO markers per 1000 files"
        return "few TODO markers"
    raise ValueError(f"unknown trait {trait!r}")


def _conclusions(features: RepositoryFeatures, spec: VisualSpec) -> list[str]:
    has_history = features.history.commit_count > 0
    candidates = [
        (abs(getattr(spec.traits, name) - 0.5), order, name)
        for order, name in enumerate(TRAIT_NAMES)
        if has_history or name not in HISTORY_TRAITS
    ]
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [
        _phrase(name, getattr(spec.traits, name) >= 0.5, features, spec)
        for _, _, name in candidates[:CONCLUSION_COUNT]
    ]


def _mass_index_of(spec: VisualSpec, mass_name: str | None) -> int | None:
    """Owning mass of a hotspot: a merged mass wins over a real directory of the same name."""
    candidates = [i for i, mass in enumerate(spec.masses) if mass.name == mass_name]
    if not candidates:
        return None
    return next((i for i in candidates if spec.masses[i].is_merged), candidates[0])


def _hover(features: RepositoryFeatures, spec: VisualSpec) -> list[HoverDetail]:
    owned: dict[int, str] = {}
    for hotspot in _top_hotspots(features, HOTSPOT_RANK):
        index = _mass_index_of(spec, hotspot.mass)
        if index is not None:
            owned.setdefault(index, hotspot.path)
    return [
        HoverDetail(
            mass_index=index,
            label=MERGED_LABEL if mass.is_merged else mass.name,
            file_count=source.file_count,
            file_share_percent=round(mass.file_share * 100),
            top_hotspot=owned.get(index),
        )
        for index, (mass, source) in enumerate(zip(spec.masses, features.structure.masses, strict=True))
    ]


def build_orbits_scene(
    features: RepositoryFeatures,
    spec: VisualSpec,
    *,
    repository_name: str | None = None,
    caption: bool = True,
) -> OrbitsScene:
    """Build the abstract live scene: the VisualSpec plus HUD conclusions and hover details.

    Raises:
        TypeError: If features or spec have the wrong type.
        ValueError: If spec is not an abstract ``orbits`` scene or its masses do not
            match ``features.structure.masses``.
    """
    if not isinstance(features, RepositoryFeatures):
        raise TypeError(f"Expected RepositoryFeatures, got {type(features).__name__}")
    if not isinstance(spec, VisualSpec):
        raise TypeError(f"Expected VisualSpec, got {type(spec).__name__}")
    if spec.representation != "abstract":
        raise ValueError(f"orbits draws the abstract representation, got {spec.representation!r}")
    if spec.style != "orbits":
        raise ValueError(f"orbits draws style 'orbits', got {spec.style!r}")
    if len(spec.masses) != len(features.structure.masses):
        raise ValueError("spec masses do not match features masses")
    return OrbitsScene(
        schema_version="1",
        representation="abstract",
        repository_name=repository_name,
        caption=caption,
        conclusions=_conclusions(features, spec) if caption else [],
        hover=_hover(features, spec) if caption else [],
        spec=spec,
    )
