"""Tests for the self-contained character creature page (stage 5 spec: business rules 2, 3, 6, criteria 1 and 6)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from gitgeist.render.creature import build_creature_scene
from gitgeist.render.html_template import generate_creature_html
from gitgeist.schemas.features import Hotspot
from gitgeist.schemas.live_state import CreatureScene
from tests.creature_helpers import CORPUS_LIKE, make_character_spec, make_creature_scene, make_features, mass_table, with_masses

STATE_MARKER = '<script id="gitgeist-state" type="application/json">'
HOSTILE = '"><script>alert(1)</script>'


def _embedded_json(page: str) -> str:
    start = page.index(STATE_MARKER) + len(STATE_MARKER)
    return page[start : page.index("</script>", start)]


def _code(page: str) -> str:
    start = page.index("<script>", page.index(STATE_MARKER)) + len("<script>")
    return page[start : page.index("</script>", start)]


def test_embedded_json_parses_back_to_the_scene() -> None:
    scene = make_creature_scene()
    page = generate_creature_html(scene)
    assert CreatureScene.model_validate_json(_embedded_json(page)) == scene
    assert json.loads(_embedded_json(page)) == json.loads(scene.model_dump_json())


@pytest.mark.parametrize("caption", [True, False])
def test_page_is_self_contained(caption: bool) -> None:
    page = generate_creature_html(make_creature_scene(caption=caption))
    assert re.findall(r"""(?:src|href)\s*=""", page) == []
    assert "url(" not in page and "@import" not in page and "<link" not in page
    for forbidden in ("http:", "https:", "//"):
        assert forbidden not in page
    assert "<canvas" in page and "requestAnimationFrame" in page


def test_hostile_names_are_escaped() -> None:
    features = make_features(hotspots=[Hotspot(path='src/<b>"x"</script>.py', change_count=9, mass="src")])
    scene = build_creature_scene(features, make_character_spec(features), repository_name=HOSTILE)
    page = generate_creature_html(scene)

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert page.count("</script>") == 2  # the state payload and the code; the JSON cannot end its own tag early
    assert json.loads(_embedded_json(page))["repository_name"] == HOSTILE
    outside = page.replace(_embedded_json(page), "")
    assert "<b>" not in outside and "alert(1)</script>" not in outside


def test_hud_shows_name_and_three_conclusions_only() -> None:
    scene = make_creature_scene()
    page = generate_creature_html(scene)
    hud = page[page.index('<div id="hud">') : page.index('<div id="hover">')]
    assert "creature-demo" in hud
    assert re.findall(r"<li>(.*?)</li>", hud) == scene.conclusions
    for removed in ("Material", "Seed", "Engine", "Mode"):
        assert removed not in hud


def test_caption_off_has_no_hud_or_hover_and_draws_the_same() -> None:
    quiet = generate_creature_html(make_creature_scene(caption=False))
    loud = generate_creature_html(make_creature_scene(caption=True))
    assert 'id="hud"' not in quiet and 'id="hover"' not in quiet and "<li>" not in quiet
    assert 'id="hud"' in loud and 'id="hover"' in loud
    assert _code(quiet) == _code(loud)


def test_script_draws_only_from_the_scene_and_has_no_spine_or_rotated_copies() -> None:
    code = _code(generate_creature_html(make_creature_scene()))
    assert "rotate(" not in code  # no rotated copies of one shape (design.md:135)
    for removed in ("spineSegments", "symmetry_order", "geometry", "dynamics", "dominant_material", "materiality",
                    "palette.background", "emotional", "drawCharacter", "drawAbstract"):
        assert removed not in code
    assert "Math.random" not in code and "Date.now" not in code and "new Date" not in code


def test_page_is_deterministic() -> None:
    assert generate_creature_html(make_creature_scene()) == generate_creature_html(make_creature_scene())


def test_wrong_type_raises() -> None:
    with pytest.raises(TypeError, match="CreatureScene"):
        generate_creature_html("scene")  # type: ignore[arg-type]


NODE_HARNESS = r"""
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');
const start = html.indexOf('<script>', html.indexOf('gitgeist-state')) + 8;
const code = html.slice(start, html.indexOf('</script>', start));
const stateStart = html.indexOf('>', html.indexOf('gitgeist-state')) + 1;
const stateText = html.slice(stateStart, html.indexOf('</script>', stateStart));
const bad = [];
let calls = 0;
let minTop = Infinity;
const note = (name, args) => {
  if (name === 'arc') minTop = Math.min(minTop, args[1] - args[2]);
  else if (name === 'ellipse') minTop = Math.min(minTop, args[1] - Math.max(args[2], args[3]));
  else if (name === 'fillRect' && !(args[0] === 0 && args[1] === 0)) minTop = Math.min(minTop, args[1]);
};
const ctx = new Proxy({}, {
  get(target, name) {
    if (name in target) return target[name];
    return (...args) => {
      calls += 1;
      for (const a of args) if (typeof a === 'number' && !Number.isFinite(a)) bad.push(name + ':' + a);
      note(name, args);
      return {addColorStop() {}};
    };
  },
  set(target, name, value) { target[name] = value; return true; },
});
const canvas = {getContext: () => ctx};
const hoverBox = {style: {}};
const listeners = {};
let frame = null;
global.window = {
  innerWidth: Number(process.argv[3]), innerHeight: Number(process.argv[4]), devicePixelRatio: 1,
  addEventListener: (n, f) => { listeners[n] = f; },
};
global.document = {getElementById: (id) => id === 'gitgeist-state' ? {textContent: stateText}
  : id === 'hover' ? hoverBox : canvas};
global.requestAnimationFrame = (f) => { frame = f; };
eval(code);
for (const ts of [1, 1501, 7000, 12001, 12000 * 5 + 99]) frame(ts);
if (listeners.mousemove) {
  listeners.mousemove({clientX: window.innerWidth / 2, clientY: window.innerHeight / 2});
  listeners.mousemove({clientX: -5, clientY: -5});
}
console.log(JSON.stringify({bad, calls, minTop}));
"""


def _run(tmp_path: Path, scene: CreatureScene, size: tuple[int, int]) -> dict:
    page = tmp_path / "page.html"
    page.write_text(generate_creature_html(scene), encoding="utf-8")
    script = tmp_path / "harness.js"
    script.write_text(NODE_HARNESS, encoding="utf-8")
    result = subprocess.run(["node", str(script), str(page), str(size[0]), str(size[1])],
                            capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("size", [(520, 520), (1280, 720), (150, 90), (1, 1)])
def test_script_draws_without_nan_in_any_window_size(tmp_path: Path, size: tuple[int, int]) -> None:
    report = _run(tmp_path, make_creature_scene(), size)
    assert report["bad"] == []
    assert report["calls"] > 0


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("rows", [[(1.0, 1.0)], [(0.0, 0.0), (0.0, 0.0)], CORPUS_LIKE["flask"], CORPUS_LIKE["zlib"]])
@pytest.mark.parametrize("alive", [0.0, 1.0])
def test_script_draws_one_mass_empty_masses_and_eight_masses(tmp_path: Path, rows: list, alive: float) -> None:
    features = with_masses(make_features(), mass_table(rows))
    scene = build_creature_scene(features, make_character_spec(features, alive=alive), repository_name="x")
    report = _run(tmp_path, scene, (520, 520))
    assert report["bad"] == [] and report["calls"] > 0


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_script_draws_a_scene_without_masses_or_history(tmp_path: Path) -> None:
    features = make_features(commit_count=0, hotspots=[], timeline=[], timeline_start=None)
    features = with_masses(features, [])
    scene = build_creature_scene(features, make_character_spec(features), repository_name="empty")
    assert scene.body.torso is None
    report = _run(tmp_path, scene, (520, 520))
    assert report["bad"] == [] and report["calls"] > 0


def test_hud_is_a_fixed_height_box_inside_the_reserved_strip() -> None:
    page = generate_creature_html(make_creature_scene())
    assert "var HUD_STRIP = 120;" in _code(page)
    hud_css = page[page.index("#hud {") : page.index("#hud h1 {")]
    top = int(re.search(r"top: (\d+)px", hud_css).group(1))
    height = int(re.search(r"height: (\d+)px", hud_css).group(1))
    assert top + height + 2 * 1 <= 120
    assert "white-space: nowrap" in page[page.index("#hud h1, #hud li") :]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("size", [(520, 520), (1280, 720), (800, 1200), (400, 300)])
def test_composition_stays_below_the_hud_strip(tmp_path: Path, size: tuple[int, int]) -> None:
    # Crisp edges (no jitter, no blur) so the parts are exact; tendrils, sway and breathing may pass the circle a little.
    scene = make_creature_scene()
    crisp = scene.spec.model_copy(update={"edge": scene.spec.edge.model_copy(update={"blur_px": 0.0, "jitter": 0.0})})
    for coverage in (0.25, 0.85):
        spec = crisp.model_copy(update={"footprint": crisp.footprint.model_copy(update={"coverage": coverage})})
        top = _run(tmp_path, scene.model_copy(update={"spec": spec}), size)["minTop"]
        radius = 0.5 * min(coverage * min(size), size[1] - min(120, size[1] * 0.3))
        assert top >= min(120, size[1] * 0.3) - 0.12 * radius
