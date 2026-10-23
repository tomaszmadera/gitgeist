# Visual diversity: repair plan

Path: `docs/features/visual-diversity/plan.md`

Status: stage 0 decided on 2026-10-22; stage 1 done (merged in PR #3 on 2026-10-22, version 0.6.0); stage 2 done (spec in PR #5, implementation merged in PR #6, version 0.7.0); stage 3 spec approved on 2026-10-23 (`docs/features/traits-visualspec-seeds/spec.md`), implementation not started; stages 4 to 13 are not started. `D` means D v1 as defined in `tools/diversity_report.py`; baselines are in `analysis.md`. Evidence: `analysis.md`. Target design: `design.md`. Stages 0 to 8 build the counter strategy and the shared portrait format; stages 9 to 13 add the evaluation strategy.

## Classification

Per `AGENTS.md`, the whole change is `large` development: several independently demonstrable units (features, spec model, two live renderers, prompt, CLI, evaluator). It runs under the spec-driven workflow with a task record, an approved spec and plan per standard stage, and independent review. Small stages follow the small-development route. Stages 0 and 1 can start before any spec is approved.

## Stages

### Stage 0: decisions (no code)

Size: decision only.

Status: decided by you on 2026-10-22.

1. Channel rule: accepted. One trait per abstract visual channel, including cracks for TODO and debt density; the ban on "one trait -> one prop" stays for props and character items. Recorded in `docs/decisions/0001-trait-per-abstract-channel.md`, which amends sections 3 and 10 of `docs/product/emotional-repository-portrait-system.md` for abstract channels.
2. First styles: `orbits` (abstract) and `creature` (character).
3. Default scale mode: `absolute`.
4. Evaluation strategy: enabled as an opt-in with `--strategy evaluation`; `counters` stays the default; `jev-real-integration` stays `unmet`; the feature-extraction and emotional-state-model specs stay deterministic-only. Recorded in `docs/decisions/0002-optional-llm-evaluation-strategy.md`.
5. First evaluation backend: the Antigravity CLI `agy` (Google Gemini models), adapter id `agy`, called as `agy -p --print-timeout <seconds>`. You call this path "gemini-cli"; the `gemini` binary is not used.

Acceptance: decision records exist; `design.md` is updated to match. Met on 2026-10-22.

### Stage 1: measurement harness and bug fixes

Size: small, four independent changes, each with a test that fails before the fix.

Status: done. Merged in PR #3 on 2026-10-22, version 0.6.0. Line references in this stage point to `03741e1`, before the change.

1. Dev script that reproduces `analysis.md`: runs the pipeline on a list of repository paths, writes per-layer JSON, saturation counts, participation ratios and a headless Chrome contact sheet with distance `D`. Lives outside the package (for example `tools/diversity_report.py`). Acceptance: on the same 12 repositories at `03741e1` it reproduces the analysis tables. Result for `D`: met under D v1. The pre-v1 `D` numbers in `analysis.md` cannot be reproduced, because their measurement parameters were not recorded; the script defines D v1 with fixed parameters and a frozen 1.5 s animation clock, and repeated runs give identical values. The D v1 baseline at `03741e1` is 0.192 (abstract) and 0.083 (character).
2. `summary.md` labels velocity as commits/week (`explain/explainer.py:211`, `276`, `324`). Acceptance: test asserts the unit string.
3. Git dates from `--format=%H|%an|%at` (Unix time) instead of `%aI` (`ingest/git_history.py:80`). Acceptance: a fixture commit with a malformed zone (`+518:00`, as in `requests`) keeps its date.
4. Identity seed from the root commit, replacing the profile-plus-HEAD seed (`render/abstract_renderer.py:11-21`, `render/character_renderer.py:11-21`), and `identity-seed.json` written. Needs a one-line amendment to `docs/features/live-renderers/spec.md`. Acceptance: two fixture commits that change one file give the same seed; two fixture repositories with different roots give different seeds.

These four survive the redesign, so none of them is throwaway work.

### Stage 2: features v2 and normalization

Size: standard. Needs a spec (amends `docs/features/feature-extraction/spec.md`).

Status: done. Spec `docs/features/features-v2-normalization/spec.md` (PR #5); implementation merged in PR #6, version 0.7.0.

- New features from `design.md` "Features v2": recency, monthly timeline, active months, author concentration, masses, language shares by name, size-adjusted hotspot concentration, test ratio, doc ratio, TODO density, code bytes.
- Normalization module with `absolute` mode (log anchors and smoothstep) and percentile lookup against a quantile table.
- Dev script to build the quantile table from a fixed repository list; the table ships as package data with its own version.

Acceptance:

1. Each feature has a fixture test with an exact expected value.
2. Extraction time on `lua` grows by at most 50% over `main`.
3. On the 12-repository corpus, no normalized trait input is at 0 or 1 for more than 3 repositories (today up to 11 of 12 hit a cap).

### Stage 3: traits, VisualSpec and seeds

Size: standard. Needs a spec (amends `docs/features/visual-latent-mapper/spec.md`; new schema doc for `VisualSpec`).

Status: spec approved on 2026-10-23 (`docs/features/traits-visualspec-seeds/spec.md`, decisions O1-O13); implementation not started.

- 9 traits from `design.md` "Traits".
- `VisualSpec` schema: masses with positions and sizes, rings, palette, marks (knot, strands, cracks, hatching), motion, style, seeds.
- Seeded layout, style registry with `auto` selection and `--variety`.
- `profile.json` gains `traits`; `engine_version` changes; the decision on keeping the 14 axes is made in the spec.

Acceptance:

1. Channel isolation, monotonicity, determinism and seed tests from `design.md` "Testing diversity".
2. Golden diversity test on about 8 synthetic fixtures passes; `VisualSpec` golden snapshots committed.
3. Reference corpus report: no trait pair above |r| 0.8 on the 12-repository corpus.

### Stage 4: live renderer v2, abstract

Size: standard. Needs a spec (replaces the abstract business rules in `docs/features/live-renderers/spec.md`).

- Canvas code draws `VisualSpec` in the `orbits` style: masses, rings, knot, strands, edges, hatching, cracks.
- Motion grammar: timeline replay loop, speed by `alive`, no rotated copies.
- HUD with three plain conclusions and hover details per mass; `--caption`.

Acceptance:

1. HTML stays self-contained and works from `file:///`.
2. Contact sheet on the 12-repository corpus: nearest-neighbour median `D` v1 at least 0.40. Decided 2026-10-22: about 2x the D v1 baseline 0.192 at `03741e1` and about half of the v2 mockup (0.743). The previous target, 0.40 against the pre-v1 baseline 0.255, is not comparable with D v1. The baseline is remeasured on the same corpus right before the stage.
3. Your visual review of the contact sheet and two live pages.

### Stage 5: live renderer v2, character

Size: standard. Same spec family as stage 4.

- `creature` style: body plan from masses (largest mass as torso, others as limbs, depth as segments), rings on the torso, knot on the hotspot limb, posture and speed by `alive`.
- The fixed spine template (`html_template.py:217-295`) is removed.

Acceptance: as stage 4, with nearest-neighbour median `D` v1 at least 0.25 for character. Decided 2026-10-22: about 3x the D v1 baseline 0.083 at `03741e1`, keeping the larger relative step for character that the pre-v1 targets had (0.164 to 0.40). In addition, `gitgeist` and `NeKode` are no longer the closest pair.

### Stage 6: prompt composer v2

Size: standard. Needs a spec (amends `docs/features/prompt-to-image/spec.md`, which today fixes three qualifier bins and the block layout).

- Prompt from `VisualSpec` as in `design.md` "Prompt-to-image": subject sentence, 5 to 7 concrete directives, hex palette, seeded medium, negative constraints, name off by default.
- Seed passthrough if the OpenRouter images API accepts one (to verify).
- Fake backend draws a small raster of the spec.
- Caption strip composited with Pillow under `--caption on`.

Acceptance:

1. No prompt line other than fixed instructions is identical across the 12-repository corpus (today 20 of 48 are).
2. Paid A/B run, only after your approval: 12 repositories, one model, old and new prompt (24 images). Success: with captions removed, you match at least 9 of 12 new portraits to their repositories, and fewer with the old set.

### Stage 7: CLI and config

Size: small.

- Flags `--style`, `--seed`, `--variety`, `--scale`, `--palette`, `--caption`, `--prompt-name`.
- Config file lookup: CLI, `./gitgeist.toml`, `~/.config/gitgeist/config.toml`, defaults; unknown keys are an error.

Acceptance: CLI tests for each flag, precedence and the unknown-key error; README updated.

### Stage 8: more styles and portfolio scale

Size: small per style once stage 3 to 5 exist.

- Abstract `strata`, `topography`, `weave`; character `tree`, `colony`, `totem`.
- `--scale portfolio` with the opt-in feature store.

Acceptance per style: it draws every channel (channel isolation test on rendered spec), and the golden diversity test still passes.

### Stage 9: evaluator contract

Size: standard. Needs a spec (new `docs/features/evaluation-strategy/spec.md`).

- `EvaluationBundle` builder with budgets and exclusions; `evaluation-input.json` artifact.
- `RubricResult` schema and validation, single re-ask, cache, timeouts, error behavior without fallback.
- `Evaluator` interface and the `fake` adapter.

Acceptance:

1. Contract tests from `design.md` "Testing diversity" pass with the `fake` evaluator; no test calls a real backend.
2. The bundle is deterministic for a fixture commit and never contains `.env*`, key files, binaries or `.agents/`.
3. Every failure path exits non-zero with a message naming backend and cause.

### Stage 10: rubric, prompt and lenses

Size: standard (the rubric and prompt are a contract with their own versions).

- Rubric v1 (17 criteria, anchors) and prompt v1 as versioned package data.
- Lenses `default`, `newcomer`, `maintainer`, `craftsperson`, `archaeologist`, `critic`.
- Flat-score measures as a dev script: per-criterion spread, modal share, per-repository spread.

Acceptance:

1. Prompt rendering tests: the prompt contains every criterion with its anchors, the bundle, the lens text and the output schema; the version strings match.
2. With your yes, a dry run on 2 of your repositories through `agy` returns valid results.

### Stage 11: adapters

Size: small per adapter.

- `agy` first (Antigravity CLI, Google Gemini models), then `command`, `grok-cli`, `openrouter`. Exact CLI flags and the OpenRouter JSON schema option are verified while building each one.

Acceptance per adapter: a test with a stub executable or a local HTTP stub covers success, non-JSON output, timeout and missing binary or key; the key never appears in logs or artifacts.

### Stage 12: rubric-to-trait mapping and the strategy switch

Size: small, as an amendment to the stage 3 spec.

- Mapping table from `design.md` "Mapping rubric scores to traits", forced-choice adjustment, `null` handling, `focal_path` as knot position.
- `--strategy counters|evaluation`, `--evaluator`, `--lens`, `--eval-budget`, `--eval-refresh`, config keys `strategy` and `[evaluation]`.
- HUD and caption show strategy, backend, model and lens.

Acceptance: mapping tests with fixed `RubricResult` fixtures; both strategies produce a `VisualSpec` that passes the same schema and golden-structure tests; `--strategy evaluation` without a backend is an error.

### Stage 13: strategy comparison

Size: small (analysis, no product change). Needs your yes, because it calls an LLM backend.

- Run both strategies on the 12-repository corpus; write `docs/features/visual-diversity/comparison.md` with trait correlations, distances, flat-score measures and a side-by-side contact sheet.

Acceptance: the four criteria in `design.md` "Comparing the strategies". If they fail, the report says which mitigation from "Flat scores, the one real risk" to try next.

## Order and dependencies

```text
0 -> 1 (can run in parallel with 0)
0 -> 2 -> 3 -> 4 -> 5
               3 -> 6
               3 -> 7
          4, 5 -> 8
0, 2 -> 9 -> 10 -> 11
       3, 9 -> 12
4, 5, 11, 12 -> 13
```

Stages 4 and 6 can run in parallel after stage 3. Stages 9 to 11 can run in parallel with stages 3 to 5. The first visible change for you is stage 4; the first evaluation portrait comes after stage 12.

## Out of scope

- JEV integration (`docs/product/invariants.md`); the evaluation strategy does not change that invariant.
- Multi-commit timelines and comparison views (product section 16).
