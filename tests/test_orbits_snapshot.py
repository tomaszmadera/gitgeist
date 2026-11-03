"""The abstract live output stays byte-identical to 0.10.0 (stage 5 spec, business rule 5 and criterion 5)."""

from __future__ import annotations

from pathlib import Path

from gitgeist._version import current_engine_version
from gitgeist.render.html_template import generate_orbits_html
from tests.orbits_helpers import make_scene

GOLDEN_LIVE = Path(__file__).parent / "golden" / "live"


def test_orbits_page_and_state_match_the_0_10_0_snapshot() -> None:
    """Snapshot of ``make_scene()`` taken at 0.10.0 before any page code was shared with the creature page.

    The engine version is masked; nothing else may change in the page or in the scene JSON.
    """
    version = current_engine_version()
    scene = make_scene()
    page = generate_orbits_html(scene).replace(version, "<ENGINE_VERSION>")
    state = scene.model_dump_json(indent=2).replace(version, "<ENGINE_VERSION>")
    assert page == (GOLDEN_LIVE / "orbits-0.10.0-live-preview.html").read_text(encoding="utf-8")
    assert state == (GOLDEN_LIVE / "orbits-0.10.0-live-state.json").read_text(encoding="utf-8")


def test_orbits_snapshot_covers_the_caption_off_page_too() -> None:
    version = current_engine_version()
    quiet = generate_orbits_html(make_scene(caption=False)).replace(version, "<ENGINE_VERSION>")
    loud = (GOLDEN_LIVE / "orbits-0.10.0-live-preview.html").read_text(encoding="utf-8")
    # Same drawing code with and without the HUD: only the HUD and hover markup differ.
    assert quiet.count("<script>") == loud.count("<script>")
    assert quiet.split("<script>")[-1].split("</script>")[0] == loud.split("<script>")[-1].split("</script>")[0]
