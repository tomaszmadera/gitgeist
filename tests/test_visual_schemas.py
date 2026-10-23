"""Validation contracts for the renderer-neutral portrait schemas."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from gitgeist.schemas.traits import TRAIT_NAMES, Traits
from gitgeist.schemas.visual_spec import Cracks, Footprint, SeedInfo, Strands

REF = datetime(2026, 4, 16, tzinfo=timezone.utc)


def traits_data() -> dict:
    return dict(scale="absolute", table_version=None, reference_time=REF,
                **dict.fromkeys(TRAIT_NAMES, 0.5))


def test_traits_roundtrip_and_frozen() -> None:
    traits = Traits(**traits_data())
    assert Traits.model_validate_json(traits.model_dump_json()) == traits
    with pytest.raises(ValidationError):
        traits.size = 0.2


@pytest.mark.parametrize("name", TRAIT_NAMES)
@pytest.mark.parametrize("value", [-0.01, 1.01, float("nan"), float("inf")])
def test_traits_reject_outside_range(name: str, value: float) -> None:
    with pytest.raises(ValidationError):
        Traits(**(traits_data() | {name: value}))


def test_traits_reject_extra_and_naive_time() -> None:
    with pytest.raises(ValidationError):
        Traits(**traits_data(), surprise=True)
    with pytest.raises(ValidationError):
        Traits(**(traits_data() | {"reference_time": datetime(2026, 4, 16)}))


@pytest.mark.parametrize("model,data", [
    (Footprint, {"coverage": 0.2, "element_count": 40}),
    (SeedInfo, dict(identity_seed="bad", user_seed=None, style_seed=0, effective_seed=0)),
    (Strands, {"count": 2, "paths": []}),
    (Cracks, {"count": 1, "marks": []}),
])
def test_scene_parts_reject_invalid_values(model: type, data: dict) -> None:
    with pytest.raises(ValidationError):
        model(**data)
