"""Compose portrait traits from the stage 2 normalized inputs."""

from datetime import datetime, timezone

from gitgeist.normalization import QuantileTable, ScaleMode, normalize_features
from gitgeist.schemas.features import RepositoryFeatures
from gitgeist.schemas.traits import Traits


def compute_traits(
    features: RepositoryFeatures,
    scale: ScaleMode = "absolute",
    *,
    reference_time: datetime | None = None,
    table: QuantileTable | None = None,
) -> Traits:
    """Compose weighted means, retaining full precision until storage."""
    reference = reference_time
    if reference is None:
        if features.extracted_at.utcoffset() is None:
            raise ValueError("reference_time must be timezone-aware")
        reference = features.extracted_at.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    normalized = normalize_features(features, scale, reference_time=reference, table=table)
    v = {name: item.value for name, item in normalized.inputs.items()}
    values = dict(
        size=v["code_size"], age=v["age"], alive=0.5 * v["recency"] + 0.5 * v["active_months"],
        crowd=0.5 * v["authors"] + 0.5 * (1 - v["top_author_share"]), focus=v["focus"],
        care=0.75 * v["test_ratio"] + 0.25 * v["ci"],
        sprawl=0.5 * v["top_level_dirs"] + 0.5 * v["depth"], prose=v["doc_ratio"], debt=v["debt"],
    )
    if features.history.commit_count == 0:
        values.update(age=0.0, alive=0.0, crowd=0.0)
    return Traits(scale=normalized.scale, table_version=normalized.table_version,
                  reference_time=normalized.reference_time, **{name: round(x, 6) for name, x in values.items()})
