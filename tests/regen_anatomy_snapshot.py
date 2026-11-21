"""Regenerate tests/golden/live/anatomy-0.13.0-live-preview.html (run: PYTHONPATH=src python -m tests.regen_anatomy_snapshot)."""

from pathlib import Path

from gitgeist._version import current_engine_version
from gitgeist.render.anatomy_page import generate_anatomy_html
from tests.anatomy_helpers import make_anatomy_scene

TARGET = Path(__file__).parent / "golden" / "live" / "anatomy-0.13.0-live-preview.html"

if __name__ == "__main__":
    TARGET.write_text(
        generate_anatomy_html(make_anatomy_scene()).replace(current_engine_version(), "<ENGINE_VERSION>"),
        encoding="utf-8",
    )
    print("wrote", TARGET)
