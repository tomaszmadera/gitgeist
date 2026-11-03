"""Tests for the self-contained abstract orbits page (spec business rules 2, 3, 6)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from gitgeist.render.html_template import generate_orbits_html
from gitgeist.schemas.features import Hotspot
from gitgeist.schemas.live_state import OrbitsScene
from tests.orbits_helpers import make_features, make_scene, make_spec, with_traits

STATE_MARKER = '<script id="gitgeist-state" type="application/json">'
HOSTILE = '"><script>alert(1)</script>'


def _embedded_json(page: str) -> str:
    start = page.index(STATE_MARKER) + len(STATE_MARKER)
    return page[start : page.index("</script>", start)]


def _code(page: str) -> str:
    start = page.index("<script>", page.index(STATE_MARKER)) + len("<script>")
    return page[start : page.index("</script>", start)]


def test_embedded_json_parses_back_to_the_scene() -> None:
    scene = make_scene()
    page = generate_orbits_html(scene)
    assert OrbitsScene.model_validate_json(_embedded_json(page)) == scene
    assert json.loads(_embedded_json(page)) == json.loads(scene.model_dump_json())


@pytest.mark.parametrize("caption", [True, False])
def test_page_is_self_contained(caption: bool) -> None:
    page = generate_orbits_html(make_scene(caption=caption))
    assert re.findall(r"""(?:src|href)\s*=""", page) == []
    assert "url(" not in page and "@import" not in page and "<link" not in page
    for forbidden in ("http:", "https:", "//"):
        assert forbidden not in page
    assert "<canvas" in page and "requestAnimationFrame" in page


def test_hostile_names_are_escaped() -> None:
    features = make_features(hotspots=[Hotspot(path='src/<b>"x"</script>.py', change_count=9, mass="src")])
    spec = with_traits(make_spec(features), focus=1.0, size=0.5, age=0.5, alive=0.5, crowd=0.5,
                       care=0.5, sprawl=0.5, prose=0.5, debt=0.5)
    from gitgeist.render.orbits import build_orbits_scene

    scene = build_orbits_scene(features, spec, repository_name=HOSTILE)
    page = generate_orbits_html(scene)

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "&lt;b&gt;&quot;x&quot;&lt;/script&gt;.py" in page
    # One closing tag for the state payload and one for the code: the JSON cannot end its own tag early.
    assert page.count("</script>") == 2
    assert json.loads(_embedded_json(page))["repository_name"] == HOSTILE
    outside = page.replace(_embedded_json(page), "")
    assert "<b>" not in outside and "alert(1)</script>" not in outside


def test_hud_shows_name_and_three_conclusions_only() -> None:
    scene = make_scene()
    page = generate_orbits_html(scene)
    hud = page[page.index('<div id="hud">') : page.index('<div id="hover">')]
    assert "orbits-demo" in hud
    assert re.findall(r"<li>(.*?)</li>", hud) == scene.conclusions
    for removed in ("Material", "Seed", "Engine", "Mode"):
        assert removed not in hud


def test_caption_off_has_no_hud_or_hover_and_draws_the_same() -> None:
    quiet = generate_orbits_html(make_scene(caption=False))
    loud = generate_orbits_html(make_scene(caption=True))
    assert 'id="hud"' not in quiet and 'id="hover"' not in quiet and "<li>" not in quiet
    assert 'id="hud"' in loud and 'id="hover"' in loud
    assert _code(quiet) == _code(loud)


def test_script_draws_only_from_the_scene_and_has_no_rotated_copies() -> None:
    code = _code(generate_orbits_html(make_scene()))
    assert "rotate(" not in code
    for legacy in ("geometry", "symmetry_order", "dominant_material", "materiality", "axes", "emotional", "palette.background"):
        assert legacy not in code
    # Randomness comes only from the seeded generator.
    assert "Math.random" not in code and "Date.now" not in code and "new Date" not in code


def test_page_is_deterministic() -> None:
    assert generate_orbits_html(make_scene()) == generate_orbits_html(make_scene())


def test_wrong_type_raises() -> None:
    with pytest.raises(TypeError, match="OrbitsScene"):
        generate_orbits_html("scene")  # type: ignore[arg-type]


NODE_HARNESS = r"""
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');
const start = html.indexOf('<script>', html.indexOf('gitgeist-state')) + 8;
const code = html.slice(start, html.indexOf('</script>', start));
const stateStart = html.indexOf('>', html.indexOf('gitgeist-state')) + 1;
const stateText = html.slice(stateStart, html.indexOf('</script>', stateStart));
const bad = [];
let calls = 0;
const ctx = new Proxy({}, {
  get(target, name) {
    if (name in target) return target[name];
    return (...args) => {
      calls += 1;
      for (const a of args) if (typeof a === 'number' && !Number.isFinite(a)) bad.push(name + ':' + a);
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
console.log(JSON.stringify({bad, calls}));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("size", [(520, 520), (1280, 720), (150, 90), (1, 1)])
def test_script_draws_without_nan_in_any_window_size(tmp_path: Path, size: tuple[int, int]) -> None:
    page = tmp_path / "page.html"
    page.write_text(generate_orbits_html(make_scene()), encoding="utf-8")
    harness = tmp_path / "harness.js"
    harness.write_text(NODE_HARNESS, encoding="utf-8")
    result = subprocess.run(
        ["node", str(harness), str(page), str(size[0]), str(size[1])],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["bad"] == []
    assert report["calls"] > 0


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_script_draws_a_scene_without_masses_or_history(tmp_path: Path) -> None:
    features = make_features(commit_count=0, hotspots=[], timeline=[], timeline_start=None)
    features = features.model_copy(update={"structure": features.structure.model_copy(update={"masses": []})})
    from gitgeist.render.orbits import build_orbits_scene

    scene = build_orbits_scene(features, make_spec(features), repository_name="empty")
    page = tmp_path / "page.html"
    page.write_text(generate_orbits_html(scene), encoding="utf-8")
    harness = tmp_path / "harness.js"
    harness.write_text(NODE_HARNESS, encoding="utf-8")
    result = subprocess.run(["node", str(harness), str(page), "520", "520"], capture_output=True, text=True,
                            timeout=60, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["bad"] == []
