"""Anatomy live page and CLI (spec ``docs/features/anatomy-representation/spec.md``, stage 3).

These tests need the ``anatomy`` extra (``networkx``, ``numpy`` and ``scipy``) for the CLI runs; the page
tests use a hand-built scene and need no layout library.
"""

from __future__ import annotations

import colorsys
import json
import re
import sys
from pathlib import Path

import pytest

from gitgeist._version import current_engine_version
from gitgeist.cli import main
from gitgeist.ingest.identity import compute_identity_seed
from gitgeist.render import anatomy as layout
from gitgeist.render.anatomy_page import (
    LANGUAGE_HUES,
    LEGEND_ROWS,
    TISSUE_SATURATION,
    generate_anatomy_html,
    hud_lines,
)
from gitgeist.render.facade import render_live
from gitgeist.schemas.identity import IdentitySeed
from gitgeist.schemas.live_state import AnatomyScene
from tests.anatomy_helpers import make_anatomy_scene
from tests.fixtures.builder import create_anatomy_repo
from tests.snapshot_helpers import assert_matches_snapshot

GOLDEN_PAGE = Path(__file__).parent / "golden" / "live" / "anatomy-0.13.0-live-preview.html"
LIVE_FILES = ("live-preview.html", "live-state.json", "identity-seed.json")
ALL_FILES = ("profile.json", "summary.md", *LIVE_FILES)


@pytest.fixture(scope="module")
def anatomy_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return create_anatomy_repo(tmp_path_factory.mktemp("anatomy-cli") / "anatomy-repo")


def _render(repo: Path, out: Path, *extra: str) -> int:
    return main(["render", str(repo), "--representation", "anatomy", "--mode", "live", "-o", str(out), *extra])


def _page_without_state(page: str) -> str:
    """The page with the embedded scene JSON removed: CSS, markup and script only."""
    return re.sub(r'<script id="gitgeist-state" type="application/json">.*?</script>', "", page, flags=re.DOTALL)


# --- CLI -------------------------------------------------------------------------------------------


def test_render_anatomy_live_writes_the_five_artifacts(anatomy_repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    assert _render(anatomy_repo, out) == 0
    for name in ALL_FILES:
        assert (out / name).is_file(), f"missing artifact: {name}"
    scene = AnatomyScene.model_validate_json((out / "live-state.json").read_text(encoding="utf-8"))
    assert scene.repository_name == "anatomy-repo" and scene.caption is True
    assert scene.counts.files == 17 and scene.counts.bodies == 3
    page = (out / "live-preview.html").read_text(encoding="utf-8")
    assert 'id="hud"' in page and 'id="hover"' in page and 'id="legend"' in page
    assert "(Anatomy)</title>" in page
    identity = IdentitySeed.model_validate_json((out / "identity-seed.json").read_text(encoding="utf-8"))
    assert identity.root_commits


def test_render_anatomy_live_is_byte_identical_for_two_runs(anatomy_repo: Path, tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    assert _render(anatomy_repo, first) == 0
    assert _render(anatomy_repo, second) == 0
    assert (first / "live-state.json").read_bytes() == (second / "live-state.json").read_bytes()
    assert (first / "live-preview.html").read_bytes() == (second / "live-preview.html").read_bytes()


def test_render_anatomy_caption_off_removes_hud_and_hover_but_keeps_the_legend(
    anatomy_repo: Path, tmp_path: Path
) -> None:
    on, off = tmp_path / "on", tmp_path / "off"
    assert _render(anatomy_repo, on, "--caption", "on") == 0
    assert _render(anatomy_repo, off, "--caption", "off") == 0
    scene_on = AnatomyScene.model_validate_json((on / "live-state.json").read_text(encoding="utf-8"))
    scene_off = AnatomyScene.model_validate_json((off / "live-state.json").read_text(encoding="utf-8"))
    assert scene_on.caption and not scene_off.caption
    assert scene_on.model_copy(update={"caption": False}) == scene_off
    page_off = (off / "live-preview.html").read_text(encoding="utf-8")
    assert 'id="hud"' not in page_off and 'id="hover"' not in page_off
    assert 'id="legend"' in page_off


def test_render_anatomy_prompt_mode_exits_2_and_writes_nothing(
    anatomy_repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "prompt"
    code = main(["render", str(anatomy_repo), "--representation", "anatomy", "--mode", "prompt-to-image", "-o", str(out)])
    assert code == 2
    assert "error: --representation anatomy supports only --mode live" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize("library", ["networkx", "numpy", "scipy"])
def test_render_anatomy_without_the_extra_exits_1_with_the_hint_before_analysis(
    anatomy_repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, library: str
) -> None:
    monkeypatch.setitem(sys.modules, library, None)
    analysed: list[Path] = []
    monkeypatch.setattr("gitgeist.cli.extract_features", lambda path: analysed.append(path))
    out = tmp_path / "no-extra"
    assert _render(anatomy_repo, out) == 1
    err = capsys.readouterr().err
    assert (
        "error: --representation anatomy requires networkx, numpy and scipy; "
        "install them with: pip install gitgeist[anatomy]"
    ) in err
    assert analysed == []
    assert not out.exists()


def test_render_anatomy_organ_separation_failure_exits_1_without_a_page(
    anatomy_repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(layout, "SEPARATION_ROUNDS", 0)
    out = tmp_path / "diverged"
    assert _render(anatomy_repo, out) == 1
    err = capsys.readouterr().err
    assert re.search(r"error: organ separation did not converge in 0 rounds \(2 organs, body of web/\S+\)", err)
    assert not any((out / name).exists() for name in LIVE_FILES)


def test_render_anatomy_on_a_directory_without_git_exits_1_naming_the_cause(
    non_git_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "plain"
    assert _render(non_git_dir, out) == 1
    assert "is not a Git repository root" in capsys.readouterr().err
    assert not any((out / name).exists() for name in LIVE_FILES)


# --- Page ------------------------------------------------------------------------------------------


def test_anatomy_page_matches_the_snapshot() -> None:
    """Page of the hand-built scene; the engine version is masked, floats compared within a relative 1e-9.

    Regenerate with ``PYTHONPATH=src python -m tests.regen_anatomy_snapshot`` after an intended page change and review the diff.
    """
    version = current_engine_version()
    page = generate_anatomy_html(make_anatomy_scene()).replace(version, "<ENGINE_VERSION>")
    assert_matches_snapshot(page, GOLDEN_PAGE.read_text(encoding="utf-8"))


def test_anatomy_page_embeds_the_scene_json() -> None:
    scene = make_anatomy_scene()
    page = generate_anatomy_html(scene)
    embedded = re.search(r'<script id="gitgeist-state" type="application/json">\n(.*?)\n  </script>', page, re.DOTALL)
    assert embedded is not None
    assert AnatomyScene.model_validate_json(embedded.group(1).replace("<\\/", "</")) == scene


def test_anatomy_hud_shows_raw_counts_only() -> None:
    assert hud_lines(make_anatomy_scene()) == [
        "files scanned: 11",
        "edges: 7",
        "bodies: 1",
        "organs in the largest body: 2",
        "dust files: 2",
        "foreign share of lines: 13.2% (40 of 303)",
        "blame years: 2019-2024",
        "unresolved references: 5",
    ]
    page = generate_anatomy_html(make_anatomy_scene())
    for line in hud_lines(make_anatomy_scene()):
        assert f"<li>{line}</li>" in page


def test_anatomy_hud_of_an_empty_scene() -> None:
    empty = make_anatomy_scene().model_copy(
        update={
            "counts": make_anatomy_scene().counts.model_copy(
                update={"files": 0, "edges": 0, "bodies": 0, "organs_in_largest_body": 0, "dust": 0,
                        "cysts": 0, "lines": 0, "foreign_lines": 0, "unblamed": 0}
            ),
            "blame_years": None,
            "bodies": [],
            "tendons": [],
            "dust": [],
            "cysts": [],
            "unresolved_references": 0,
        }
    )
    lines = hud_lines(empty)
    assert "foreign share of lines: 0 of 0" in lines
    assert "blame years: none" in lines
    assert 'id="legend"' in generate_anatomy_html(empty)


def test_anatomy_legend_lists_every_visual_property_once() -> None:
    page = generate_anatomy_html(make_anatomy_scene(caption=False))
    legend = re.search(r'<div id="legend">(.*?)</div>\n', page, re.DOTALL)
    assert legend is not None
    items = re.findall(r"<li>", legend.group(1))
    assert len(items) == len(LEGEND_ROWS) == 14
    for name in ("PHP", "TypeScript", "JavaScript", "Python"):
        assert name in legend.group(1)


def test_anatomy_legend_states_the_dust_speck_size_rule() -> None:
    page = generate_anatomy_html(make_anatomy_scene())
    legend = re.search(r'<div id="legend">(.*?)</div>\n', page, re.DOTALL)
    assert legend is not None
    assert "0.18 of its cell radius, at least 0.6 px" in legend.group(1)
    assert "var DUST_SCALE = 0.18;" in page and "var DUST_MIN = 0.6;" in page


def test_anatomy_dust_is_drawn_above_the_bodies_and_hovered_first() -> None:
    script = generate_anatomy_html(make_anatomy_scene()).split("<script>")[-1]
    build = script[script.index("function build()") : script.index("window.addEventListener('resize', build)")]
    assert build.index("bodyLayers = scene.bodies.map") < build.index("scene.dust.forEach")
    draw = script[script.index("function draw(seconds)") : script.index("function factsText")]
    assert draw.index("bodyLayers.forEach") < draw.index("dustLayer.canvas")
    hover = script[script.index("var mx = event.clientX;") :]
    assert hover.index("scene.dust.forEach") < hover.index("for (var b = scene.bodies.length - 1;")


def test_anatomy_caption_off_page_has_the_same_script() -> None:
    on = generate_anatomy_html(make_anatomy_scene())
    off = generate_anatomy_html(make_anatomy_scene(caption=False))
    assert 'id="hud"' not in off and 'id="hover"' not in off and 'id="legend"' in off
    assert on.split("<script>")[-1] == off.split("<script>")[-1]


def test_render_live_accepts_an_anatomy_scene(tmp_path: Path) -> None:
    scene = make_anatomy_scene()
    artifacts = render_live(scene, tmp_path, identity=compute_identity_seed(create_anatomy_repo(tmp_path / "repo")))
    assert artifacts.state == scene
    assert artifacts.html_content == generate_anatomy_html(scene)
    assert json.loads((tmp_path / "live-state.json").read_text(encoding="utf-8"))["representation"] == "anatomy"


# --- Palette (criterion 7) -------------------------------------------------------------------------


def _forbidden(hue: float, saturation: float) -> bool:
    """Red (hue 340-20) or green (hue 90-150) at saturation above 40 %."""
    hue %= 360
    return saturation > 40 and (hue >= 340 or hue <= 20 or 90 <= hue <= 150)


def _page_colours(text: str) -> list[tuple[str, float, float]]:
    colours: list[tuple[str, float, float]] = []
    for match in re.finditer(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", text):
        digits = match.group(1)
        if len(digits) == 3:
            digits = "".join(c * 2 for c in digits)
        r, g, b = (int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4))
        hue, _light, sat = colorsys.rgb_to_hls(r, g, b)
        colours.append((match.group(0), hue * 360, sat * 100))
    for match in re.finditer(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", text):
        r, g, b = (int(v) / 255 for v in match.groups())
        hue, _light, sat = colorsys.rgb_to_hls(r, g, b)
        colours.append((match.group(0), hue * 360, sat * 100))
    for match in re.finditer(r"hsla?\(\s*([\d.]+)\s*,\s*([\d.]+)%", text):
        colours.append((match.group(0), float(match.group(1)), float(match.group(2))))
    return colours


def test_anatomy_page_has_no_red_or_green() -> None:
    page = _page_without_state(generate_anatomy_html(make_anatomy_scene()))
    colours = _page_colours(page)
    assert colours, "the palette check found no colour literal"
    assert [c for c in colours if _forbidden(c[1], c[2])] == []
    script_hues = json.loads(re.search(r"var LANGUAGE_HUE = (\{.*?\});", page).group(1))
    script_saturation = int(re.search(r"var TISSUE_SATURATION = (\d+);", page).group(1))
    assert script_hues == LANGUAGE_HUES and script_saturation == TISSUE_SATURATION
    assert [hue for hue in script_hues.values() if _forbidden(hue, script_saturation)] == []
    # The only computed colour of the script is the language hue at the tissue saturation.
    computed = [line.strip() for line in page.split("<script>")[-1].splitlines() if "hsl" in line]
    assert computed == [
        "return 'hsla(' + LANGUAGE_HUE[facts.language] + ',' + TISSUE_SATURATION + '%,' + light.toFixed(1) + '%,' + alpha + ')';"
    ]


def test_palette_check_rejects_red_and_green() -> None:
    assert _forbidden(0, 60) and _forbidden(350, 41) and _forbidden(120, 80)
    assert not _forbidden(0, 30) and not _forbidden(210, 90) and not _forbidden(45, 60)
    assert _page_colours("#ff0000 rgba(0, 200, 0, 0.5) hsl(120, 50%, 40%)")[0][2] > 40
