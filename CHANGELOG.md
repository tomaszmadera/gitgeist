# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file starts at 0.6.0. Earlier versions (tags `0.0.1` to `0.5.1`) have no changelog entries.

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

[0.8.0]: https://github.com/tomaszmadera/gitgeist/compare/0.7.0...0.8.0
[0.7.0]: https://github.com/tomaszmadera/gitgeist/compare/0.6.0...0.7.0
[0.6.0]: https://github.com/tomaszmadera/gitgeist/compare/0.5.1...0.6.0
