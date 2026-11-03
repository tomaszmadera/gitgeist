"""Tests for live renderers (palette, dynamics, abstract, character, HTML, facade)."""

import colorsys
import hashlib
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from gitgeist.schemas.visual_latent import (
    MaterialityDistribution,
    VisualLatentAxes,
    VisualLatentProfile,
)
from gitgeist.schemas.identity import IdentitySeed
from gitgeist.schemas.live_state import LiveSimulationState, OrbitsScene
from gitgeist.render.palette import generate_palette
from gitgeist.render.dynamics import generate_dynamics
from gitgeist.render.character_renderer import generate_character_simulation
from gitgeist.render.html_template import generate_live_html
from gitgeist.render.facade import LiveRenderArtifacts, render_live
from tests.orbits_helpers import make_scene

# Fixed identity: sha256("sample-root").
SAMPLE_IDENTITY = IdentitySeed(
    identity_seed=hashlib.sha256(b"sample-root").hexdigest(),
    source="root-commits",
    root_commits=["sample-root"],
)


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


def test_generate_character_simulation(sample_profile: VisualLatentProfile):
    state = generate_character_simulation(
        sample_profile, repository_name="repo2", identity_seed=SAMPLE_IDENTITY.identity_seed
    )
    assert state.representation_mode == "character"
    assert state.repository_name == "repo2"
    assert isinstance(state, LiveSimulationState)
    assert state.geometry.organic_ratio == pytest.approx(1.0 - sample_profile.axes.biological_vs_mechanical)


def test_generate_live_html(sample_profile: VisualLatentProfile):
    state = generate_character_simulation(
        sample_profile, repository_name="gitgeist-test", identity_seed=SAMPLE_IDENTITY.identity_seed
    )
    html = generate_live_html(state)
    assert "<!DOCTYPE html>" in html
    assert "<canvas" in html
    assert "gitgeist-test" in html
    assert "requestAnimationFrame" in html
    assert "http://" not in html
    assert "https://" not in html  # zero-external dependencies
    assert "drawAbstract" not in html and "symStep" not in html  # the rotated-copy abstract path is gone


def test_generate_live_html_rejects_abstract_state(sample_profile: VisualLatentProfile):
    state = generate_character_simulation(
        sample_profile, repository_name="x", identity_seed=SAMPLE_IDENTITY.identity_seed
    ).model_copy(update={"representation_mode": "abstract"})
    with pytest.raises(ValueError, match="orbits"):
        generate_live_html(state)
    with pytest.raises(TypeError, match="LiveSimulationState"):
        generate_live_html("state")  # type: ignore[arg-type]


def test_render_live_facade_abstract(sample_profile: VisualLatentProfile):
    scene = make_scene()
    artifacts = render_live(sample_profile, mode="abstract", identity=SAMPLE_IDENTITY, scene=scene)
    assert isinstance(artifacts, LiveRenderArtifacts)
    assert artifacts.state == scene
    assert "<!DOCTYPE html>" in artifacts.html_content
    assert OrbitsScene.model_validate_json(artifacts.state_json) == scene


def test_render_live_abstract_without_scene_raises(sample_profile: VisualLatentProfile):
    with pytest.raises(TypeError, match="OrbitsScene"):
        render_live(sample_profile, mode="abstract", identity=SAMPLE_IDENTITY)
    with pytest.raises(TypeError, match="OrbitsScene"):
        render_live(sample_profile, identity=SAMPLE_IDENTITY, scene="scene")  # type: ignore[arg-type]


def test_render_live_character_with_scene_raises(sample_profile: VisualLatentProfile):
    with pytest.raises(ValueError, match="scene"):
        render_live(sample_profile, mode="character", identity=SAMPLE_IDENTITY, scene=make_scene())


def test_render_live_abstract_is_byte_identical_on_two_runs(sample_profile: VisualLatentProfile, tmp_path: Path):
    first = render_live(sample_profile, identity=SAMPLE_IDENTITY, scene=make_scene(), output_dir=tmp_path / "a")
    second = render_live(sample_profile, identity=SAMPLE_IDENTITY, scene=make_scene(), output_dir=tmp_path / "b")
    for name in ("live-preview.html", "live-state.json", "identity-seed.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    assert first.html_content == second.html_content and first.state_json == second.state_json


def test_old_abstract_renderer_is_removed():
    import importlib

    import gitgeist.render

    assert not hasattr(gitgeist.render, "generate_abstract_simulation")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("gitgeist.render.abstract_renderer")


def test_render_live_facade_character(sample_profile: VisualLatentProfile):
    artifacts = render_live(
        sample_profile, mode="character", repository_name="gitgeist-character", identity=SAMPLE_IDENTITY
    )
    assert isinstance(artifacts, LiveRenderArtifacts)
    assert artifacts.state.representation_mode == "character"
    assert "<!DOCTYPE html>" in artifacts.html_content
    parsed_json = json.loads(artifacts.state_json)
    assert parsed_json["representation_mode"] == "character"


def test_render_live_save_to_disk(sample_profile: VisualLatentProfile, tmp_path: Path):
    out_dir = tmp_path / "renders" / "run_1"
    artifacts = render_live(
        sample_profile, mode="abstract", output_dir=out_dir, identity=SAMPLE_IDENTITY, scene=make_scene()
    )

    assert artifacts.html_path is not None
    assert artifacts.json_path is not None
    assert artifacts.html_path.exists()
    assert artifacts.json_path.exists()
    assert artifacts.html_path.name == "live-preview.html"
    assert artifacts.json_path.name == "live-state.json"
    assert artifacts.html_path.read_text(encoding="utf-8") == artifacts.html_content


def test_render_live_invalid_mode(sample_profile: VisualLatentProfile):
    with pytest.raises(ValueError, match="Unsupported representation mode"):
        render_live(sample_profile, mode="unsupported", identity=SAMPLE_IDENTITY)  # type: ignore[arg-type]


def test_render_live_invalid_profile():
    with pytest.raises(TypeError, match="Expected VisualLatentProfile"):
        render_live("not-a-profile", identity=SAMPLE_IDENTITY)  # type: ignore[arg-type]


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
    state_a = generate_character_simulation(sample_profile, identity_seed=SAMPLE_IDENTITY.identity_seed)
    state_b = generate_character_simulation(shifted, identity_seed=SAMPLE_IDENTITY.identity_seed)
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
    artifacts = render_live(profile, mode="character", repository_name="extreme", identity=SAMPLE_IDENTITY)
    assert "<!DOCTYPE html>" in artifacts.html_content
    assert "NaN" not in artifacts.html_content
    assert artifacts.state.palette.aura.startswith("rgba(")


def test_generate_live_html_escapes_repository_name(sample_profile: VisualLatentProfile):
    state = generate_character_simulation(
        sample_profile,
        repository_name='"><script>alert(1)</script>',
        identity_seed=SAMPLE_IDENTITY.identity_seed,
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


def test_render_live_requires_identity_seed_model(sample_profile: VisualLatentProfile):
    with pytest.raises(TypeError, match="Expected IdentitySeed"):
        render_live(sample_profile, identity="not-an-identity")  # type: ignore[arg-type]


def test_render_live_writes_identity_seed_json(sample_profile: VisualLatentProfile, tmp_path: Path):
    artifacts = render_live(sample_profile, output_dir=tmp_path, identity=SAMPLE_IDENTITY, scene=make_scene())

    assert artifacts.identity_seed_path == tmp_path / "identity-seed.json"
    written = IdentitySeed.model_validate_json(artifacts.identity_seed_path.read_text(encoding="utf-8"))
    assert written == SAMPLE_IDENTITY


GOLDEN_LIVE = Path(__file__).parent / "golden" / "live"


def _without_abstract_code(page: str) -> str:
    """The 0.9.0 character page minus the abstract code path that 0.10.0 removed (and nothing else)."""
    start = page.index("      function drawAbstract(t) {")
    end = page.index("      function drawCharacter(t) {")
    page = page[:start] + page[end:]
    dispatch = (
        "        if (mode === 'character') {\n          drawCharacter(elapsed);\n"
        "        } else {\n          drawAbstract(elapsed);\n        }\n"
    )
    assert dispatch in page
    return page.replace(dispatch, "        drawCharacter(elapsed);\n")


def test_character_live_output_matches_the_0_9_0_snapshot(sample_profile: VisualLatentProfile):
    """Business rule 5: the character state is byte-identical to 0.9.0 and the page differs only
    by the removed abstract code path (engine version masked in both)."""
    from gitgeist._version import current_engine_version

    artifacts = render_live(
        sample_profile, mode="character", repository_name="golden-character", identity=SAMPLE_IDENTITY
    )
    version = current_engine_version()
    snapshot_page = (GOLDEN_LIVE / "character-0.9.0-live-preview.html").read_text(encoding="utf-8")
    assert artifacts.html_content.replace(version, "<ENGINE_VERSION>") == _without_abstract_code(snapshot_page)
    assert artifacts.state_json.replace(version, "<ENGINE_VERSION>") == (
        GOLDEN_LIVE / "character-0.9.0-live-state.json"
    ).read_text(encoding="utf-8")
