# Traits, VisualSpec and seeds

Path: `docs/features/traits-visualspec-seeds/spec.md`

Status: approved 2026-10-23 (stage 3 of `docs/features/visual-diversity/plan.md`). Tomasz accepted the recommended option (a) of every decision O1-O13 in "Decisions"; the spec describes those options.

## Goal

Add the third step of the counter strategy from `design.md` "Architecture": turn the normalized inputs of stage 2 into 9 portrait traits, and build one renderer-neutral scene description, `VisualSpec`, from the traits, the factual structure of features v2 and the seeds. `VisualSpec` holds masses with positions and sizes, rings, palette, marks (knot, strands, cracks, hatching), edge quality, motion, style and seeds. A style registry with `auto` selection and a variety level picks the style. `profile.json` gains `traits`. The stage changes no picture: the live renderers, the prompt composer and `summary.md` do not read the new data yet. `VisualSpec` is the input of stages 4 (abstract live), 5 (character live) and 6 (prompt composer).

## Related requirements

- `docs/features/visual-diversity/plan.md:54-67` (stage 3: scope and acceptance criteria).
- `docs/features/visual-diversity/design.md:91-116` ("Traits": inputs, formulas, decision on the 14 axes deferred to this spec).
- `docs/features/visual-diversity/design.md:118-168` ("Visual grammar", "Composition and layout", "Motion grammar", "Styles": channels, ranges, spiral packing, style table, `--variety`).
- `docs/features/visual-diversity/design.md:170-174` ("Seeds": identity, user and effective seed).
- `docs/features/visual-diversity/design.md:414-424` ("Testing diversity": spec distance, golden diversity test, snapshots, channel isolation, monotonicity, determinism and seeds, reference corpus check).
- `docs/features/visual-diversity/design.md:21-31` (stage 0 decisions: channel rule, first styles `orbits` and `creature`, default scale `absolute`).
- `docs/decisions/0001-trait-per-abstract-channel.md` (one trait per abstract channel; no trait maps to a prop).
- `docs/decisions/0002-optional-llm-evaluation-strategy.md` (`counters` stays the default; this stage is deterministic).
- `docs/features/features-v2-normalization/spec.md` (stage 2: features v2, `normalize_features`, decision O11 that defers the order of normalization and trait formulas to this spec).
- `docs/features/visual-latent-mapper/spec.md` (layer 3 contract that this spec amends; see "Effect on existing specs").
- `docs/features/live-renderers/spec.md` (seed rule from stage 1; unchanged here).
- `docs/features/mvp-completion/spec.md:41` (snapshot stability of `profile.json`).
- `review/rules.md` (R5: offline tests; R8: CHANGELOG for API changes; R11: amendments in the language of the amended spec).

## Scope

1. New schemas, all Pydantic v2 and frozen:
   - `src/gitgeist/schemas/traits.py`: `Traits` (9 values in [0, 1] plus scale mode and reference time).
   - `src/gitgeist/schemas/visual_spec.py`: `VisualSpec` and its parts (`SeedInfo`, `Footprint`, `SpecMass`, `Rings`, `Palette`, `Knot`, `Strands`, `Cracks`, `Hatching`, `Edge`, `Topology`, `Motion`).
2. New package `src/gitgeist/visual/`:
   - `traits.py`: `compute_traits(features, scale, *, reference_time, table)` from `normalize_features`.
   - `seeds.py`: user seed handling, style seed, effective seed and labelled sub-seeds.
   - `styles.py`: style registry with `orbits` (abstract) and `creature` (character), `auto` selection and the variety levels `low`, `medium`, `high`.
   - `palette.py`: fixed hue per language, seeded hue offset, saturation from `alive`.
   - `layout.py`: seeded spiral packing of masses.
   - `spec_builder.py`: `build_visual_spec(...)`, the single entry point that assembles `VisualSpec`.
   - `distance.py`: spec distance from `design.md:418`, shared by tests and `tools/diversity_report.py`.
3. `profile.json` gains a top-level `traits` block: `explain()` takes an optional `traits` argument and the CLI `analyze` and `render` always pass it, computed with the default scale `absolute`.
4. Version 0.8.0 (`engine_version` follows the package version, `src/gitgeist/_version.py`) and a `CHANGELOG.md` entry (O13).
5. `tools/diversity_report.py`: a `traits` layer per repository, a `visual_spec` layer per repository and representation, and a "Traits" section in `report.md` with the trait correlation matrix, the maximum |r|, the participation ratio of the traits and the nearest-neighbour spec distance (for criterion 3).
6. Fixtures in `tests/fixtures/builder.py` for the golden diversity test (8 synthetic repositories, see "Required tests") and committed golden `VisualSpec` snapshots under `tests/golden/visual_spec/`.
7. Schema document for `VisualSpec` (plan: "new schema doc"), written with the implementation (O12).

## Non-goals

- Drawing `VisualSpec`: stage 4 (`orbits`, abstract live) and stage 5 (`creature`, character live). The existing live generators, `live-state.json`, `live-preview.html` and their seed (`render/abstract_renderer.py:10-17`) stay as they are.
- Prompt from `VisualSpec`, caption strip, `--prompt-name`: stage 6. HUD, hover details and the `summary.md` section "Reading this portrait": stages 4 and 5.
- CLI flags `--style`, `--seed`, `--variety`, `--scale`, `--palette`, `--caption` and the config file: stage 7 (O8). In stage 3 they are keyword arguments of the library.
- `--palette seeded`: stage 7 (flag) with the palette code it needs; stage 3 builds only the `language` palette.
- Styles `strata`, `topography`, `weave`, `tree`, `colony`, `totem` and `--scale portfolio`: stage 8.
- Evaluation strategy, rubric-to-trait mapping and `--strategy`: stages 9 to 12. Stage 12 amends this spec.
- Removing or changing the 14 axes, `MaterialityDistribution`, `EmotionalState` or the sensors (O6).
- New features, new `git` calls, new normalized inputs or anchors, and a new quantile table version.
- A `visual-spec.json` CLI artifact (O7).

## Behaviour

### Traits

- `compute_traits(features, scale="absolute", *, reference_time=None, table=None)` calls `normalize_features` with the same arguments and composes the 9 traits from the normalized `value`s. Traits are weighted means of values in [0, 1], so each is in [0, 1] in both scale modes and no trait needs its own anchor or quantile row (O1).
- `reference_time` defaults to `features.extracted_at` truncated to 00:00:00 UTC of that day (O5). An explicit `reference_time` is used as given.
- Each trait is rounded to 6 places (`round(x, 6)`) when stored; intermediate values keep full precision.

| Trait | Normalized inputs (stage 2 names) | Formula | Design source |
|---|---|---|---|
| `size` | `code_size` | `code_size` | `design.md:97` |
| `age` | `age` | `age` | `design.md:98` |
| `alive` | `recency`, `active_months` | `0.5 * recency + 0.5 * active_months` | `design.md:99` |
| `crowd` | `authors`, `top_author_share` | `0.5 * authors + 0.5 * (1 - top_author_share)` | `design.md:100` |
| `focus` | `focus` | `focus` | `design.md:101` |
| `care` | `test_ratio`, `ci` | `0.75 * test_ratio + 0.25 * ci` (O2) | `design.md:102` |
| `sprawl` | `top_level_dirs`, `depth` | `0.5 * top_level_dirs + 0.5 * depth` (O3) | `design.md:103` |
| `prose` | `doc_ratio` | `doc_ratio` | `design.md:104` |
| `debt` | `debt` | `debt` | `design.md:105` |

- Every normalized input feeds exactly one trait, so changing one raw feature changes at most one trait.
- Without history (`history.commit_count == 0`), `age`, `alive` and `crowd` are `0.0` (otherwise `top_author_share = 0.0` would give `crowd = 0.5` for a directory without Git).

### Structure

Structure is factual and comes from features v2 without scaling: `structure.masses`, `history.timeline` and `history.timeline_start`, `static.language_shares`, `history.hotspots` with `change_share` and `mass`. Traits never change structure, and seeds never change structure or traits.

### Seeds

- Identity seed: `IdentitySeed.identity_seed` from `compute_identity_seed` (stage 1), unchanged.
- User seed: `user_seed: int | None`, 0 to 2^63 - 1. `None` means identity seed only. Resolving `random` to a recorded integer belongs to the `--seed` flag (stage 7).
- Style seed: `int(sha256("style:{identity}:{user}")[:16], 16)`, where `{user}` is the decimal user seed or an empty string. It is used only to pick the style in `auto`, which breaks the cycle "the effective seed needs the style".
- Effective seed: `int(sha256("spec:{identity}:{user}:{style}")[:16], 16)` (`design.md:174`).
- Every free choice draws from its own sub-seed `sha256("{effective}:{label}")` with a fixed label (`layout`, `hue`, `strands`, `cracks`), so adding a new free choice later does not shift the others.
- Free choices are only: style in `auto`, layout start angle and jitter, hue offsets, strand phases and curvatures, crack positions (`design.md:50`).

### Styles

- The registry maps a style name to its representation and a fit rule. Stage 3 registers `orbits` (abstract) and `creature` (character), both with the fit rule "always" (`design.md:159`, `:163`: default).
- `style="auto"`: candidates are the registered styles of the representation whose fit rule holds, ordered by name; the pool is the first 1, 3 or all candidates for variety `low`, `medium`, `high`; the style seed picks one from the pool. With one registered style per representation, `auto` always returns `orbits` or `creature`.
- `style="<name>"`: the named style, which must exist and belong to the representation.
- Variety sets the maximum hue offset (10, 25 or 45 degrees, `design.md:168`) and the layout jitter (0.02, 0.05 or 0.10 footprint units, O11). Default variety is `medium`.

### VisualSpec

`build_visual_spec(features, traits, identity, representation, *, style="auto", user_seed=None, variety="medium")` returns a `VisualSpec`. Lengths and positions are in footprint units: the footprint is a circle of radius 1 centred at (0, 0), and renderers scale it by `footprint.coverage`. So `size` changes only the footprint and no mass position.

| Channel | Field | Driven by | Rule (trait `t` in [0, 1], `lerp(a, b, t) = a + (b - a) * t`) | Design source |
|---|---|---|---|---|
| footprint | `footprint.coverage`, `footprint.element_count` | `size` | `lerp(0.25, 0.85, t)` of frame diameter; `round(lerp(40, 600, t))` elements | `design.md:124` |
| rings | `rings.thickness` | `timeline` (O4) | one ring per calendar year of the timeline, oldest first; thickness = that year's commits / commits of the busiest year; more than 40 years: the oldest years are merged into the first ring | `design.md:125` |
| saturation | `palette.saturation` | `alive` | `lerp(0.10, 0.85, t)` | `design.md:126` |
| motion | `motion.speed_hz` | `alive` | `lerp(0.05, 1.2, t)` | `design.md:126`, `:148` |
| strands | `strands.count`, `strands.paths` | `crowd` | `round(lerp(1, 12, t))` strands; each path has a seeded phase in [0, 1) and curvature in [-1, 1] | `design.md:127`, `:150` |
| focal knot | `knot.radius` | `focus` | `lerp(0.15, 0.50, t)` of the owning mass radius | `design.md:128` |
| focal knot | `knot.mass_index`, `knot.path`, `knot.offset`, `knot.flicker` | `hotspots` | mass that owns the top hotspot; offset from the mass centre at half its radius, seeded angle; flicker = `change_share` of the top hotspot | `design.md:128`, `:149` |
| edge quality | `edge.blur_px`, `edge.jitter` | `care` | `6 * (1 - t)` px; `0.25 * (1 - t)` of radius | `design.md:129` |
| topology | `topology.nesting_levels` | `sprawl` | `round(lerp(0, 3, t))` nested sub-shapes per mass (O11) | `design.md:130` |
| topology | `masses` | `structure.masses` | one `SpecMass` per mass, see "Layout" | `design.md:130` |
| hatching | `hatching.coverage` | `prose` | `lerp(0, 0.60, t)` of mass area | `design.md:131` |
| cracks | `cracks.count`, `cracks.marks` | `debt` | `round(lerp(0, 60, t))` marks; each mark has a seeded mass index, position in the mass and angle | `design.md:132` |
| hue | `SpecMass.hue`, `palette.hue_offset` | `language_shares`, `Mass.dominant_language` | fixed hue per language plus one seeded offset in [-max, +max] for the whole spec; a mass without a dominant language is neutral (saturation 0 for that mass) | `design.md:133`, `:137` |
| motion | `motion.loop_seconds`, `motion.pulse` | `timeline` | `12.0`; monthly counts divided by the maximum month | `design.md:147` |

- The language hue table is a fixed mapping in `visual/palette.py` with one hue for each language in `EXTENSION_LANGUAGE_MAP`; a test pins it.
- `VisualSpec.traits` is a copy of the input `Traits`, so a spec records which values it was drawn from.

### Layout

- Masses keep the order of `structure.masses` (file count descending, then name). Mass radius before packing is `sqrt(file_share)`; after packing, all radii and positions are scaled so the composition fits in the unit circle.
- Seeded spiral packing (`design.md:141`): mass 0 at (0, 0) plus jitter; mass `k` is placed on the ray at angle `start + k * 137.508` degrees (golden angle), with `start` from the `layout` sub-seed, at the smallest distance in steps of 0.01 at which it does not overlap any placed mass; then jitter. Jitter is a seeded offset of at most the variety jitter in each axis.
- With the same identity seed, the same user seed and the same mass list, masses move only when file shares change (`design.md:141`).

### Profile and report

- `explain(features, emotional_state, profile, repository_name=None, output_dir=None, *, traits=None)`: when `traits` is set, `profile.json` gets a top-level key `traits` with `Traits.model_dump(mode="json")`; `summary.md` and `why_this_look` do not change.
- CLI `analyze` and `render` compute `compute_traits(features)` (scale `absolute`) and pass it to `explain`. No other CLI behaviour changes.
- `tools/diversity_report.py run` writes the `traits` and `visual_spec` layers and the "Traits" section with `--reference-time` as the trait reference time.

## Business rules

1. Determinism: the same features, reference time, scale, table, identity seed, user seed, style and variety give an identical `VisualSpec` (equal models and byte-identical `model_dump_json`).
2. Seeds touch only free choices: a different user seed gives identical `traits`, `masses` names, shares and order, `rings`, `footprint`, `knot.radius`, `edge`, `topology`, `hatching`, `palette.saturation`, `motion` and the counts of strands and cracks; only free fields may change.
3. Channel isolation: changing one normalized input changes exactly one trait and, in `VisualSpec`, only the fields of that trait's channel in "VisualSpec".
4. Monotonicity: each trait is non-decreasing in its input (`alive` non-increasing in days since the last commit), and each channel field is non-decreasing in its trait.
5. No picture change: the live renderers, the prompt composer, `summary.md`, `why_this_look`, `live-state.json`, `live-preview.html`, `prompt.txt` and `identity-seed.json` do not read traits or `VisualSpec`.
6. No silent fallback: an unknown style, a style of the other representation, an unknown variety or an invalid user seed is an error, never a switch to `auto` or a default. New code adds no `except` that hides errors.
7. Read-only and offline: trait and spec code calls no `git`, no network and no file system, except the quantile table read through `normalize_features` in the `corpus` mode.
8. The 14 axes, materiality and the emotional state keep their values for every input (O6).

## Authorization

`none` - local library and development scripts with no authorization mechanism and no network.

## Data / API

```python
# src/gitgeist/schemas/traits.py (frozen, extra="forbid")
TRAIT_NAMES = ("size", "age", "alive", "crowd", "focus", "care", "sprawl", "prose", "debt")

class Traits(BaseModel):
    scale: Literal["absolute", "corpus"]
    table_version: str | None          # None in the absolute mode
    reference_time: datetime           # aware UTC
    size: float                        # each trait: ge=0, le=1
    age: float
    alive: float
    crowd: float
    focus: float
    care: float
    sprawl: float
    prose: float
    debt: float
```

```python
# src/gitgeist/schemas/visual_spec.py (all frozen, extra="forbid")
class SeedInfo(BaseModel):
    identity_seed: str                 # 64 hex characters
    user_seed: int | None
    style_seed: int
    effective_seed: int

class Footprint(BaseModel):
    coverage: float                    # 0.25..0.85
    element_count: int                 # 40..600

class SpecMass(BaseModel):
    name: str
    is_merged: bool
    file_share: float
    churn_share: float
    language: str | None
    hue: float | None                  # degrees [0, 360); None without language
    x: float                           # footprint units
    y: float
    radius: float

class Rings(BaseModel):
    first_year: int | None
    thickness: list[float]             # 0..40 values in [0, 1]

class Palette(BaseModel):
    mode: Literal["language"]
    saturation: float                  # 0.10..0.85
    hue_offset: float                  # degrees, |offset| <= variety maximum

class Knot(BaseModel):
    mass_index: int                    # index into VisualSpec.masses
    path: str
    offset_x: float
    offset_y: float
    radius: float                      # share of the mass radius, 0.15..0.50
    flicker: float                     # change_share of the top hotspot

class StrandPath(BaseModel):
    phase: float
    curvature: float

class Strands(BaseModel):
    count: int                         # 1..12
    paths: list[StrandPath]            # len == count

class CrackMark(BaseModel):
    mass_index: int
    u: float                           # position in the mass, polar radius share [0, 1]
    v: float                           # polar angle share [0, 1)
    angle: float                       # degrees

class Cracks(BaseModel):
    count: int                         # 0..60
    marks: list[CrackMark]             # len == count

class Hatching(BaseModel):
    coverage: float                    # 0..0.60

class Edge(BaseModel):
    blur_px: float                     # 0..6
    jitter: float                      # 0..0.25

class Topology(BaseModel):
    nesting_levels: int                # 0..3

class Motion(BaseModel):
    speed_hz: float                    # 0.05..1.2
    loop_seconds: float                # 12.0
    pulse: list[float]                 # timeline / max month, [0, 1]

class VisualSpec(BaseModel):
    schema_version: Literal["1"]
    representation: Literal["abstract", "character"]
    style: str
    style_requested: str               # "auto" or the requested name
    variety: Literal["low", "medium", "high"]
    seeds: SeedInfo
    traits: Traits
    footprint: Footprint
    masses: list[SpecMass]             # 0..8
    rings: Rings
    palette: Palette
    knot: Knot | None
    strands: Strands
    cracks: Cracks
    hatching: Hatching
    edge: Edge
    topology: Topology
    motion: Motion
```

```python
# src/gitgeist/visual/__init__.py exports
def compute_traits(features: RepositoryFeatures, scale: ScaleMode = "absolute", *,
                   reference_time: datetime | None = None,
                   table: QuantileTable | None = None) -> Traits: ...
def build_visual_spec(features: RepositoryFeatures, traits: Traits, identity: IdentitySeed,
                      representation: Literal["abstract", "character"], *,
                      style: str = "auto", user_seed: int | None = None,
                      variety: Literal["low", "medium", "high"] = "medium") -> VisualSpec: ...
def registered_styles(representation: str) -> tuple[str, ...]: ...
def spec_distance(a: VisualSpec, b: VisualSpec) -> float: ...     # [0, 1]
```

Files written:

- Package: `profile.json` gains `traits` (see "Compatibility and migration"). No new CLI artifact (O7).
- Tests: golden snapshots `tests/golden/visual_spec/<fixture>-<representation>.json`, changed only by running the tests with `GITGEIST_UPDATE_GOLDEN=1`.
- Scripts: `tools/diversity_report.py` writes only under `--out`.

## Compatibility and migration

- `profile.json`: new top-level key `traits` next to `emotional_state`, `repository` and `visual_latent`. Existing keys and values do not change. `traits.reference_time` is the UTC day of the run, so two runs on the same snapshot on the same UTC day give identical traits; on another day `alive` may differ (O5).
- `summary.md`, `why_this_look`, `live-state.json`, `live-preview.html`, `prompt.txt`, `portrait.png` (fake backend), `identity-seed.json`: byte-identical apart from the engine version string.
- `explain()` gains a keyword-only argument with a default, so existing calls keep working; the CHANGELOG lists it (R8).
- Version 0.8.0 (new `profile.json` key and new public API), CHANGELOG entry (O13). New runtime dependencies: none.

## Effect on existing specs

- `docs/features/visual-latent-mapper/spec.md` (amended in the implementation PR, in Polish per R11): "Scope" and "Data / API" name the second layer 3 output (`Traits`, `VisualSpec`) with a link to this spec; the existing mapper, axes and business rules stay.
- `docs/features/mvp-completion/spec.md:41` (amended in Polish): `traits.reference_time` and `traits.alive` may change between runs on different UTC days.
- `docs/features/explainability/spec.md`: the `profile.json` roundtrip includes `traits`; amended in Polish if its "Data / API" lists the keys.
- `docs/features/features-v2-normalization/spec.md`: unchanged; decision O11 there is resolved by O1 here.
- `docs/features/live-renderers/spec.md`, `docs/features/prompt-to-image/spec.md`, `docs/features/emotional-state-model/spec.md`, `docs/features/feature-extraction/spec.md`: unchanged.
- `README.md`: `traits` in the description of `profile.json` and of the run-specific fields; "Measuring visual diversity" gets the `traits` and `visual_spec` layers.
- `docs/features/visual-diversity/plan.md`: stage 3 status set to "spec approved" in the spec PR; set to done only after the implementation merge.

## Edge cases

- Directory without Git or repository without commits: `age`, `alive`, `crowd` are `0.0`; `rings.thickness = []`, `first_year = None`; `motion.pulse = []`; `knot = None`; identity seed from the directory name (stage 1).
- No scanned files: `masses = []`, `knot = None`, `cracks.count = 0` (`todo_density` and so `debt` are 0 without files); `footprint` from `size = 0`.
- One mass: placed at (0, 0) plus jitter, radius 1 before jitter.
- Top hotspot whose `mass` is not in `masses` (Q1 case from PR #6, `Hotspot.mass = "other"` without a merged mass): `knot = None`. When `mass` is `other` and a merged `other` mass exists, the knot is on that mass (`is_merged = True`), never on a real directory named `other`.
- Two masses named `other` (real and merged, stage 2 edge case): told apart by `is_merged`; `knot.mass_index` and `CrackMark.mass_index` point by index, not by name.
- Timeline over more than 40 calendar years: 40 rings, the first ring holds the merged oldest years.
- Timeline within one calendar year: one ring with thickness `1.0`.
- `corpus` scale with a missing or invalid table: the error of `normalize_features`, no switch to `absolute`.
- Two masses with equal file share: order from stage 2 (name ascending), so packing is deterministic.

## Errors

- `compute_traits`: the errors of `normalize_features` (unknown scale, naive `reference_time`, missing or invalid table), unchanged.
- `build_visual_spec`: `style` not registered: `ValueError` naming the style and the registered styles of the representation; style of the other representation: `ValueError`; `variety` outside `low`, `medium`, `high`: `ValueError`; `user_seed` negative or above 2^63 - 1: `ValueError`; `identity` not an `IdentitySeed` or `traits` not a `Traits`: `TypeError`; unknown `representation`: `ValueError`.
- `explain`: `traits` not a `Traits` and not `None`: `TypeError`, like the existing argument checks.

## Acceptance criteria

1. The tests from `design.md` "Testing diversity" pass: channel isolation for each of the 9 traits, monotonicity on a 20-point grid per input, determinism (identical spec for the same inputs), user seed (business rule 2), and a fixture commit that changes one file keeps the identity seed and moves no mass by more than 0.05 footprint units (O11).
2. The golden diversity test on 8 synthetic fixtures passes: the smallest nearest-neighbour spec distance is at least the threshold recorded from the first passing run (O10), and no trait is constant across the fixtures. The golden `VisualSpec` snapshots of all 8 fixtures in both representations are committed.
3. Reference corpus report (offline, `tools/diversity_report.py`, not CI): on the 12-repository corpus of `analysis.md`, no trait pair has |r| above 0.8 with the default `absolute` scale; the `corpus` scale is reported, not gated (O9). The report log with its command goes into the PR.
4. No picture change: `tools/diversity_report.py run` on the same corpus gives on the branch and on `main` at the branch point identical `scores`, `nouls`, `choices`, `axes`, `materiality`, `live-state.json`, prompts and D v1 values, apart from the engine version string, as in stage 2 criterion 4.
5. `profile.json` from `analyze` contains `traits` with all 9 values, and `Traits` and `VisualSpec` pass a JSON roundtrip (`model_validate` after `model_dump(mode="json")`) with equal models.
6. All tests pass offline (R5) on Python 3.11, 3.12 and 3.13 in CI `verify` and in `verify-windows`.

## Required tests

Expected values below were computed by a reference script outside the repository with the stage 2 code at `a194bdd` and the recommended options. The implementation's test is the source of truth; a difference is a question for the spec, not a reason to change an expected value silently.

New fixtures in `tests/fixtures/builder.py` for the golden diversity test (`design.md:419`), dates through `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE`:

- `create_single_script_repo`: one shell script, 3 commits by one author over 2 weeks.
- `create_dormant_old_repo`: 10 commits spread over 2012 to 2016, nothing after.
- `create_big_team_repo`: 40 commits by 30 authors over 6 months, CI file.
- `create_monorepo_single_author`: 8 top-level directories, 2 languages, 60 commits by one author.
- `create_docs_only_repo`: Markdown and text files only.
- `create_fresh_repo`: 3 files, 1 commit.
- `create_one_hotspot_repo`: 20 files, 30 commits of which 25 touch one file.
- `create_deep_tree_repo`: one path 10 directories deep, TODO markers in 5 files.

`tests/test_traits.py` (new), `reference_time = 2026-04-16T00:00:00Z`, scale `absolute`, values to 6 places:

- `timeline_repo`: `size 0.0`, `age 0.333624`, `alive 0.590964`, `crowd 0.329394`, `focus 0.0`, `care 0.0`, `sprawl 0.0`, `prose 0.0`, `debt 0.0`.
- `wide_repo`: `alive 0.924992`, `crowd 0.0`, `focus 0.0754`, `sprawl 0.201278`, `prose 0.0179`.
- `clean-modular-repo`: `age 0.023946`, `alive 0.750103`, `crowd 0.172755`, `care 0.625`, `sprawl 0.118739`, `prose 0.2857`.
- Default reference time is `extracted_at` truncated to the UTC day.
- Directory without Git: `age`, `alive`, `crowd` are `0.0`.
- `corpus` scale on a test table built in the test: traits in [0, 1] and `table_version` recorded.
- Monotonicity per input on a 20-point grid; each input changes exactly one trait.

`tests/test_visual_spec.py` (new):

- Channel isolation: for each trait, a `Traits` copy with that trait moved from 0.2 to 0.8 changes only the fields of its channel (table in "VisualSpec"); `size` moves no mass.
- Channel ranges: each channel field at trait 0 and 1 equals the range ends in "VisualSpec".
- Rings: `timeline_repo` gives `first_year 2025` and two rings; a 45-year synthetic timeline gives 40 rings.
- Knot: on the owning mass for `wide_repo` (`a`); `None` for the Q1 case (`create_emptied_repo`); merged `other` versus a real `other` directory.
- Determinism: two builds give byte-identical `model_dump_json`.
- Seeds: user seed 1 versus 2 keeps every non-free field (business rule 2) and changes at least the layout start angle; style seed and effective seed follow the formulas in "Seeds".
- Stability: `wide_repo` plus one commit that changes `a/m1.py`: same identity seed, no mass moves more than 0.05.
- Errors: unknown style, style of the other representation, unknown variety, negative user seed.

`tests/test_styles.py` (new): `registered_styles("abstract") == ("orbits",)`, `registered_styles("character") == ("creature",)`; `auto` returns them for every variety; the pool size rule with a test registry of 4 styles (1, 3, 4).

`tests/test_spec_distance.py` (new): distance of a spec to itself is 0; symmetric; in [0, 1]; each of the four parts moves the distance when only that part differs.

`tests/test_golden_diversity.py` (new): builds the 8 fixtures, compares each `VisualSpec` with its snapshot (update only with `GITGEIST_UPDATE_GOLDEN=1`), asserts the nearest-neighbour threshold and that no trait is constant.

Regression and contracts:

- `tests/test_explain.py`: `profile.json` with `traits`; `summary.md` identical with and without `traits`.
- `tests/test_cli.py`: `analyze` writes `traits` with 9 values.
- `tests/test_extractor.py` and `tests/test_latent_mapper.py`: emotional state and axes unchanged.
- `tests/test_diversity_report.py`: `run --no-images` on two fixtures writes the `traits` and `visual_spec` layers and the "Traits" section.

No test uses the network, an LLM or the external corpus; criteria 3 and 4 are checked by the development script with the log in the PR.

## Risks

- Readability competes with variety (`design.md:438`): same-language repositories share a hue family. Stage 3 only builds the hue rule; `--palette seeded` is stage 7.
- Fixed absolute anchors keep some traits at 0 for small repositories (`size` is 0 for every test fixture with the 1 kB anchor). The golden test still needs every trait to vary across the 8 fixtures, so the fixtures must be chosen for that.
- The corpus correlation check runs on 12 repositories, so one repository moves |r| a lot; the result is a guard, not a proof of independence.
- `VisualSpec` is built before any renderer draws it, so stage 4 or 5 may need field changes. Such changes amend this spec (R10) and bump `schema_version`.
- `alive` depends on the run date; golden snapshots and tests must always pass a fixed reference time.

## Decisions

All decided by Tomasz on 2026-10-23: option (a) in O1-O13. The options stay below as a record of the reasoning.

O1. Order of normalization and trait formulas (open from stage 2, O11). (a) Compose traits from the per-input normalized values with the weights of `design.md:95-105`; works in both scale modes without new anchors or table rows. The `alive` term uses the stage 2 `recency` input (anchor 1825 days), not the `log(3650)` of `design.md:99`. (b) Compute each design formula on raw values and scale the result: needs new anchors and quantile rows for `alive`, `crowd`, `care`, `sprawl` (a new table version) and makes `design.md:99` and `:89` disagree on the recency horizon. Recommendation: (a). Decided: (a).

O2. `doc_ratio` feeds both `care` and `prose` in `design.md:102` and `:104`, which breaks channel isolation (`design.md:421`). (a) `care = 0.75 * test_ratio + 0.25 * ci` (the design's 3:1 weight of tests to CI); documentation shows only as hatching. (b) Keep the design formula and state in the isolation test that `doc_ratio` changes two traits. (c) Give `prose` another input: none exists in features v2, so it needs a new feature (outside the plan). Recommendation: (a). Decided: (a).

O3. `sprawl` weights. `design.md:103` gives `log10(dirs + 1) + 0.1 * depth`, not in [0, 1]. (a) `0.5 * top_level_dirs + 0.5 * depth` on the normalized inputs. (b) `0.57 * top_level_dirs + 0.43 * depth`, the ratio of the two terms at the stage 2 upper anchors (2.0 and 1.5). Recommendation: (a), simpler and close to (b). Decided: (a).

O4. What `age` drives. `design.md:125` draws rings "one per year, thickness by that year's commits", and the evaluation mapping keeps the ring count factual (`design.md:359`). (a) Ring count and thickness from the timeline (factual); the `age` trait is stored and is the input of the ring channel only through the history it is computed from; the isolation test for `age` changes the history span, which moves `age` and the rings together. (b) Ring count from the `age` trait (`lerp(1, 40, age)`), thickness resampled from the timeline: the trait drives the channel directly, but rings stop being one per year. Recommendation: (a), it follows the design text and stage 12. Decided: (a).

O5. Reference time for `alive` in `profile.json`. (a) `extracted_at` truncated to the UTC day: same-day runs are identical; `mvp-completion/spec.md:41` is amended for runs on different days. (b) Exact `extracted_at`: `traits` becomes a run-specific field and two runs a second apart can differ. (c) Time of the last commit: stable, but recency is then always 0 and `alive` loses its meaning. Recommendation: (a). Decided: (a).

O6. The 14 axes (`plan.md:61`, `design.md:116`). (a) Keep axes, materiality and the mapper unchanged in stage 3, because the live renderers (stages 4, 5) and the prompt composer (stage 6) still read them; decide removal in the stage 6 spec, when the last reader moves to `VisualSpec`. (b) Remove them from `profile.json` now: breaks the current renderers and prompts. (c) Keep them and mark them deprecated in the CHANGELOG now. Recommendation: (a). Decided: (a).

O7. Where `VisualSpec` goes in stage 3. (a) Library, `tools/diversity_report.py` and golden snapshots only; stage 4 adds a `visual-spec.json` artifact next to the live files. (b) `render` writes `visual-spec.json` now: a new artifact nothing reads yet, and `analyze` has no representation to build it for. Recommendation: (a). Decided: (a).

O8. Flags in stage 3. The plan lists "`auto` selection and `--variety`" for stage 3 (`plan.md:60`) and the flags `--style`, `--seed`, `--variety` for stage 7 (`plan.md:110`). (a) Stage 3 adds keyword arguments `style`, `user_seed`, `variety`; stage 7 adds the CLI flags and the config file. (b) Stage 3 adds `--style`, `--seed`, `--variety` to the CLI now: visible flags with no visible effect until stage 4. Recommendation: (a), as stage 2 did with `scale`. Decided: (a).

O9. Scale mode for criterion 3 (|r| at most 0.8). (a) Gate on `absolute` (the default), report `corpus`. (b) Both modes must pass. (c) Only `corpus`: the v1 table is built from the same corpus, so the check is circular. Recommendation: (a). Decided: (a).

O10. Spec distance and golden threshold details (`design.md:418-419` gives the parts, not their scaling). (a) Traits: mean absolute difference over the 9 traits; masses: earth mover's distance between the mass file shares sorted descending and padded with zeros to 8, divided by 7 (the maximum for 8 slots); hue: 12-bin histogram of mass hues weighted by file share, half the L1 distance; style: 1 if different; the spec distance is the mean of the four parts. The golden threshold is the smallest nearest-neighbour distance of the first passing run, rounded down to 0.01, per representation, written in the test with the run log in the PR. (b) Leave the details to the implementation and record them in the PR. Recommendation: (a), so the threshold has a fixed meaning. Decided: (a).

O11. Values the design does not give. (a) Accept: `topology.nesting_levels` 0 to 3; layout jitter 0.02, 0.05 and 0.10 footprint units for `low`, `medium`, `high`; stability threshold 0.05 footprint units for a one-file commit; knot offset at half the mass radius; neutral colour for masses without a known language. (b) Other values named by you. Recommendation: (a); they can change in stage 4 by amending this spec. Decided: (a).

O12. `VisualSpec` schema document (plan: "new schema doc"). (a) `docs/features/traits-visualspec-seeds/visual-spec.md` in the implementation PR, with field ranges and one example from a golden snapshot. (b) In this spec PR, before the code exists. (c) No separate document; "Data / API" here is the schema doc. Recommendation: (a). Decided: (a).

O13. Version. (a) 0.8.0: new `profile.json` key and new public API. (b) 0.7.1: the change is additive and no picture changes. Recommendation: (a), the same reasoning as stage 2 (O9 there). Decided: (a).

## Relevant SDD / ADR

- `docs/features/visual-diversity/plan.md`, `docs/features/visual-diversity/design.md`, `docs/features/visual-diversity/analysis.md`
- `docs/decisions/0001-trait-per-abstract-channel.md`, `docs/decisions/0002-optional-llm-evaluation-strategy.md`
- `docs/features/features-v2-normalization/spec.md`
- `docs/features/visual-latent-mapper/spec.md`, `docs/features/live-renderers/spec.md`, `docs/features/mvp-completion/spec.md`, `docs/features/explainability/spec.md`
