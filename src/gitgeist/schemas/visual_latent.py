"""Pydantic schemas for visual latent parameters and profile."""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, model_validator


class VisualLatentAxes(BaseModel):
    """Normalized continuous visual latent axes in range [0.0, 1.0]."""

    model_config = ConfigDict(frozen=True)

    form_complexity: float = Field(..., ge=0.0, le=1.0)
    symmetry: float = Field(..., ge=0.0, le=1.0)
    fragmentation: float = Field(..., ge=0.0, le=1.0)
    tension_curvature: float = Field(..., ge=0.0, le=1.0)
    texture_density: float = Field(..., ge=0.0, le=1.0)
    luminosity: float = Field(..., ge=0.0, le=1.0)
    contrast: float = Field(..., ge=0.0, le=1.0)
    sharpness: float = Field(..., ge=0.0, le=1.0)
    visual_rhythm: float = Field(..., ge=0.0, le=1.0)
    compositional_balance: float = Field(..., ge=0.0, le=1.0)
    biological_vs_mechanical: float = Field(..., ge=0.0, le=1.0)
    ornamental_load: float = Field(..., ge=0.0, le=1.0)
    opacity: float = Field(..., ge=0.0, le=1.0)
    layering: float = Field(..., ge=0.0, le=1.0)


class MaterialityDistribution(BaseModel):
    """Categorical distribution of material tendencies with normalized weights and dominant."""

    model_config = ConfigDict(frozen=True)

    weights: dict[str, float]
    dominant: str

    @model_validator(mode="after")
    def validate_dominant_and_weights(self) -> MaterialityDistribution:
        if not self.weights:
            raise ValueError("weights dictionary cannot be empty")
        for k, w in self.weights.items():
            if not (0.0 <= w <= 1.0):
                raise ValueError(f"weight for '{k}' ({w}) must be between 0.0 and 1.0")
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 1e-4:
            raise ValueError(f"weights must sum to 1.0 within 1e-4 tolerance, got {total_weight}")
        if self.dominant not in self.weights:
            raise ValueError(f"dominant choice '{self.dominant}' must be present in weights")
        max_weight = max(self.weights.values())
        if abs(self.weights[self.dominant] - max_weight) > 1e-5:
            raise ValueError(
                f"dominant '{self.dominant}' (weight={self.weights[self.dominant]}) "
                f"does not match max weight {max_weight}"
            )
        return self


class VisualLatentProfile(BaseModel):
    """Aggregated visual latent profile (Layer 3 in Gitgeist architecture)."""

    model_config = ConfigDict(frozen=True)

    axes: VisualLatentAxes
    materiality: MaterialityDistribution
    dominant_features: list[str] = Field(default_factory=list)
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_commit: str | None = None
    engine_version: str = "0.1.0-beta.2"
