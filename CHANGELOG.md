# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file starts at 0.6.0. Earlier versions (tags `0.0.1` to `0.5.1`) have no changelog entries.

## [0.11.0] - 2026-11-03

Live renderer v2 for the character representation (plan stage 5, GITGEIST-18; spec `docs/features/live-renderer-v2/character-spec.md`).

### Changed

- The character live portrait (`render --representation character --mode live`) is drawn from `VisualSpec` in the `creature` style instead of the fixed spine with ribs, core nodes and an ornament ring: the largest directory is an upright torso with growth rings, every other directory is a limb in a left/right pair along the body (the pad at its end is the directory; thickness from its file share, reach from its churn share, `1 + nesting_levels` segments), strands are tendrils growing from the torso, the focal knot sits on the limb of the top hotspot, and posture and speed follow `alive` (a dormant repository has curled, barely swaying limbs, an active one has extended, swaying limbs). The HUD, hover details and `--caption` work as for the abstract portrait, and both pages share the same page code (HUD strip, seeded noise, timeline replay).
- Breaking: for the character representation `live-state.json` holds a `CreatureScene` (schema version "1": the full `VisualSpec`, the computed body plan, the HUD conclusions and the hover details) instead of a `LiveSimulationState`. Readers of the old shape break. The abstract file does not change.
- Breaking: `render_live(scene, output_dir=None, *, identity)` takes the scene of either representation (`OrbitsScene` or `CreatureScene`); the representation comes from the scene. The `profile`, `mode`, `repository_name` and `scene=` parameters are removed (the scene carries the repository name); a scene of another type raises `TypeError`. Before and after:

  ```python
  # 0.10.0
  render_live(profile, "character", repository_name="repo", identity=identity)
  render_live(profile, "abstract", identity=identity, scene=orbits_scene)
  # 0.11.0
  spec = build_visual_spec(features, compute_traits(features), identity, "character")
  scene = build_creature_scene(features, spec, repository_name="repo")
  render_live(scene, identity=identity)
  render_live(orbits_scene, identity=identity)
  ```

- `LiveRenderArtifacts.state` is `OrbitsScene | CreatureScene`.
- The abstract live page and `live-state.json` are byte-identical to 0.10.0 apart from the engine version (checked against a committed 0.10.0 snapshot; on Linux byte for byte, across platforms exact text except float literals, which match within a relative 1e-9, because the last bit of a `math` result can differ on Windows): the HUD text and page code moved to modules shared with the creature page (`gitgeist.render.captions`, `gitgeist.render.page_common`).
- The `engine_version` string in `profile.json` and `live-state.json` follows the package version, so it changes to `0.11.0`.

### Added

- `gitgeist.render.creature.build_creature_scene` (and `build_creature_body`, the body plan as a pure function of the `VisualSpec`, computed from a new independent seed stream `"body"`; the `VisualSpec` and its golden snapshots do not change), `gitgeist.render.generate_creature_html` and the schemas `gitgeist.schemas.CreatureScene`, `CreatureBody`, `CreatureTorso`, `CreatureLimb` and `CreatureSegment`.
- Tests of the body plan, the scene and the page (offline, no browser; a Node.js check of the drawing code runs when `node` is installed) and a committed `CreatureScene` snapshot (`tests/golden/live/`).

### Removed

- Breaking: `gitgeist.render.character_renderer`, `dynamics` and `palette` and the functions `generate_character_simulation`, `generate_palette`, `generate_dynamics` and `generate_live_html` (also exported from `gitgeist.render`); the models `LiveSimulationState`, `ColorPalette`, `MotionDynamics` and `GeometryParameters` (also exported from `gitgeist.schemas`). Use `build_creature_scene` with `render_live(scene, ...)`.
- The 0.9.0 character snapshot of `tests/golden/live/` (its subject no longer exists); the abstract 0.10.0 snapshot stays.

### Development tools

- `tools/diversity_report.py` draws the character live render through the new path. D v1 is unchanged. On the 12-repository corpus the nearest-neighbour median `D` of the character live portraits is 0.442 (0.091 before; the closest pair is click and NeKode at 0.167, no longer gitgeist and NeKode at 0.039); the abstract median stays 0.409 (`docs/evidence/stage-5-live-renderer-d.txt`).

## [0.10.0] - 2026-11-03

Live renderer v2 for the abstract representation (plan stage 4, GITGEIST-17; spec `docs/features/live-renderer-v2/spec.md`).

### Changed

- The abstract live portrait (`render --representation abstract --mode live`) is drawn from `VisualSpec` in the `orbits` style instead of the rotated particle kaleidoscope: masses with growth rings, strands as orbits, a focal knot, edge quality, hatching, cracks and nested sub-shapes, one trait per channel. The animation replays the commit timeline in a 12 s loop. The HUD shows the repository name and three plain conclusions (the three traits farthest from 0.5) instead of material, seed and engine version, and hovering a body shows its directory, file count, share and top hotspot. The HUD is a fixed-size box in a strip reserved at the top of the window (120 px, with and without a caption), and the composition is fitted into the area below it, so the HUD never covers the portrait. A repository with no top-level directory reads "flat tree, all files at the root" instead of "deep, narrow tree".
- Breaking: for the abstract representation `live-state.json` holds an `OrbitsScene` (schema version "1": the full `VisualSpec`, the HUD conclusions and the hover details) instead of a `LiveSimulationState`. Readers of the old shape break. The character file does not change.
- Breaking: `render_live` takes a keyword-only `scene: OrbitsScene | None = None`. It is required for `mode="abstract"` (`TypeError` when missing) and must be `None` for `mode="character"` (`ValueError` otherwise). Before: `render_live(profile, "abstract", identity=identity)`. After:

  ```python
  spec = build_visual_spec(features, compute_traits(features), identity, "abstract")
  scene = build_orbits_scene(features, spec, repository_name="repo")
  render_live(profile, "abstract", identity=identity, scene=scene)
  ```

- `LiveRenderArtifacts.state` is `LiveSimulationState | OrbitsScene`.
- `generate_live_html` draws only the character representation; it raises `ValueError` for an abstract state. The character page and `live-state.json` are unchanged apart from the engine version: the page no longer contains the unused abstract drawing code (checked against a committed 0.9.0 snapshot).
- The `engine_version` string in `profile.json` and `live-state.json` follows the package version, so it changes to `0.10.0`.

### Added

- `gitgeist render --caption on|off` (default `on`, only with `--mode live`; `--mode prompt-to-image` exits with code 2). It switches the HUD and hover details of the abstract live page; the picture is the same.
- `gitgeist.render.orbits.build_orbits_scene`, `gitgeist.render.generate_orbits_html` and the schemas `gitgeist.schemas.OrbitsScene` and `HoverDetail`.
- Snapshot of the 0.9.0 character live output (`tests/golden/live/`) and tests for the scene, the page (offline, no browser; a Node.js check of the drawing code runs when `node` is installed).

### Removed

- Breaking: `gitgeist.render.abstract_renderer` and `generate_abstract_simulation` (also exported from `gitgeist.render`). Use `build_orbits_scene` with `render_live(..., scene=...)`.

### Development tools

- `tools/diversity_report.py` draws the abstract live render through the new path (scene built from the absolute traits at `--reference-time`). D v1 is unchanged. On the 12-repository corpus the nearest-neighbour median `D` of the abstract live portraits is 0.409 (0.186 before; `docs/evidence/stage-4-live-renderer-d.txt`).

## [0.9.0] - 2026-10-30

### Changed

- `traits.sprawl` (in `profile.json` and in `gitgeist.visual.compute_traits()`, both scale modes) is now the share of breadth in the tree structure, `top_level_dirs / (top_level_dirs + depth)` on the normalized inputs, and `0.0` when both are `0.0`. It was `0.5 * top_level_dirs + 0.5 * depth`. More top-level directories raise it, more depth lowers it. On the 12-repository reference corpus the correlation of `sprawl` with `size` falls from 0.880 to 0.740 and with `care` from 0.842 to 0.757 (absolute scale), so no trait pair is above 0.8 (GITGEIST-12; spec decision O14, accepted by Tomasz on 2026-10-30). The values of `sprawl` and the `topology.nesting_levels` of `VisualSpec` change for most repositories; the other traits and the signatures do not change.
- The `engine_version` string in `profile.json` follows the package version, so it changes to `0.9.0`.

## [0.8.0] - 2026-10-23

### Changed

- `profile.json`: `analyze` and `render` add the top-level `traits` block with nine portrait traits in the default `absolute` scale. `traits.reference_time` defaults to midnight UTC of the extraction day; it and `traits.alive` may change on different UTC days. Existing emotional scores, axes, materiality, summaries, live rendering and prompts keep their behavior, apart from the engine version string.
- `explain()` gains the optional keyword-only argument `traits: Traits | None = None`. When supplied, it serializes `Traits` into `profile.json`; `summary.md` and `why_this_look` stay unchanged. Existing calls keep working.

### Added

- `gitgeist.visual`: `compute_traits()`, `build_visual_spec()`, `registered_styles()` and `spec_distance()`. Traits compose stage 2 normalized inputs in both scale modes. VisualSpec assembles isolated channels, factual masses and timelines, language hues, seeded spiral packing and marks, with registered styles `orbits` and `creature` and variety levels `low`, `medium`, `high`.
- Frozen Pydantic schemas in `gitgeist.schemas.traits` (`Traits`, `TRAIT_NAMES`) and `gitgeist.schemas.visual_spec` (`VisualSpec`, `SeedInfo`, `Footprint`, `SpecMass`, `Rings`, `Palette`, `Knot`, `StrandPath`, `Strands`, `CrackMark`, `Cracks`, `Hatching`, `Edge`, `Topology`, `Motion`). The [schema document](docs/features/traits-visualspec-seeds/visual-spec.md) lists field ranges and a golden example.
- `tools/diversity_report.py`: `traits` layers for both scales, `visual_spec` layers for both representations with absolute traits, and a "Traits" section with correlation matrices, maximum |r|, participation ratios and nearest-neighbour spec distances.
- Eight synthetic repository fixtures and sixteen explicit-update golden VisualSpec snapshots, with per-representation diversity thresholds.

## [0.7.0] - 2026-10-22

### Changed

- `profile.json`: the `repository` block has new fields (additive, with defaults, so an older `profile.json` still validates): `static` gains `code_bytes`, `code_file_count`, `test_file_count`, `test_ratio`, `doc_ratio`, `todo_density`, `top_level_directory_count` and `language_shares`; `history` gains `timeline_start`, `timeline`, `active_months_ratio`, `top_author_share` and `top3_author_share`; every hotspot gains `change_share` and `mass`; the new `structure` block has the directory `masses` and `hotspot_concentration`. Existing fields keep their values, and the emotional state, the visual profile, `summary.md`, the live artifacts and the prompts do not change.

### Added

- Features v2 (`docs/features/features-v2-normalization/spec.md`): `LanguageShare`, `Mass` and `StructureFeatures` schemas, `gitgeist.features.structure` (at most 8 directory masses with file, churn and test-file shares and the dominant language, size-adjusted hotspot concentration), `days_since_last_commit()` in `gitgeist.features.history`, and `CODE_LANGUAGES`, `DOC_LANGUAGES`, `is_test_path()` and `ScannedFile` in `gitgeist.ingest.repository`. Extraction makes no new `git` calls.
- `gitgeist.normalization`: `normalize_features()` scales 13 inputs to [0, 1] in the `absolute` mode (log anchors and `smoothstep`) or the `corpus` mode (percentile against a quantile table), with `NormalizedInputs`, `QuantileTable` and `load_quantile_table()`. The package ships `gitgeist/normalization/data/quantiles-v1.json` as package data.
- `tools/build_quantile_table.py` and `tools/quantile-corpus.toml`: a development tool that builds the quantile table offline from local clones pinned to commits.
- `tools/diversity_report.py`: a `normalized` layer with both scale modes, a "Normalized inputs" section in `report.md`, `--reference-time`, and the `extract-time` command.

## [0.6.0] - 2026-10-22

### Changed

- Breaking: `render_live` takes a required keyword-only argument `identity: IdentitySeed`, and `generate_abstract_simulation` and `generate_character_simulation` take a required keyword-only argument `identity_seed: str`. Compute it with `gitgeist.compute_identity_seed(repo_path)`. `render_live` raises `TypeError` when `identity` is not an `IdentitySeed`.
- Breaking: the live generator seed comes only from the repository identity seed and the representation mode, no longer from profile values or `source_commit` (HEAD). The identity seed is the SHA-256 of the sorted root commit hashes, or of the directory name when the path is not a Git repository root with commits. A new commit no longer changes the live picture, but the seed, and with it every live picture, changes once for every repository compared with 0.5.1.
- `render_live` writes `identity-seed.json` next to `live-preview.html` and `live-state.json` when `output_dir` is set, and `gitgeist render --mode live` writes and lists it.
- Commit dates are read as Unix time (`git log --format=%at`) and stored as aware UTC datetimes. `first_commit_date` and `last_commit_date` are now always in UTC instead of the author's zone; the instant is unchanged.
- `gitgeist` CLI: `main()` also catches `RuntimeError` and reports it as an error message with exit code 1 (before: `OSError` and `ValueError` only). It was added for `compute_identity_seed`, which raises `RuntimeError` when listing root commits fails. The catch is broader than that source: any other `RuntimeError` raised in the pipeline, including its subclasses `NotImplementedError` and `RecursionError`, now ends as exit code 1 with a one-line message instead of a traceback. No test covers this path yet.
- README, package description and `BACKLOG.md` are in English, and the README's status and claims were corrected.

### Added

- `IdentitySeed` schema (`gitgeist.IdentitySeed`, `gitgeist.schemas.identity`) and `compute_identity_seed()` (`gitgeist.compute_identity_seed`, `gitgeist.ingest.identity`).
- `tools/diversity_report.py`: a development tool outside the package (offline, read-only for the scanned repositories). It runs the pipeline on a list of repositories and writes per-layer JSON, saturation counts, participation ratios of scores and axes, prompt line overlap, frozen-clock headless Chrome screenshots of the live previews, contact sheets and the image distance D (version 1, defined in the script) with its nearest-neighbour median. Needs Pillow and Chrome.
- Review loop rules (`review/rules.md`, `review/roles.md`) and a CI workflow (`.github/workflows/ci.yml`) that runs the tests on Python 3.11, 3.12 and 3.13.

### Fixed

- `summary.md` labels velocity as commits/week; it is computed per week but was printed as commits/day in the overview and in the volatility and tension signals.
- Commit dates whose stored zone is malformed (for example `+051800`, printed by `%aI` as `+518:00`) are no longer dropped silently.
- Author names containing `|` no longer cut the commit record short and drop its date.
- File changes are counted under real paths: renames no longer appear as `old => new` pseudo-paths and non-ASCII paths are not octal-escaped.
- The default `gitgeist-output` directory is skipped when scanning, so a rerun inside the repository does not analyse its own artifacts.
- Empty values in a local `.env` no longer shadow the user-level `~/.config/gitgeist/.env`.

[0.11.0]: https://github.com/tomaszmadera/gitgeist/compare/0.10.0...0.11.0
[0.10.0]: https://github.com/tomaszmadera/gitgeist/compare/0.9.0...0.10.0
[0.9.0]: https://github.com/tomaszmadera/gitgeist/compare/0.8.0...0.9.0
[0.8.0]: https://github.com/tomaszmadera/gitgeist/compare/0.7.0...0.8.0
[0.7.0]: https://github.com/tomaszmadera/gitgeist/compare/0.6.0...0.7.0
[0.6.0]: https://github.com/tomaszmadera/gitgeist/compare/0.5.1...0.6.0
