# Live renderer v2: abstract `orbits`

Path: `docs/features/live-renderer-v2/spec.md`

Status: decisions approved by Tomasz 2026-11-03 (stage 4 of `docs/features/visual-diversity/plan.md`, Plane GITGEIST-17). O1-O9 option (a), O10 option (b): spec and implementation in one PR. Implemented in 0.10.0 on branch `gitgeist-17-stage-4-spec`; implementation in review.

## Goal

Draw `VisualSpec` (stage 3) in the live abstract portrait. `gitgeist render --representation abstract --mode live` stops drawing the 14 axes as a rotated kaleidoscope and draws the `orbits` style instead: masses with growth rings, strands as orbits, the focal knot, edge quality, hatching, cracks and nested sub-shapes, each from its own trait channel (`design.md` "Visual grammar"). The animation replays the repository's history (`design.md` "Motion grammar"). The HUD shows three plain conclusions about the repository instead of material, seed and engine, and hovering a mass shows its directory. This is the first stage whose result Tomasz sees in a picture (`plan.md` "Order and dependencies").

## Related requirements

- `docs/features/visual-diversity/plan.md:73-85` (stage 4: scope and acceptance criteria).
- `docs/features/visual-diversity/design.md:118-152` ("Visual grammar", "Composition and layout", "Motion grammar": channels, ranges, no rotated copies, timeline replay).
- `docs/features/visual-diversity/design.md:153-168` ("Styles": `orbits` draws masses as bodies with growth rings and strands as orbits).
- `docs/features/visual-diversity/design.md:176-180` ("Reading at a glance": HUD with three plain conclusions, hover, `--caption on|off`).
- `docs/features/visual-diversity/design.md:414-426` ("Testing diversity": image check with `tools/diversity_report.py`, frozen 1.5 s clock, D v1, target 0.40 for abstract).
- `docs/features/traits-visualspec-seeds/spec.md` and `visual-spec.md` (the `VisualSpec` contract this stage draws; risk "stage 4 or 5 may need field changes").
- `docs/features/live-renderers/spec.md` (layer 4 contract; its abstract business rules are replaced, see "Effect on existing specs").
- `docs/decisions/0001-trait-per-abstract-channel.md` (one trait per abstract channel).
- `docs/product/emotional-repository-portrait-system.md:1157-1159` (live mode artifacts, including `live-state.json`).
- The gitgeist review rules outside the repository, `F:\projects\grok-bot\review\gitgeist\rules.md` (R5 offline tests, R8 CHANGELOG and specs for API changes, R10 plan criteria, R11 amendment language, R12 version bump).

## Scope

1. `src/gitgeist/render/orbits.py` (new): `build_orbits_scene(features, spec, *, repository_name=None, caption=True) -> OrbitsScene`, the Python half of the renderer. It computes everything the browser needs that is not in `VisualSpec`: the three HUD conclusions and the hover details per mass (O3, O4).
2. `src/gitgeist/schemas/live_state.py`: new frozen model `OrbitsScene` (schema below). `LiveSimulationState` stays for `character` until stage 5.
3. `src/gitgeist/render/html_template.py`: a second template, `generate_orbits_html(scene)`, with its own Canvas 2D code that draws only from the embedded `OrbitsScene` JSON. The old `drawAbstract` code path, including the rotated copies (`html_template.py:184-213` at `03741e1`), is removed.
4. `src/gitgeist/render/facade.py`: `render_live` takes the scene for the abstract representation (O1); the abstract branch no longer calls `generate_abstract_simulation`, which is removed with its module.
5. CLI `gitgeist render`: for `--representation abstract --mode live` it builds `compute_traits(features)`, `build_visual_spec(features, traits, identity, "abstract")` and the scene, and writes the artifacts (O2). New flag `--caption on|off` (default `on`), valid only with `--mode live` (O5).
6. `tools/diversity_report.py`: the live abstract render goes through the new path; the report keeps D v1 unchanged so numbers stay comparable with the baseline.
7. Version 0.10.0 and a `CHANGELOG.md` entry (O9).

## Non-goals

- `character` representation and the `creature` style: stage 5. `--representation character --mode live` renders exactly as in 0.9.0.
- Prompt composer v2, caption strip under images, `--prompt-name`: stage 6.
- `--style`, `--seed`, `--variety`, `--scale`, `--palette` flags and the config file: stage 7. The CLI uses `style="auto"`, no user seed, `variety="medium"`, scale `absolute` and palette `language`, the stage 3 defaults.
- Styles other than `orbits`: stage 8.
- The `summary.md` section "Reading this portrait" (O8).
- Changes to traits, `VisualSpec` fields or its `schema_version` (O4).
- Pixel metrics in tests (`design.md:416`).

## Behaviour

### Coordinates

- The canvas fills the window. A strip of `HUD_STRIP = 120` px at the top of the window is reserved for the HUD, with and without a caption, so the drawing never depends on `caption` and the HUD never covers the composition. In windows lower than 400 px the strip is 30% of the height. The HUD is a box of fixed height (104 px at 12 px from the top and left, one line per conclusion, long text cut with an ellipsis), so it always ends inside the strip.
- The footprint circle of `VisualSpec` (radius 1 at (0, 0)) is centred horizontally and, vertically, in the free area below the strip (`area = height - strip`). Its radius in pixels is `0.5 * min(footprint.coverage * min(width, height), area)`: `size` is the share of the frame the form covers (`design.md:124`), limited to the free area. On a 520 px square window the limit applies from coverage 0.77 (`size` about 0.87) upwards; in a 1280x720 window from 0.83.
- All mass positions, radii, knot offsets and crack positions are drawn in footprint units scaled by that radius. Resizing the window rescales the whole composition and changes no proportion.

### Channels in `orbits`

Every field below comes from `VisualSpec`; the browser code computes nothing from traits or features.

| Channel | `VisualSpec` field | How `orbits` draws it |
|---|---|---|
| topology | `masses[i].x`, `y`, `radius` | one body per mass: a filled disc at its position |
| topology | `topology.nesting_levels` | that many concentric inner sub-discs per body at radius `1 - k / (levels + 1)` of the body, `k = 1..levels` |
| footprint | `footprint.coverage`, `element_count` | scale of the composition (above); `element_count` small dust points spread over the bodies in proportion to `file_share`, seeded positions |
| rings | `rings.thickness` | one growth ring per entry, oldest innermost, evenly spaced from the centre to the edge of every body; line width `0.5 + 3.5 * thickness` px; an empty list draws no rings |
| hue | `masses[i].hue`, `palette.hue_offset` | body fill `hsl(hue, saturation, 45%)` (`hue` already contains `palette.hue_offset`, added by `build_visual_spec`; the browser does not add it again); `hue = null` draws the body in neutral grey (saturation 0) |
| saturation | `palette.saturation` | HSL saturation of every body with a hue, of the rings and of the knot |
| strands | `strands.count`, `paths[j].phase`, `curvature` | one closed orbit per strand around the footprint centre, radius `0.55 + 0.4 * phase` footprint units, eccentricity `0.35 * abs(curvature)`, tilt `curvature * 90` degrees; each strand moves on its own phase |
| focal knot | `knot.mass_index`, `offset_x`, `offset_y`, `radius`, `flicker` | a bright disc on the owning body at the offset, radius `knot.radius * body radius`; `knot = null` draws no knot |
| edge quality | `edge.blur_px`, `edge.jitter` | body outline blurred by `blur_px` (canvas `shadowBlur`), outline vertices displaced by up to `jitter * body radius` with a seeded, frame-stable noise; `0` and `0` give a crisp circle |
| hatching | `hatching.coverage` | parallel thin lines clipped to each body, line spacing chosen so the lines cover `coverage` of the body area |
| cracks | `cracks.marks[k]` | a short jagged line on body `mass_index` at polar position (`u * radius`, `v * 360` degrees), direction `angle`, length `0.15` of the body radius |

- Background: a fixed dark ground `#121218` for every repository (O7), so saturation and hue are the only colour channels.
- Draw order, back to front: strands, bodies, nested sub-discs, rings, hatching, cracks, knot, dust.
- No mirrored or rotated copies of anything (`design.md:151`). Symmetry appears only when the data is balanced.

### Motion

- One loop of `motion.loop_seconds` (12 s) replays `motion.pulse`, oldest month first: at loop time `t` the global pulse amplitude is the pulse value of month `floor(t / loop_seconds * len(pulse))`; the bodies breathe by up to 4% of their radius times that value. The last 90 days of history (the last 3 monthly values of `pulse`) take the final 10% of the loop (`design.md:147`), so the formula applies to the earlier months over the first 90% of the loop; with 3 or fewer months it applies to the whole loop. An empty `pulse` gives a constant amplitude of 0.
- Drift speed of the dust and of the strands follows `motion.speed_hz` (`design.md:148`).
- The knot's brightness oscillates at `0.5 + 2.5 * knot.flicker` Hz (`design.md:149`).
- Strands move with their own phases, so more strands give more independent motion (`design.md:150`).
- All randomness in the page comes from one seeded generator (mulberry32) initialised with `seeds.effective_seed` modulo 2^32. Every frame is a pure function of the scene and the animation time, so the frozen 1.5 s clock of `tools/diversity_report.py` gives the same picture on every run.

### HUD and hover (O3, O4, O5)

- With `caption=True` the HUD shows the repository name and three plain conclusions: the three traits whose value is farthest from 0.5, ties broken by trait order (`size`, `age`, `alive`, `crowd`, `focus`, `care`, `sprawl`, `prose`, `debt`). Each conclusion is one phrase from the table below with a number from the raw features. The HUD no longer shows material, seed or engine version.
- Hovering a body shows its directory name (`.` for root files, `other (merged)` for the merged mass), its file count, its file share in percent and its top hotspot path if one of the top 3 hotspots belongs to it. The hover details are precomputed in Python, so the browser does not need features.
- With `caption=False` there is no HUD and no hover box; the drawing is identical.

| Trait | Low end (value < 0.5) | High end (value >= 0.5) |
|---|---|---|
| `size` | "small codebase ({code_kb} kB of code)" | "large codebase ({code_mb} MB of code)" |
| `age` | "young ({age_days} days of history)" | "{age_years} years old" |
| `alive` | "last commit {days} days ago" | "active: last commit {days} days ago" |
| `crowd` | "one main author ({top_share}%)" | "{authors} authors" |
| `focus` | "changes spread across the tree" | "changes concentrate in {top_hotspot}" |
| `care` | "few tests ({test_pct}% test files)" | "well tested ({test_pct}% test files)" |
| `sprawl` | "deep, narrow tree ({dirs} top-level directories, depth {depth})" | "wide, shallow tree ({dirs} top-level directories, depth {depth})" |
| `prose` | "mostly code" | "text-heavy ({doc_pct}% documents)" |
| `debt` | "few TODO markers" | "{todo} TODO markers per 1000 files" |

A repository with no top-level directory (`dirs` is 0, so the depth is 0 as well) has the `sprawl` phrase "flat tree, all files at the root" at either end, because the trait value 0.0 of such a tree is not "deep". The trait keeps its place in the ordering (it is not skipped), so the HUD still shows three conclusions.

Numbers are rounded to whole units, except `code_mb` and `age_years`, which have one decimal. A repository without history has no `age`, `alive` or `crowd` phrase; the next traits in the ordering take their place.

### Artifacts (O2)

`render --representation abstract --mode live` writes `live-preview.html`, `live-state.json` and `identity-seed.json`, the same file names as before. `live-state.json` now holds the `OrbitsScene` JSON, which contains the full `VisualSpec`; the HTML embeds the same JSON. The character mode keeps writing `LiveSimulationState`.

## Business rules

1. Determinism: the same features, reference time, identity seed and `caption` give byte-identical `live-state.json` and `live-preview.html`.
2. The page draws only from the embedded scene: no value in the Canvas code depends on the 14 axes, materiality or the emotional state.
3. Self-contained: the HTML has no external URL, script, stylesheet or font, and works from `file:///` (stage 4 criterion 1).
4. No silent fallback: a missing or wrong-type scene for the abstract representation is an error, never a switch to the old renderer. New code adds no `except` that hides errors.
5. Character mode unchanged: `--representation character` output is byte-identical to 0.9.0 apart from the engine version string. The character page loses only the unused abstract drawing code (`drawAbstract` and the mode dispatch), which Scope item 3 removes; its picture is unchanged.
6. HTML injection: repository and directory names are escaped in the HUD and hover, and the embedded JSON escapes `</` as today.

## Authorization

`none` - local library, CLI and development scripts with no authorization mechanism and no network.

## Data / API

```python
# src/gitgeist/schemas/live_state.py (frozen, extra="forbid")
class HoverDetail(BaseModel):
    mass_index: int            # index into scene.spec.masses
    label: str                 # ".", directory name, or "other (merged)"
    file_count: int
    file_share_percent: int
    top_hotspot: str | None

class OrbitsScene(BaseModel):
    schema_version: Literal["1"]
    representation: Literal["abstract"]
    repository_name: str | None
    engine_version: str        # current_engine_version()
    caption: bool
    conclusions: list[str]     # 0 to 3 phrases; [] when caption is False
    hover: list[HoverDetail]   # one per mass; [] when caption is False
    spec: VisualSpec           # representation "abstract", style "orbits"

# src/gitgeist/render/orbits.py
def build_orbits_scene(
    features: RepositoryFeatures,
    spec: VisualSpec,
    *,
    repository_name: str | None = None,
    caption: bool = True,
) -> OrbitsScene: ...

# src/gitgeist/render/facade.py (O1)
def render_live(
    profile: VisualLatentProfile,
    mode: Literal["abstract", "character"] = "abstract",
    repository_name: str | None = None,
    output_dir: Path | str | None = None,
    *,
    identity: IdentitySeed,
    scene: OrbitsScene | None = None,
) -> LiveRenderArtifacts: ...
```

- `mode="abstract"` requires `scene`; `mode="character"` requires `scene=None` in stage 4.
- `LiveRenderArtifacts.state` becomes `LiveSimulationState | OrbitsScene`.
- Removed: `gitgeist.render.abstract_renderer` and `generate_abstract_simulation` (breaking, CHANGELOG, R8).
- CLI: `gitgeist render <path> --representation abstract --mode live [--caption on|off]`.

## Compatibility and migration

- `live-state.json` for the abstract representation changes shape completely (from `LiveSimulationState` to `OrbitsScene`); readers of the old shape break. The character file does not change.
- `render_live(profile, "abstract", identity=...)` without `scene` raises `TypeError`; callers build the scene first. The CHANGELOG shows the three calls.
- `profile.json`, `summary.md`, `prompt.txt` and the image backends do not change.
- Version 0.10.0 (O9). New runtime dependencies: none.

## Effect on existing specs

- `docs/features/live-renderers/spec.md` (amended in Polish per R11): "Business rules / Tryb Abstract", the abstract parts of "Scope" and "Data / API" point to this spec; the character rules stay.
- `docs/features/traits-visualspec-seeds/visual-spec.md`: one sentence that stage 4 draws the abstract scene and writes it inside `live-state.json`.
- `README.md`: the live abstract output and the `--caption` flag.
- `docs/features/visual-diversity/plan.md`: stage 4 status "spec approved" in the spec PR, "done" after the implementation merge.
- `docs/product/emotional-repository-portrait-system.md`: unchanged; the artifact list keeps `live-state.json`.

## Edge cases

- No masses (no scanned files): no bodies, no knot, no cracks, no hover; strands and dust still draw inside the footprint so the page is not empty.
- One mass: one body at the centre plus jitter.
- No history: no rings, constant pulse 0, no `age`, `alive`, `crowd` conclusions.
- `knot = null`: no knot, the `focus` phrase uses "changes spread across the tree".
- Mass without language: neutral grey body.
- 40 rings on a small body: line width is capped so rings never overlap (`min(width, body radius / (rings + 1))`).
- Very small window (below 200 px): drawing still runs without NaN or division by zero.
- Directory names with HTML or quotes: escaped (business rule 6).
- Large portraits next to the HUD: the strip is reserved, so a portrait with coverage 0.85 in a 520 px window is drawn smaller (see Coordinates) instead of under the HUD. Edge jitter (up to 25% of a body radius) and breathing (4%) may let a body at the very edge of the footprint pass the circle by a few pixels.

## Errors

- `build_orbits_scene`: `spec.representation` not `abstract` or `spec.style` not `orbits`: `ValueError`; `features` not `RepositoryFeatures` or `spec` not `VisualSpec`: `TypeError`.
- `render_live`: `mode="abstract"` with `scene=None` or not an `OrbitsScene`: `TypeError`; `mode="character"` with a scene: `ValueError`; unknown mode: `ValueError` as today.
- CLI: `--caption` with `--mode prompt-to-image`: exit 2 with the message `--caption applies only to --mode live` before anything is analysed or written. (`--backend` with `--mode live` exits 1 through the generic error path; this flag exits 2 as written here.) `--caption` with `--representation character --mode live` is accepted and has no effect until stage 5.

## Acceptance criteria

1. The abstract `live-preview.html` is self-contained: no `http:`, `https:` or `//` URLs in `src`, `href` or `url()`, and it opens from `file:///` (plan criterion 1).
2. Contact sheet on the 12-repository corpus of `analysis.md`: nearest-neighbour median D v1 of the abstract live portraits at least 0.40 (plan criterion 2). The baseline is remeasured on the same corpus at `main` right before the implementation (`4fa14c9` or the branch point) and recorded next to the result in `docs/evidence/` with the command (R6, O6).
3. Tomasz's visual review of the abstract contact sheet and of two live pages of his choice (plan criterion 3).
4. Determinism, channel drawing and HUD tests below pass offline (R5) on Python 3.11, 3.12 and 3.13 in CI `verify` and in `verify-windows`.
5. Character live output is byte-identical to 0.9.0 apart from the engine version and the removed, unused abstract drawing code of the page template (business rule 5), checked by a test against a committed snapshot (`tests/golden/live/`). The state JSON is byte-identical.

## Required tests

- `tests/test_orbits_scene.py` (new): scene for the 8 golden fixtures; conclusions pick the three traits farthest from 0.5 with the tie order; phrase numbers from features (one expected phrase per trait end); no-history fixture drops `age`, `alive`, `crowd`; hover has one entry per mass with file counts and the top hotspot on the right mass; `caption=False` gives empty conclusions and hover; errors.
- `tests/test_live_renderers.py` (changed): `render_live` abstract with a scene writes the three files; `live-state.json` validates as `OrbitsScene`; determinism (byte-identical HTML and JSON on two runs); abstract without a scene raises `TypeError`; character with a scene raises `ValueError`; the old abstract tests that read `GeometryParameters` are removed.
- `tests/test_orbits_html.py` (new): the embedded JSON parses back to the scene; no external URL (criterion 1); names with `<`, `"` and `</script>` are escaped; the JS source contains no `rotate(` call inside a copy loop and reads no `geometry` or `symmetry_order` key (business rules 2, no rotated copies).
- `tests/test_cli.py` (changed): `render --representation abstract --mode live` writes an `OrbitsScene`; `--caption off` gives no HUD; `--caption` with `prompt-to-image` exits 2.
- `tests/golden/live/` (new): snapshot of the character `live-preview.html` and `live-state.json` of one fixture at 0.9.0 with the engine version masked (criterion 5).
- `tests/test_diversity_report.py` (changed): `run --no-images` on two fixtures still works with the new abstract path.

No test starts a browser; criterion 2 is checked by the development script with the log in the PR (`docs/evidence/stage-4-live-renderer-d.txt`). One test runs the drawing code in Node.js against a recording stub of the canvas and checks that no drawing call gets NaN or infinity for window sizes from 1 px to 1280x720; it is skipped when `node` is not installed.

## Risks

- D v1 at least 0.40 is not guaranteed: the Pillow mockup reached 0.743 (`design.md:434`), but the live canvas draws thinner marks and dust. If the first run misses, the drawing constants in "Channels in `orbits`" are tuned within this spec (R10) before any target change.
- The image check needs headless Chrome on the machine that runs `tools/diversity_report.py`. On the box it was refused by Auto-review in GITGEIST-12 (O6).
- Same-language repositories share a hue family (`design.md:438`); `--palette seeded` is stage 7.
- A canvas `shadowBlur` looks slightly different between browsers; D v1 is always measured in the same Chrome.

## Decisions

Decided by Tomasz on 2026-11-03: O1 (a), O2 (a), O3 (a), O4 (a), O5 (a), O6 (a, left to the implementer), O7 (a), O8 (a), O9 (a), O10 (b).

O1. Library API for the abstract scene. (a) `render_live` gets a keyword-only `scene: OrbitsScene | None`, required for `abstract`; `generate_abstract_simulation` is removed (breaking, CHANGELOG). (b) A new function `render_live_scene(scene, output_dir)` next to an unchanged `render_live`, which keeps the old abstract renderer for library callers. Recommendation: (a), one path and no dead renderer; (b) keeps code nobody uses.

O2. Artifact for the scene. (a) `live-state.json` holds `OrbitsScene` (with the full `VisualSpec`); file names stay as in the product document. (b) A new `visual-spec.json` next to a reduced `live-state.json` (the stage 3 O7 idea). Recommendation: (a), one file with one meaning and no change to the product artifact list.

O3. HUD conclusions. (a) The three traits farthest from 0.5 with the phrase table above. (b) Fixed three: age, crowd, alive (the `design.md:178` example). Recommendation: (a), it shows what is unusual about each repository.

O4. Where the hover data lives. (a) In `OrbitsScene.hover`, computed from features; `VisualSpec` and its `schema_version` stay unchanged. (b) Add `file_count` and `top_hotspot` to `SpecMass` (`schema_version` "2", stage 3 golden snapshots regenerated). Recommendation: (a), hover is HUD text, not a picture channel.

O5. `--caption` flag. (a) Add `--caption on|off` to `render` now, as `plan.md:79` lists it in stage 4. (b) Library keyword only; the flag comes with the others in stage 7. Recommendation: (a).

O6. Where the image check (criterion 2) runs. (a) On my computer with headless Chrome; if Auto-review refuses it again, I ask for its approval card, and if that is refused, we go to (b). (b) On your Windows PC with your Chrome: one approved command per run, with the 12 corpus clones copied there. Recommendation: (a), no work on your PC.

O7. Values the design does not give. (a) Accept: dark ground `#121218`, body lightness 45%, ring width 0.5 to 4 px, strand radius 0.55 to 0.95 footprint units, breathing 4% of radius, crack length 0.15 of radius, knot flicker 0.5 to 3 Hz, last 90 days in the final 10% of the loop. (b) Other values named by you. Recommendation: (a); they can be tuned within this spec if criterion 2 misses.

O8. `summary.md` section "Reading this portrait". (a) Stage 5, once both representations draw the channels, so the section is written once. (b) Now, for the abstract channels only. Recommendation: (a); `plan.md:73-85` does not list it for stage 4.

O9. Version. (a) 0.10.0: the abstract picture, the `live-state.json` shape and the public API change. (b) 1.0.0. Recommendation: (a); 1.0.0 is better kept for the end of the counter strategy (stage 8).

O10. Two PRs as in stage 3. (a) This spec in its own PR first, implementation in a second PR after you approve the spec. (b) Spec and implementation in one PR. Recommendation: (a).

## Relevant SDD / ADR

- `docs/features/visual-diversity/plan.md`, `docs/features/visual-diversity/design.md`, `docs/features/visual-diversity/analysis.md`
- `docs/features/traits-visualspec-seeds/spec.md`, `docs/features/traits-visualspec-seeds/visual-spec.md`
- `docs/features/live-renderers/spec.md`
- `docs/decisions/0001-trait-per-abstract-channel.md`
