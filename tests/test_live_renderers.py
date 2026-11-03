"""Tests for the live facade: ``render_live(scene, ...)`` for both scenes, and the removed pre-0.10 code."""

import hashlib
import importlib
import json
from pathlib import Path

import pytest

from gitgeist.render.facade import LiveRenderArtifacts, render_live
from gitgeist.schemas.identity import IdentitySeed
from gitgeist.schemas.live_state import CreatureScene, OrbitsScene
from tests.creature_helpers import make_creature_scene
from tests.orbits_helpers import make_scene

# Fixed identity: sha256("sample-root").
SAMPLE_IDENTITY = IdentitySeed(
    identity_seed=hashlib.sha256(b"sample-root").hexdigest(),
    source="root-commits",
    root_commits=["sample-root"],
)

SCENES = {"abstract": (make_scene, OrbitsScene), "character": (make_creature_scene, CreatureScene)}


@pytest.mark.parametrize("representation", ["abstract", "character"])
def test_render_live_facade_renders_the_scene(representation: str):
    build, model = SCENES[representation]
    scene = build()
    artifacts = render_live(scene, identity=SAMPLE_IDENTITY)
    assert isinstance(artifacts, LiveRenderArtifacts)
    assert artifacts.state == scene
    assert "<!DOCTYPE html>" in artifacts.html_content
    assert model.model_validate_json(artifacts.state_json) == scene
    assert artifacts.html_path is None and artifacts.json_path is None and artifacts.identity_seed_path is None


@pytest.mark.parametrize("representation", ["abstract", "character"])
def test_render_live_is_byte_identical_on_two_runs(representation: str, tmp_path: Path):
    build, _ = SCENES[representation]
    first = render_live(build(), tmp_path / "a", identity=SAMPLE_IDENTITY)
    second = render_live(build(), tmp_path / "b", identity=SAMPLE_IDENTITY)
    for name in ("live-preview.html", "live-state.json", "identity-seed.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    assert first.html_content == second.html_content and first.state_json == second.state_json


@pytest.mark.parametrize("representation", ["abstract", "character"])
def test_render_live_save_to_disk(representation: str, tmp_path: Path):
    build, _ = SCENES[representation]
    out_dir = tmp_path / "renders" / "run_1"
    artifacts = render_live(build(), output_dir=out_dir, identity=SAMPLE_IDENTITY)

    assert artifacts.html_path == out_dir / "live-preview.html"
    assert artifacts.json_path == out_dir / "live-state.json"
    assert artifacts.identity_seed_path == out_dir / "identity-seed.json"
    assert artifacts.html_path.read_text(encoding="utf-8") == artifacts.html_content
    assert artifacts.json_path.read_text(encoding="utf-8") == artifacts.state_json
    written = IdentitySeed.model_validate_json(artifacts.identity_seed_path.read_text(encoding="utf-8"))
    assert written == SAMPLE_IDENTITY


@pytest.mark.parametrize("bad", [None, "scene", {"a": 1}])
def test_render_live_requires_a_scene(bad):
    with pytest.raises(TypeError, match="OrbitsScene or CreatureScene"):
        render_live(bad, identity=SAMPLE_IDENTITY)


def test_render_live_requires_identity_seed_model():
    with pytest.raises(TypeError, match="Expected IdentitySeed"):
        render_live(make_creature_scene(), identity="not-an-identity")  # type: ignore[arg-type]


def test_render_live_no_longer_takes_a_profile_or_mode():
    with pytest.raises(TypeError):
        render_live(make_scene(), mode="abstract", identity=SAMPLE_IDENTITY)  # type: ignore[call-arg]


def test_creature_page_escapes_the_repository_name():
    scene = make_creature_scene(name='"><script>alert(1)</script>')
    html = render_live(scene, identity=SAMPLE_IDENTITY).html_content

    # The raw name must not survive unescaped in markup, and the JSON payload must not close its own script tag.
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert html.count("</script>") == 2
    marker = '<script id="gitgeist-state" type="application/json">'
    start = html.index(marker) + len(marker)
    embedded = html[start:html.index("</script>", start)]
    assert json.loads(embedded)["repository_name"] == '"><script>alert(1)</script>'


def test_old_live_code_is_removed():
    import gitgeist
    import gitgeist.render
    import gitgeist.schemas
    import gitgeist.schemas.live_state as live_state

    for module in ("abstract_renderer", "character_renderer", "dynamics", "palette"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(f"gitgeist.render.{module}")
    for owner in (gitgeist, gitgeist.render, gitgeist.schemas):
        for name in ("generate_abstract_simulation", "generate_character_simulation", "generate_live_html",
                     "generate_palette", "generate_dynamics", "LiveSimulationState"):
            assert not hasattr(owner, name), (owner.__name__, name)
    for name in ("LiveSimulationState", "ColorPalette", "MotionDynamics", "GeometryParameters"):
        assert not hasattr(live_state, name)
