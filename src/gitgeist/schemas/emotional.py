"""Pydantic schemas for emotional state and semantic sensors."""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, model_validator

from gitgeist._version import current_engine_version


class EmotionalScores(BaseModel):
    """Continuous emotional and semantic metrics in range [0.0, 1.0]."""

    model_config = ConfigDict(frozen=True)

    coherence: float = Field(..., ge=0.0, le=1.0)
    maturity: float = Field(..., ge=0.0, le=1.0)
    volatility: float = Field(..., ge=0.0, le=1.0)
    fragility: float = Field(..., ge=0.0, le=1.0)
    novelty: float = Field(..., ge=0.0, le=1.0)
    discipline: float = Field(..., ge=0.0, le=1.0)
    tension: float = Field(..., ge=0.0, le=1.0)
    chaos: float = Field(..., ge=0.0, le=1.0)
    identity_strength: float = Field(..., ge=0.0, le=1.0)
    internal_conflict: float = Field(..., ge=0.0, le=1.0)


class EmotionalNouls(BaseModel):
    """Binary qualifier flags (semantic nouls)."""

    model_config = ConfigDict(frozen=True)

    appears_experimental: bool = False
    feels_stable: bool = False
    feels_overloaded: bool = False
    feels_under_control: bool = False
    feels_fragmented: bool = False
    feels_unfinished: bool = False
    feels_resilient: bool = False


class ChoiceDistribution(BaseModel):
    """Categorical choice distribution with normalized weights and dominant choice."""

    model_config = ConfigDict(frozen=True)

    weights: dict[str, float]
    dominant: str

    @model_validator(mode="after")
    def validate_dominant_and_weights(self) -> ChoiceDistribution:
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


class EmotionalChoices(BaseModel):
    """Categorical dimensions and temperament profiles."""

    model_config = ConfigDict(frozen=True)

    temperament: ChoiceDistribution
    visual_tone: ChoiceDistribution
    energy_profile: ChoiceDistribution


class EmotionalState(BaseModel):
    """Aggregated explicit emotional state profile (Layer 2 in Gitgeist architecture)."""

    model_config = ConfigDict(frozen=True)

    scores: EmotionalScores
    nouls: EmotionalNouls
    choices: EmotionalChoices
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_commit: str | None = None
    engine_version: str = Field(default_factory=current_engine_version)
