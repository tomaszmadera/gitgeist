# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file starts at 0.6.0. Earlier versions (tags `0.0.1` to `0.5.1`) have no changelog entries.

## [0.6.0] - Unreleased

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

[0.6.0]: https://github.com/tomaszmadera/gitgeist/compare/0.5.1...HEAD
