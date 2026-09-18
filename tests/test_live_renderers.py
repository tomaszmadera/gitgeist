"""Tests for live renderers (palette, dynamics, abstract, character, HTML, facade)."""

import colorsys
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from gitgeist.schemas.visual_latent import (
    MaterialityDistribution,
    VisualLatentAxes,
    VisualLatentProfile,
)
from gitgeist.schemas.live_state import LiveSimulationState
from gitgeist.render.palette import generate_palette
from gitgeist.render.dynamics import generate_dynamics
from gitgeist.render.abstract_renderer import generate_abstract_simulation
from gitgeist.render.character_renderer import generate_character_simulation
from gitgeist.render.html_template import generate_live_html
from gitgeist.render.facade import LiveRenderArtifacts, render_live


@pytest.fixture
def sample_profile() -> VisualLatentProfile:
    axes = VisualLatentAxes(
        form_complexity=0.7,
        symmetry=0.6,
        fragmentation=0.3,
        tension_curvature=0.4,
        texture_density=0.5,
        luminosity=0.6,
        contrast=0.7,
        sharpness=0.8,
        visual_rhythm=0.75,
        compositional_balance=0.8,
        biological_vs_mechanical=0.7,
        ornamental_load=0.2,
        opacity=0.85,
        layering=0.6,
    )
    materiality = MaterialityDistribution(
        weights={"organic": 0.1, "mechanical": 0.6, "crystalline": 0.2, "ethereal": 0.1},
        dominant="mechanical",
    )
    return VisualLatentProfile(
        axes=axes,
        materiality=materiality,
        dominant_features=["sharpness", "compositional_balance"],
    )


def test_generate_palette_determinism(sample_profile: VisualLatentProfile):
    palette1 = generate_palette(sample_profile)
    palette2 = generate_palette(sample_profile)
    assert palette1 == palette2
    assert palette1.background.startswith("#")
    assert palette1.primary.startswith("#")


def test_generate_palette_luminosity_impact(sample_profile: VisualLatentProfile):
    dark_axes = sample_profile.axes.model_copy(update={"luminosity": 0.1})
    dark_profile = sample_profile.model_copy(update={"axes": dark_axes})

    bright_axes = sample_profile.axes.model_copy(update={"luminosity": 0.9})
    bright_profile = sample_profile.model_copy(update={"axes": bright_axes})

    dark_pal = generate_palette(dark_profile)
    bright_pal = generate_palette(bright_profile)

    assert dark_pal.background != bright_pal.background


def test_generate_dynamics_determinism(sample_profile: VisualLatentProfile):
    dyn1 = generate_dynamics(sample_profile)
    dyn2 = generate_dynamics(sample_profile)
    assert dyn1 == dyn2
    assert dyn1.pulse_frequency > 0
    assert dyn1.flow_speed > 0


def test_generate_dynamics_rhythm_impact(sample_profile: VisualLatentProfile):
    calm_axes = sample_profile.axes.model_copy(update={"visual_rhythm": 0.1})
    calm_profile = sample_profile.model_copy(update={"axes": calm_axes})

    intense_axes = sample_profile.axes.model_copy(update={"visual_rhythm": 0.9})
    intense_profile = sample_profile.model_copy(update={"axes": intense_axes})

    calm_dyn = generate_dynamics(calm_profile)
    intense_dyn = generate_dynamics(intense_profile)

    assert intense_dyn.pulse_frequency > calm_dyn.pulse_frequency


def test_generate_abstract_simulation(sample_profile: VisualLatentProfile):
    state = generate_abstract_simulation(sample_profile, repository_name="repo1")
    assert state.representation_mode == "abstract"
    assert state.repository_name == "repo1"
    assert isinstance(state, LiveSimulationState)
    assert state.geometry.fragmentation == pytest.approx(sample_profile.axes.fragmentation)


def test_generate_character_simulation(sample_profile: VisualLatentProfile):
    state = generate_character_simulation(sample_profile, repository_name="repo2")
    assert state.representation_mode == "character"
    assert state.repository_name == "repo2"
    assert isinstance(state, LiveSimulationState)
    assert state.geometry.organic_ratio == pytest.approx(1.0 - sample_profile.axes.biological_vs_mechanical)


def test_generate_live_html(sample_profile: VisualLatentProfile):
    state = generate_abstract_simulation(sample_profile, repository_name="gitgeist-test")
    html = generate_live_html(state)
    assert "<!DOCTYPE html>" in html
    assert "<canvas" in html
    assert "gitgeist-test" in html
    assert "requestAnimationFrame" in html
    assert "http://" not in html
    assert "https://" not in html  # zero-external dependencies


def test_render_live_facade_abstract(sample_profile: VisualLatentProfile):
    artifacts = render_live(sample_profile, mode="abstract", repository_name="gitgeist-abstract")
    assert isinstance(artifacts, LiveRenderArtifacts)
    assert artifacts.state.representation_mode == "abstract"
    assert "<!DOCTYPE html>" in artifacts.html_content
    parsed_json = json.loads(artifacts.state_json)
    assert parsed_json["representation_mode"] == "abstract"


def test_render_live_facade_character(sample_profile: VisualLatentProfile):
    artifacts = render_live(sample_profile, mode="character", repository_name="gitgeist-character")
    assert isinstance(artifacts, LiveRenderArtifacts)
    assert artifacts.state.representation_mode == "character"
    assert "<!DOCTYPE html>" in artifacts.html_content
    parsed_json = json.loads(artifacts.state_json)
    assert parsed_json["representation_mode"] == "character"


def test_render_live_save_to_disk(sample_profile: VisualLatentProfile, tmp_path: Path):
    out_dir = tmp_path / "renders" / "run_1"
    artifacts = render_live(sample_profile, mode="abstract", output_dir=out_dir)

    assert artifacts.html_path is not None
    assert artifacts.json_path is not None
    assert artifacts.html_path.exists()
    assert artifacts.json_path.exists()
    assert artifacts.html_path.name == "live-preview.html"
    assert artifacts.json_path.name == "live-state.json"
    assert artifacts.html_path.read_text(encoding="utf-8") == artifacts.html_content


def test_render_live_invalid_mode(sample_profile: VisualLatentProfile):
    with pytest.raises(ValueError, match="Unsupported representation mode"):
        render_live(sample_profile, mode="unsupported")  # type: ignore[arg-type]


def test_render_live_invalid_profile():
    with pytest.raises(TypeError, match="Expected VisualLatentProfile"):
        render_live("not-a-profile")  # type: ignore[arg-type]


def _hex_hue(hex_color: str) -> float:
    r = int(hex_color[1:3], 16) / 255.0
    g = int(hex_color[3:5], 16) / 255.0
    b = int(hex_color[5:7], 16) / 255.0
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    return h


def _aura_alpha(rgba_color: str) -> float:
    return float(rgba_color.rsplit(", ", 1)[1].rstrip(")"))


def _profile_with_materiality(axes: VisualLatentAxes, dominant: str) -> VisualLatentProfile:
    weights = {"organic": 0.1, "mechanical": 0.1, "crystalline": 0.1, "ethereal": 0.1}
    weights[dominant] = 0.7
    materiality = MaterialityDistribution(weights=weights, dominant=dominant)
    return VisualLatentProfile(
        axes=axes,
        materiality=materiality,
        dominant_features=["sharpness"],
    )


@pytest.fixture
def sample_profile_axes_low_tension() -> VisualLatentAxes:
    return VisualLatentAxes(
        form_complexity=0.7,
        symmetry=0.6,
        fragmentation=0.3,
        tension_curvature=0.2,
        texture_density=0.5,
        luminosity=0.3,
        contrast=0.6,
        sharpness=0.8,
        visual_rhythm=0.75,
        compositional_balance=0.8,
        biological_vs_mechanical=0.7,
        ornamental_load=0.2,
        opacity=0.85,
        layering=0.6,
    )


def test_generate_palette_accent_materiality(sample_profile_axes_low_tension: VisualLatentAxes):
    crystalline = generate_palette(_profile_with_materiality(sample_profile_axes_low_tension, "crystalline"))
    organic = generate_palette(_profile_with_materiality(sample_profile_axes_low_tension, "organic"))

    crystalline_hue = _hex_hue(crystalline.accent)
    organic_hue = _hex_hue(organic.accent)

    assert 0.45 <= crystalline_hue <= 0.70
    assert organic_hue < 0.16 or organic_hue > 0.95
    assert crystalline.accent != organic.accent


def test_generate_palette_ethereal_increases_aura_transparency(
    sample_profile_axes_low_tension: VisualLatentAxes,
):
    ethereal = generate_palette(_profile_with_materiality(sample_profile_axes_low_tension, "ethereal"))
    mechanical = generate_palette(_profile_with_materiality(sample_profile_axes_low_tension, "mechanical"))

    assert _aura_alpha(ethereal.aura) < _aura_alpha(mechanical.aura)


def test_seed_ignores_calculated_at(sample_profile: VisualLatentProfile):
    shifted = sample_profile.model_copy(
        update={"calculated_at": sample_profile.calculated_at.replace(hour=1, minute=2)}
    )
    for generator in (generate_abstract_simulation, generate_character_simulation):
        state_a = generator(sample_profile)
        state_b = generator(shifted)
        assert state_a.seed == state_b.seed


@pytest.mark.parametrize("extreme", [0.0, 1.0])
def test_render_live_extreme_axis_values(extreme: float):
    axes = VisualLatentAxes(**{f: extreme for f in VisualLatentAxes.model_fields})
    profile = VisualLatentProfile(
        axes=axes,
        materiality=MaterialityDistribution(
            weights={"organic": 0.25, "mechanical": 0.25, "crystalline": 0.25, "ethereal": 0.25},
            dominant="organic",
        ),
        dominant_features=["sharpness"],
    )
    for mode in ("abstract", "character"):
        artifacts = render_live(profile, mode=mode, repository_name="extreme")
        assert "<!DOCTYPE html>" in artifacts.html_content
        assert "NaN" not in artifacts.html_content
        assert artifacts.state.palette.aura.startswith("rgba(")


def test_generate_live_html_escapes_repository_name(sample_profile: VisualLatentProfile):
    state = generate_abstract_simulation(
        sample_profile, repository_name='"><script>alert(1)</script>'
    )
    html = generate_live_html(state)

    # The raw name must not survive unescaped in markup...
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    # ...and the JSON payload must not be able to terminate its own script tag.
    assert html.count("</script>") == 2

    marker = '<script id="gitgeist-state" type="application/json">'
    start = html.index(marker) + len(marker)
    end = html.index("</script>", start)
    embedded = html[start:end]
    parsed = json.loads(embedded)
    assert parsed["repository_name"] == '"><script>alert(1)</script>'
