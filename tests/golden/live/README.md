# Live snapshots

## Abstract (0.10.0)

`orbits-0.10.0-live-preview.html` and `orbits-0.10.0-live-state.json` are the abstract `orbits` page and scene
JSON of `tests.orbits_helpers.make_scene()` at gitgeist 0.10.0 (the engine version is masked as
`<ENGINE_VERSION>`). `tests/test_orbits_snapshot.py` compares the current output with them (byte for byte on Linux; exact text except float literals, which match within a relative 1e-9, see `tests/snapshot_helpers.py`, because the last bit of a `math` result can differ on Windows):
stage 5 shares page code with the creature page and must not change the abstract output.

## Character (0.11.0)

`creature-0.11.0-live-state.json` is the `CreatureScene` of `tests.creature_helpers.make_creature_scene()`
at gitgeist 0.11.0, the regression anchor of the body plan and the scene JSON.
`tests/test_creature_scene.py::test_creature_scene_matches_the_0_11_0_snapshot` compares it the same way. If the body
plan changes on purpose, regenerate it with `python -m tests.regen_creature_snapshot` and review the diff.
