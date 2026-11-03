"""Regenerate tests/golden/live/creature-0.11.0-live-state.json (run: python -m tests.regen_creature_snapshot)."""

from pathlib import Path

from gitgeist._version import current_engine_version
from tests.creature_helpers import make_creature_scene

TARGET = Path(__file__).parent / "golden" / "live" / "creature-0.11.0-live-state.json"

if __name__ == "__main__":
    TARGET.write_text(
        make_creature_scene().model_dump_json(indent=2).replace(current_engine_version(), "<ENGINE_VERSION>"),
        encoding="utf-8",
    )
    print("wrote", TARGET)
