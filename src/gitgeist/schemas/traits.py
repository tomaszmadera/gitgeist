"""Portrait trait schema."""

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Unit = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]

TRAIT_NAMES = ("size", "age", "alive", "crowd", "focus", "care", "sprawl", "prose", "debt")


class Traits(BaseModel):
    """Nine normalized portrait channels and their scaling context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scale: Literal["absolute", "corpus"]
    table_version: str | None
    reference_time: datetime
    size: Unit
    age: Unit
    alive: Unit
    crowd: Unit
    focus: Unit
    care: Unit
    sprawl: Unit
    prose: Unit
    debt: Unit

    @field_validator("reference_time")
    @classmethod
    def utc_reference(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("reference_time must be timezone-aware")
        return value.astimezone(timezone.utc)
