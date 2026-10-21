# Visual diversity: design proposal

Path: `docs/features/visual-diversity/design.md`

Status: proposal for review. It changes product contracts, so it needs your decision (see "Decision needed") before any spec is written. Evidence: `analysis.md`. Steps: `plan.md`.

## Goals

1. Different repositories look clearly different, in both representations (`abstract`, `character`) and both generation modes (`live`, `prompt-to-image`).
2. The main conclusions about a repository are readable at a glance, without a legend: size, age, whether it is alive, team shape, where change concentrates, care, sprawl.
3. Controlled unpredictability: a stable look per repository (identity seed), an optional user seed for a new variation, and switchable styles, all set by config and CLI flags.
4. Diversity is measured and guarded by tests.

## Non-goals

- A semantic or LLM layer (JEV stays `unmet`, `docs/product/invariants.md:7-16`). The design works without it and can take its output later as one more trait.
- Literal programmer symbols or mascots. The prompt negative constraints stay.
- Multi-commit timelines and comparison views (product section 16). The identity seed makes them possible later.

## Decision needed

The product document says visuals must not come from "arbitrary assignment of one trait to one prop" (`docs/product/emotional-repository-portrait-system.md:418-421`) and gives "many tests -> glasses" as the anti-example (`:84-92`). Your request, conclusions visible at a glance, needs a stable mapping a viewer can learn. This design resolves the conflict with one rule:

- Each trait owns one perceptual channel (footprint, rings, saturation, strands, focal knot, edge quality, topology, texture, cracks). Channels are abstract visual properties, never objects or symbols. Styles decide what the channels are drawn as, so the form still varies.

This is close to the document's own anti-example: `debt` drawn as cracks is near "many TODO -> scars". The difference is that cracks are a mark density every style draws its own way, not a fixed prop; whether that difference is enough is your call.

Because the product document outranks a design document, this needs an explicit product decision (ADR) amending sections 3 and 10. Recommended: accept the channel rule; keep the ban on props and symbols. If you reject it, goals 1 and 3 still apply, but goal 2 drops to "explained in `summary.md`" and the caption becomes the only at-a-glance reading.

## Architecture

The layer order from the product document stays: features, interpretation, visual latent, renderer. Three things change inside it.

```text
repo
  -> features v2 (scalars + structure: layout, timeline, languages, hotspots, authors)
  -> normalization (log + reference percentiles)
  -> traits (9 decorrelated scalars) + existing emotional state (kept for explain)
  -> VisualSpec (renderer-neutral scene: masses, rings, palette, marks, motion, style, seed)
  -> live abstract | live character | prompt abstract | prompt character
```

- Structure, not only scalars. The current latent is 14 scalars that collapse to about 2 dimensions (`analysis.md`, "Collapsed dimensions"). Layout, timeline and language mix are lists, and they carry most of what makes a repository recognizable. They travel to the renderer as structure.
- One scene description for all four outputs. `VisualSpec` is computed once; the live renderers draw it and the prompt composer describes it. This is what makes live and prompt agree (product test 6, `:1318-1320`).
- Seeds only touch free choices. Traits and structure come from data. The seed picks the style (in `auto`), layout angle, hue offsets inside a family, noise phases and strand paths. A new seed gives a new picture with the same readings.

## Features v2

All come from the existing tree scan and two `git log` calls. Today's extraction takes at most 1.7 s on the corpus (`lua`, 5868 commits); the prototype of the extra features took 6.5 s for all 12 repositories together.

| Feature | Source | Notes |
|---|---|---|
| `days_since_last_commit` | `git log --format=%at` | relative to extraction time; use `%at` to avoid broken ISO zones |
| `timeline` | commits per month, first to last commit | stored as counts; renderers resample |
| `active_months_ratio` | months with at least one commit / months in span | separates steady from bursty |
| `author_count`, `top_author_share`, `top3_author_share` | `git log --format=%ae` | team shape, bus factor |
| `masses` | top-level directories (max 8, rest merged as `other`): file share, churn share, dominant language, test-file share | root files form a mass named `.` |
| `max_directory_depth` | existing, now used | |
| `language_shares` | top 5 by file count | existing data, now used by name |
| `hotspot_concentration` | top-10 file change share minus `min(1, 10 / file_count)` | size-adjusted, see below |
| `hotspots` | top 3 paths with change share and owning mass | existing data, now used by path |
| `test_ratio` | test files / code files, capped at 1 | replaces the `has_tests` boolean as the driver; directory names matched by `test` substring |
| `doc_ratio` | Markdown, reStructuredText and text files / files with a known language | |
| `todo_density` | TODO and FIXME per 1000 files | |
| `code_bytes` | bytes in files with a code language | separates code size from assets |

The raw `hotspot_top10_share` correlated at -0.92 with directory breadth on the corpus, because small repositories trivially concentrate change. Subtracting the share a uniform spread would give dropped the strongest trait correlation to 0.86 (breadth vs care).

## Normalization

Every scalar becomes a value in [0, 1] in two steps.

1. Log transform for counts and sizes: `log10(x + 1)`. Ratios stay linear.
2. Scale mode, selected with `--scale`:

| Mode | Meaning | Use |
|---|---|---|
| `corpus` (default) | percentile against a reference quantile table shipped in the package | portraits comparable across users |
| `portfolio` | percentile against the repositories you scanned before, stored in `~/.config/gitgeist/portfolio.json` (features only, opt-in) | maximizes contrast inside your own set |
| `absolute` | fixed log anchors, then `smoothstep` | reproducible without any table |

Percentiles spread values evenly by construction, so no trait sits at a cap for most repositories. The reference table is built offline by a dev script from a fixed list of public repositories (target about 200, spread over languages, sizes and ages) and versioned with `engine_version`. Until it exists, `absolute` is the default.

Absolute anchors (value at 0 and at 1): code size 10 kB and 100 MB; age 7 days and 20 years; days since last commit 1 and 5 years (inverted); authors 1 and 1000; TODO density 0 and 200 per 1000 files.

## Traits

Each trait has distinct inputs, so they do not move together the way today's axes do.

| Trait | Inputs | Formula before scaling |
|---|---|---|
| `size` | `code_bytes` | `log10` |
| `age` | first to last commit, days | `log10` |
| `alive` | `days_since_last_commit`, `active_months_ratio` | `0.5 * (1 - log(days) / log(3650)) + 0.5 * active_months_ratio` |
| `crowd` | `author_count`, `top_author_share` | `0.5 * log(authors) / log(1000) + 0.5 * (1 - top_author_share)` |
| `focus` | size-adjusted `hotspot_concentration` | clipped to [0, 1] |
| `care` | `test_ratio`, CI, `doc_ratio` | `0.6 * test_ratio + 0.2 * ci + 0.2 * min(1, 3 * doc_ratio)` |
| `sprawl` | top-level directory count, `max_directory_depth` | `log10(dirs + 1) + 0.1 * depth` |
| `prose` | `doc_ratio` | linear |
| `debt` | `todo_density` | `log10` |

Prototype on the same 12 repositories (`analysis.md` corpus, percentile scaling):

| Layer | Participation ratio | First component | Pairs with |r| > 0.8 |
|---|---|---|---|
| current 14 axes | 2.19 | 65% | 26 |
| prototype 9 traits | 3.37 | 47% | 2 |

The scalar gain is real but moderate. Most of the visible gain comes from the structure channels (layout, rings, hues), which a correlation number does not capture; see the mockup below.

The emotional scores, nouls and choices stay for `summary.md` and the explain layer. Renderers stop reading them. Whether the 14 axes stay in `profile.json` is decided in the stage 3 spec.

## Visual grammar

One trait, one primary channel. Every style must draw every channel, so a reading learned in one style transfers to the others.

| Trait | Channel | Range | Reading |
|---|---|---|---|
| `size` | footprint: share of the frame the form covers; element count | 25% to 85% of frame diameter; 40 to 600 elements | small or large |
| `age` + `timeline` | growth rings or strata: one per year, thickness by that year's commits | 1 to 40 rings (older history merged) | young or old; bursty or steady; quiet years visible |
| `alive` | saturation and motion speed | saturation 0.10 to 0.85; motion 0.05 to 1.2 Hz | dormant (faded, still) or active (vivid, moving) |
| `crowd` | strands threading the form | 1 to 12 | solo or team |
| `focus` + `hotspots` | focal knot: bright mark on the mass that owns the top hotspot, off its center | radius 15% to 50% of the mass | change concentrated in one place, or spread |
| `care` | edge quality | crisp outline and aligned marks at 1; frayed, blurred edge (up to 6 px, jitter up to 25% of radius) at 0 | tended or loose |
| `sprawl` + `masses` | topology: one mass per top-level directory, size by file share, depth as nested sub-shapes | 1 to 8 masses | flat or branched; lopsided or balanced |
| `prose` | fine hatching texture inside masses | 0% to 60% of mass area | code-heavy or text-heavy |
| `debt` | cracks and erosion marks | 0 to 60 | clean or marked |
| `language_shares` | hue family per mass from its dominant language; area by share | fixed hue per language, seed offset of up to 25 degrees | what the repository is made of |

Symmetry is no longer a parameter. It appears only when the data is balanced (similar mass sizes, even timeline). The rotated-copy kaleidoscope (`html_template.py:184-213`) and the fixed spine profile (`html_template.py:248`) are removed.

Language hues make same-language repositories share a family (`click`, `flask`, `requests` are all Python). Layout, rings, knot and strands still separate them, and the seed shifts the hue inside the family. If that is not enough, `--palette seeded` drops the language rule for palette and keeps it in the caption.

### Composition and layout

Masses are placed by a seeded spiral packing: the largest mass near the center, the rest at increasing distance, starting angle from the seed. Unequal directory sizes produce asymmetric compositions on their own. With the same identity seed, a new commit moves masses only when directory shares change.

### Motion grammar (live)

The animation shows history instead of a generic pulse.

- One loop replays the timeline in 12 s: global pulse amplitude follows commits per period, so bursts, quiet years and revivals are visible as a rhythm. The loop ends on the last 90 days.
- Base speed and drift follow `alive`: a dormant repository barely moves.
- The focal knot flickers with its file's change frequency.
- Strands move independently; more authors means more independent motion.
- No mirrored or rotated copies.

### Styles

Styles change how channels are drawn, never which trait drives which channel. `--style auto` lets the seed pick from the styles that fit the data; `--style <name>` fixes one.

| Representation | Style | Draws masses as | Fit hint for `auto` |
|---|---|---|---|
| abstract | `orbits` | bodies with growth rings, strands as orbits | default |
| abstract | `strata` | geological layers (timeline) with masses as inclusions | long history |
| abstract | `topography` | contour map, height by churn | high churn |
| abstract | `weave` | threads per author over time | large team |
| character | `creature` | body plan: torso is the largest mass, limbs are other masses, limb segments by depth | default |
| character | `tree` | trunk and branches from the directory tree, rings in the trunk | deep tree |
| character | `colony` | many small bodies, one per mass | flat, many top-level directories |
| character | `totem` | stacked segments, one per mass | few large masses |

`--variety {low,medium,high}` sets how much the seed may change: hue offset 10, 25 or 45 degrees; layout jitter; `auto` picks from 1, 3 or all fitting styles.

## Seeds

- Identity seed: SHA-256 of the root commit hash (all roots, sorted). Without Git: the directory name. Stable across commits, branches and clones. Written to `identity-seed.json`, which the product already lists as an optional artifact (`:1164-1168`).
- User seed: `--seed <int>` or `--seed random`. `random` prints the chosen value and records it, so any picture can be reproduced.
- Effective seed: hash of identity seed, user seed and style. The current seed (hash of the profile and HEAD, `abstract_renderer.py:11-21`) is removed, so commits no longer reshuffle the picture.

## Reading at a glance

- Live HUD: replace material, seed and engine (`html_template.py:97-103`) with the three most extreme traits as plain phrases with their numbers, for example "33 years old", "one main author (98%)", "last commit 4 days ago". Hover on a mass shows its directory, files and top hotspot. Toggle with `--caption on|off` (default on).
- Prompt-to-image: the model is never asked for text. With `--caption on`, gitgeist adds the same three phrases as a strip under the image with Pillow (already an optional dependency, `pyproject.toml` extra `image`).
- `summary.md` gets a "Reading this portrait" section mapping each visible channel to its trait value.

## Prompt-to-image

The prompt describes the `VisualSpec`, not 24 qualifiers.

1. One subject sentence from representation and style, for example "An abstract composition of five separate bodies with concentric growth rings, seen from above."
2. Five to seven concrete directives from the most extreme traits only, each stated as something visible: count, relative size, position, color, edge. Traits near the middle are left out, because "medium" adds no information.
3. Palette as hex colors from the same palette code the live renderer uses.
4. Medium from the style pack (for example ink, cut paper, carved stone, macro photography), chosen by seed.
5. Existing negative constraints.
6. Repository name left out by default, to avoid literal puns; `--prompt-name` adds it back.

Example for `lua` (33 years, one main author, last commit 4 days ago, three top-level directories; colors are illustrative):

```text
An abstract composition of two large bodies and one small one, off-center to the left, on a dark ground.
- Each large body shows 33 thin concentric growth rings, thickest in the middle rings.
- One bright, small knot sits off-center inside the larger body.
- A single thin strand links the bodies.
- Slightly frayed edges; no cracks.
- Vivid, saturated color: #d8432e, #b8321f, #f2c94c on #2b2620.
Medium: carved and painted stone relief.
No text, no letters, no logos, no code, no screens, no mascots.
```

Pass the effective seed to the backend when the API accepts one (to verify for OpenRouter images). The fake backend draws a small raster of the `VisualSpec` instead of hash noise, so offline tests show the composition.

That concrete directives make image models follow repository structure is an assumption. Plan stage 6 checks it with a small paid A/B run, after your approval.

## Configuration and CLI

New flags on `gitgeist render` (and on `analyze` where they affect `profile.json`):

| Flag | Values | Default |
|---|---|---|
| `--style` | `auto` or a style name for the representation | `auto` |
| `--seed` | integer or `random` | none (identity seed only) |
| `--variety` | `low`, `medium`, `high` | `medium` |
| `--scale` | `corpus`, `portfolio`, `absolute` | `absolute` until the corpus table exists |
| `--palette` | `language`, `seeded` | `language` |
| `--caption` | `on`, `off` | `on` |
| `--prompt-name` | flag | off |

Optional config file, same keys, precedence: CLI, then `./gitgeist.toml`, then `~/.config/gitgeist/config.toml` (same directory as the existing user `.env`, `src/gitgeist/env.py:68-71`), then defaults. Unknown keys are an error, not ignored.

## Testing diversity

Metrics live on `VisualSpec`, not on pixels, so tests are fast and deterministic. Pixel metrics stay a dev tool, because random particle noise scores as "different" while portraits look the same (`analysis.md`, "Method").

- Spec distance: L1 over trait values + earth mover's distance over mass size vectors + hue histogram distance over the palette + 1 if the style differs; each part scaled to [0, 1] and averaged.
- Golden diversity test: about 8 synthetic fixture repositories built with `tests/fixtures/builder.py` (single script, dormant old, big team, single-author monorepo, docs-only, fresh one-commit, one-hotspot, deep tree). Assert the nearest-neighbour spec distance is at least a threshold set from the first passing run, and no trait is constant across the fixtures.
- Golden snapshots: the fixture `VisualSpec` JSON files are committed and change only with an explicit update flag.
- Channel isolation: changing one raw feature changes only its trait and that trait's channel fields.
- Monotonicity: each trait rises with its input.
- Determinism and seeds: same repository and seed give identical spec and HTML; another user seed keeps traits and structure identical and changes free fields; a fixture commit that touches one file keeps the identity seed and moves no mass by more than a small threshold.
- Reference corpus check (offline dev script, not CI): trait participation ratio and maximum |r|, reported with each engine version. Target: no trait pair above |r| 0.8.
- Image check (dev script): headless Chrome contact sheet and distance `D` from `analysis.md`. Baseline nearest-neighbour median: 0.255 (abstract), 0.164 (character). Mockup: 0.462. Target for stage 4 and 5: at least 0.40 on the 12-repository corpus.

## Mockup

A static Pillow sketch of the abstract `orbits` style using the prototype traits and features (not product code; masses cycle through the repository's languages instead of using each directory's own language):

![Mockup of the proposed grammar, 12 repositories](assets/mockup-v2-abstract.jpg)

What it shows: `is-odd` and `z` are pale and faded (dormant for years), `lua` has two large masses with many rings and one strand (old, one author), `NeKode` and `gitgeist` are vivid with few rings (young, active), `awesome` is light with frayed edges (text-heavy, no tests), `zlib` and `requests` are many ringed masses (old, broad). On the image distance `D`, the nearest-neighbour median goes from 0.255 (abstract) and 0.164 (character) to 0.462, and the closest pair from 0.103 and 0.043 to 0.300.

## Risks

- Readability competes with variety. The language-hue rule and fixed channels make portraits learnable but can make same-stack repositories look related. `--palette seeded` and the style pool are the release valve.
- A corpus table must be kept current. Without it, `absolute` scaling is less even; the 12-repository prototype used percentiles inside the corpus.
- Prompt adherence of image models is unverified (stage 6).
- `profile.json` changes shape; `engine_version` must change and the README determinism claim for `analyze` must be rechecked.
