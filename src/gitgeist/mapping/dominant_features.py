"""Extractor for dominant visual features."""

from __future__ import annotations

from gitgeist.schemas.visual_latent import VisualLatentAxes


def extract_dominant_features(axes: VisualLatentAxes, top_n: int = 3) -> list[str]:
    """Select the most salient visual axes based on deviation from neutral midpoint (0.5)."""
    candidates = []
    for field_name in VisualLatentAxes.model_fields:
        val = getattr(axes, field_name)
        distance = round(abs(val - 0.5), 4)
        clean_name = field_name.replace("_", " ")
        prefix = "high" if val >= 0.5 else "low"
        label = f"{prefix} {clean_name}"
        candidates.append((distance, label))

    # Sort by deviation descending, breaking ties deterministically by label name
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [label for _, label in candidates[:max(0, top_n)]]
