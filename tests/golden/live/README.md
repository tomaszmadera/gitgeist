# Character live snapshot (0.9.0)

`character-0.9.0-live-preview.html` and `character-0.9.0-live-state.json` are the output of
`render_live(profile, mode="character", repository_name="golden-character", identity=...)` at
gitgeist 0.9.0 (commit `4fa14c9`) for the profile and identity of `tests/test_live_renderers.py`
(`sample_profile`, `SAMPLE_IDENTITY`). The engine version is masked as `<ENGINE_VERSION>`.

`tests/test_live_renderers.py::test_character_live_output_matches_the_0_9_0_snapshot` compares the
current character output with them (spec `docs/features/live-renderer-v2/spec.md`, business rule 5).
The state JSON must match exactly. The page must match after removing the abstract code path that
0.10.0 deleted (`drawAbstract` and the mode dispatch); nothing else may change.
