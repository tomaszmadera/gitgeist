"""Tests for the VisualSpec prompt composer."""

from pathlib import Path

import pytest

from gitgeist.render.prompt_composer import compose_prompt
from gitgeist.schemas.traits import TRAIT_NAMES
from gitgeist.schemas.visual_spec import VisualSpec

FIXTURE = Path(__file__).parent / "golden" / "visual_spec" / "single-script-abstract.json"
WORKED = """\
An abstract composition of one large body, centered, on a dark ground.
- The form covers 25% of the frame and contains 40 small marks.
- One strand crosses the form.
- A bright knot sits on body 1.
- Frayed edges, blur 6.0 px, jitter 0.25.
- One body with no nested shapes.
- Fine hatching covers 0% of each body.
- No cracks.
Palette: #2abb4c on #121218.
Medium: cut paper.
No text, no letters, no logos, no code, no screens, no mascots.
No watermarks and no captions inside the picture.
"""


def load_spec() -> VisualSpec:
    return VisualSpec.model_validate_json(FIXTURE.read_text(encoding="utf-8"))


def test_worked_fixture_prompt_is_exact() -> None:
    prompt = compose_prompt(load_spec())
    assert prompt == WORKED
    assert prompt.endswith("\n")
    assert not prompt.endswith("\n\n")
    assert "\n\n" not in prompt
    assert all(line.strip() == line and line for line in prompt.splitlines())


def test_include_name_inserts_only_the_repository_line() -> None:
    prompt = compose_prompt(load_spec(), include_name=True, repository_name="sample")
    lines = prompt.splitlines()
    assert lines[1] == "Repository: sample."
    bare = WORKED.splitlines()
    assert lines[0] == bare[0]
    assert lines[2:] == bare[1:]


def test_worked_prompt_hides_paths_names_and_trait_numbers() -> None:
    prompt = compose_prompt(load_spec())
    assert "run.sh" not in prompt
    assert "Shell" not in prompt
    assert "0.704486" not in prompt
    assert "sample" not in prompt


def test_same_spec_is_deterministic() -> None:
    spec = load_spec()
    assert compose_prompt(spec) == compose_prompt(spec)


def test_tie_drops_the_later_trait_name() -> None:
    spec = load_spec()
    traits = spec.traits.model_copy(update={name: 0.0 for name in TRAIT_NAMES})
    prompt = compose_prompt(spec.model_copy(update={"traits": traits, "knot": None}))
    directives = [line for line in prompt.splitlines() if line.startswith("- ")]
    assert len(directives) == 7
    assert "No cracks." not in prompt
    assert "Fine hatching" not in prompt
    assert "One growth ring." in prompt


def test_fewer_than_five_extremes_fills_the_farthest() -> None:
    spec = load_spec()
    traits = spec.traits.model_copy(
        update={name: 0.5 for name in TRAIT_NAMES} | {"size": 0.0, "age": 0.1}
    )
    prompt = compose_prompt(spec.model_copy(update={"traits": traits}))
    directives = [line for line in prompt.splitlines() if line.startswith("- ")]
    assert len(directives) == 5
    assert directives[0].startswith("- The form covers ")
    assert "growth ring" in directives[1]
    assert directives[2].startswith("- Vivid, moving at ")


def test_unknown_style_names_the_style() -> None:
    spec = load_spec().model_copy(update={"style": "auto"})
    with pytest.raises(ValueError, match="auto"):
        compose_prompt(spec)


def test_empty_creature_sentence() -> None:
    spec = load_spec().model_copy(update={"style": "creature", "masses": [], "knot": None})
    assert compose_prompt(spec).startswith(
        "A creature with no bodies, centered, on a dark ground.\n"
    )


def test_placement_uses_both_axes() -> None:
    spec = load_spec()
    mass = spec.masses[0].model_copy(update={"x": 0.5, "y": -0.5})
    prompt = compose_prompt(spec.model_copy(update={"masses": [mass]}))
    assert "off-center to the right and toward the top" in prompt


def test_grey_palette_and_duplicate_hex() -> None:
    spec = load_spec()
    grey = spec.masses[0].model_copy(update={"hue": None})
    prompt = compose_prompt(spec.model_copy(update={"masses": [grey, grey]}))
    assert "Palette: #737373 on #121218." in prompt


def test_missing_name_and_wrong_type() -> None:
    spec = load_spec()
    with pytest.raises(ValueError):
        compose_prompt(spec, include_name=True, repository_name=None)
    with pytest.raises(ValueError):
        compose_prompt(spec, include_name=True, repository_name="")
    with pytest.raises(TypeError):
        compose_prompt(object())
