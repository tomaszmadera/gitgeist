# Live renderer v2: character `creature`

Path: `docs/features/live-renderer-v2/character-spec.md`

Status: draft, waiting for Tomasz's decisions C1-C13 (stage 5 of `docs/features/visual-diversity/plan.md`, Plane GITGEIST-18). Written 2026-11-03 against `main` at `b2a99b2` (tag 0.10.0). Nothing is implemented.

This is a separate file next to the stage 4 spec, not a section of it. The stage 4 spec (`spec.md`) is closed and implemented in 0.10.0, its title and scope say "abstract `orbits`", and its decisions O1-O10 are decided; a stage 5 section in it would reopen a merged, approved document and mix two decision lists. The two specs form one family: this one reuses their coordinates, HUD, hover, motion and determinism rules by reference and only states what the `creature` style changes.

## Goal

Draw `VisualSpec` (stage 3) in the live character portrait. `gitgeist render --representation character --mode live` stops drawing the fixed diamond-shaped spine ladder with ribs and dots and draws the `creature` style instead: a body plan built from the directory masses (the largest mass is the torso, every other mass is a limb, limb segments come from depth), growth rings on the torso, the focal knot on the limb that owns the top hotspot, posture and speed by `alive` (`design.md` "Styles", `plan.md` stage 5). Every trait keeps its channel from stage 4; the style only changes what the channels are drawn as (`design.md:155`). After this stage both live representations draw `VisualSpec` and neither reads the 14 latent axes.

## Related requirements

- `docs/features/visual-diversity/plan.md` "Stage 5" (scope and acceptance criteria). Its reference to the spine template at `html_template.py:217-295` is out of date: at `b2a99b2` the spine, ribs and dots are drawn by `drawCharacter` in `generate_live_html` (`src/gitgeist/render/html_template.py:174-252`). The plan line is corrected when this stage merges.
- `docs/features/visual-diversity/design.md` "Visual grammar" (channels and ranges), "Composition and layout", "Motion grammar", "Styles" (`creature` draws masses as a body plan: torso is the largest mass, limbs are other masses, limb segments by depth), "Reading at a glance", "Testing diversity" (image check, target 0.25 for character).
- `docs/features/live-renderer-v2/spec.md` (stage 4): HUD strip, footprint scaling, motion loop, HUD conclusions and hover, mulberry32, determinism rules. This spec keeps them unless it says otherwise.
- `docs/features/traits-visualspec-seeds/spec.md` and `visual-spec.md` (the `VisualSpec` contract; `creature` is already registered with the fit rule "always").
- `docs/features/live-renderers/spec.md` (the character business rules it still holds are replaced, see "Effect on existing specs").
- `docs/decisions/0001-trait-per-abstract-channel.md` (one trait per channel; its ban on one trait to one prop still applies to the character items: the creature has no props, only the body plan, which comes from the directory structure and not from a trait).
- The gitgeist review rules outside the repository, `F:\projects\grok-bot\review\gitgeist\rules.md` (R5 offline tests, R8 CHANGELOG and specs for API changes, R10 plan criteria, R11 amendment language, R12 version bump).

## What stage 4 already provides

Stage 5 builds on these parts of 0.10.0 and does not redo them:

| Part | Where | Used by `creature` as |
|---|---|---|
| Scene schema pattern | `OrbitsScene`, `HoverDetail` in `src/gitgeist/schemas/live_state.py` | the pattern for `CreatureScene`; `HoverDetail` is reused unchanged |
| HUD text | `_conclusions`, `_hover` in `src/gitgeist/render/orbits.py` | the same three plain conclusions and hover texts (moved to a shared module, C10) |
| Scene API | `render_live(..., scene=)`, `LiveRenderArtifacts` in `render/facade.py` | extended to the character scene (C8) |
| Page | `generate_orbits_html`, the `_ORBITS_CSS` and `_ORBITS_JS` constants | the HUD and hover box, the HUD strip, the footprint scaling, the pulse replay, the knot flicker, the outline noise, mulberry32 seeded from `seeds.effective_seed` modulo 2^32 (shared code, C10) |
| CLI | `--caption on|off`, scene built in `command_render` | already accepted for `--representation character`; from this stage it has an effect |
| Scene data | `build_visual_spec(..., "character")`, style `creature` | masses, rings, palette, knot, strands, cracks, hatching, edge, topology, motion; golden snapshots `tests/golden/visual_spec/*-character.json` |
| Measurement | `tools/diversity_report.py run --chrome tools/chrome_warm_profile.sh` | the image check (needs a `character` branch in `_render_live`, Scope item 6) |

What `VisualSpec` does not provide and this stage adds: a body plan (where the torso and limbs are, how they bend). `VisualSpec` masses already carry packed circle positions, but those positions are made for `orbits` (non-overlapping discs); the creature needs connected parts (C2, C3).

## Scope

1. `src/gitgeist/render/creature.py` (new): `build_creature_scene(features, spec, *, repository_name=None, caption=True) -> CreatureScene`. It computes the body plan (below) and the HUD conclusions and hover details (shared text code, C10).
2. `src/gitgeist/schemas/live_state.py`: new frozen models `CreatureTorso`, `CreatureSegment`, `CreatureLimb`, `CreatureBody` and `CreatureScene` (schema below, C1, C2). `OrbitsScene` and `HoverDetail` do not change.
3. `src/gitgeist/render/html_template.py`: `generate_creature_html(scene)` with its own Canvas 2D code that draws only from the embedded `CreatureScene` JSON. The old `generate_live_html`, with the fixed spine, ribs, core nodes and ornament ring (`html_template.py:174-252`), is removed (C9).
4. `src/gitgeist/render/facade.py`: `render_live` takes a scene for both representations (C8). `generate_character_simulation`, `character_renderer.py`, `dynamics.py`, `palette.py` and the old live schemas are removed (C9).
5. CLI `gitgeist render --representation character --mode live`: builds `compute_traits(features)`, `build_visual_spec(features, traits, identity, "character")`, the creature scene, and writes the three artifacts as before. `--caption` now works for character.
6. `tools/diversity_report.py`: `_render_live` builds the creature scene for the character render; D v1 is unchanged so the numbers stay comparable with the baseline (`docs/evidence/stage-5-baseline-character-d.txt`).
7. Version and `CHANGELOG.md` entry (C12), README, and the specs listed in "Effect on existing specs".

## Non-goals

- Prompt-to-image: the character prompt still comes from the 14 axes until stage 6 (prompt composer v2). `summary.md` and `profile.json` keep their content; the 14 axes stay in `profile.json`.
- `--style`, `--seed`, `--variety`, `--scale`, `--palette` flags: stage 7. The CLI uses the stage 3 defaults (`style="auto"`, which resolves to `creature`, no user seed, `variety="medium"`, scale `absolute`, palette `language`).
- Other character styles (`tree`, `colony`, `totem`): stage 8.
- Changes to traits, `VisualSpec` fields or its `schema_version` (C2).
- The `summary.md` section "Reading this portrait" (stage 4 spec O8 moved it to this stage): it is a separate item, not part of this spec; it needs its own decision once both pictures are accepted, and is listed in "Open items outside this spec".
- Pixel metrics in tests (`design.md:416`).
- Any change to the `orbits` page, the abstract scene or the abstract artifacts (business rule 5).

## Behaviour

### Coordinates, HUD and scaling

Identical to the stage 4 spec ("Coordinates", "HUD and hover"): a strip of `HUD_STRIP = 120` px at the top (30% of the height in windows lower than 400 px), the footprint circle (radius 1 at (0, 0)) centred in the free area below it, pixel radius `0.5 * min(footprint.coverage * min(width, height), area)`, everything drawn in footprint units scaled by that radius. The body plan below is normalised so that the creature, including the reach of its tendrils at rest, fits inside the footprint circle (extent 1), so `coverage` means the same thing as in `orbits`.

### Body plan

Computed in Python from `VisualSpec` by `build_creature_scene` (C2), written into `CreatureScene.body`, drawn by the page. No value in the page depends on traits or features. The numbers below are the constants of C11 and are tuned within this spec if the image check misses (R10).

Inputs: `spec.masses` (file share `s`, churn share `c`), `spec.topology.nesting_levels`, `spec.traits.alive`, `spec.seeds.effective_seed`. Random numbers come from `Random(sub_seed(effective_seed, "body"))`; the new label `"body"` is an independent stream, so no existing stream (layout, hue, strands, cracks) changes.

1. Torso: the mass with the largest file share (the lowest index on ties). It is an ellipse at the centre. Its minor semi-axis is `R = sqrt(s_torso)`, its major semi-axis is `1.2 * R` (C7), its major axis points along a body axis angle `beta`, the first value drawn from the body stream (uniform, 0 to 360 degrees). The torso carries the growth rings.
2. Limbs: every other mass, in the factual order of `spec.masses` (file share descending, the merged mass last), rank `k = 0, 1, ...`. A repository with one mass has no limbs; with 8 masses it has 7.
3. Attachment (C3): limb `k` leaves the torso outline in the direction `beta + 90 + k * 137.508` degrees (the golden angle of the stage 3 packing), so limbs fan around the torso without repeating, and an even-looking creature appears only when the shares are even.
4. Limb size (C4): the pad (the round end of the limb, which is the mass's body) has radius `rho = R * max(0.12, 0.8 * sqrt(s / s_torso))`. The reach of the limb (root to pad centre) is `R * (0.8 + 1.6 * sqrt(c))`, `c` being the mass's churn share: directories where change happens reach farther.
5. Segments (C5): each limb has `1 + topology.nesting_levels` segments (1 to 4) of equal length. Half-width tapers from `0.5 * rho` at the root to `0.3 * rho` at the last joint.
6. Posture by `alive` (C6): each joint bends by `sign * (10 + 60 * (1 - alive))` degrees plus a seeded offset of up to 8 degrees. `sign` is `+1` or `-1`, drawn per limb from the body stream. An active repository (`alive` near 1) has nearly straight, extended limbs; a dormant one (`alive` near 0) has tightly curled limbs. The sway of each joint at loop time `t` is `A * sin(2 * pi * speed_hz * t + phase + 0.6 * j)` degrees, with `A = 2 + 10 * alive`, `phase` seeded per limb and `speed_hz = spec.motion.speed_hz` (0.05 to 1.2, by `alive`), so a dormant creature barely moves.
7. Fit: the rest pose (no sway, no breathing) is centred on the middle of its bounding box and scaled so that the farthest point of any part, or of a tendril tip, is at distance 1 from the origin.

`CreatureScene.body` stores the result (C2): the torso (centre, semi-axes, rotation, mass index) and for each limb the mass index, root point, root direction, the segments (length, half-width, bend), the pad radius, the sway phase and the sway amplitude. The page integrates the chain from the root (forward kinematics: each segment starts where the previous one ends, turned by its bend plus its sway).

### Channels in `creature`

| Channel | `VisualSpec` field | How `creature` draws it |
|---|---|---|
| topology | `masses[i]`, `topology.nesting_levels` | the body plan above: one part per mass; limb segments from `nesting_levels` (C5) |
| footprint | `footprint.coverage`, `element_count` | scale of the composition; `element_count` small motes spread over the parts in proportion to `file_share` (limb motes sit on its segments and pad), seeded positions, drifting inside their part |
| rings | `rings.thickness` | one growth ring per entry, oldest innermost, as concentric copies of the torso ellipse from the centre to its edge; line width `0.5 + 3.5 * thickness` px, capped at `min(width, torso minor radius / (rings + 1))`; the limbs have no rings; an empty list draws none |
| hue | `masses[i].hue` | torso and pad fill `hsl(hue, saturation, 45%)`, limb segments the same hue at 38% lightness; `hue = null` draws the part in neutral grey |
| saturation | `palette.saturation` | HSL saturation of every part with a hue, of the rings and of the knot |
| strands | `strands.count`, `paths[j]` | tendrils (C6a): thin curved lines growing outward from the torso outline at the polar angle `phase * 360` degrees (torso frame), length `0.12 + 0.18 * abs(curvature)` footprint units, bent by `curvature * 60` degrees, waving with their own phase; more strands, more independent motion |
| focal knot | `knot` | a bright disc on the part that owns `knot.mass_index`: the pad of that limb (the hotspot limb), or the torso when the torso owns the hotspot; offset `knot.offset / mass.radius` of the part radius (the torso minor radius or the pad radius), radius `knot.radius * part radius`, flicker as in `orbits`; `knot = null` draws none |
| edge quality | `edge.blur_px`, `edge.jitter` | outline of every part blurred by `blur_px`, outline vertices displaced by up to `jitter * part radius` with the stage 4 seeded, frame-stable noise |
| hatching | `hatching.coverage` | parallel thin lines clipped to the torso and to every segment and pad, spacing chosen so the lines cover `coverage` of the part area |
| cracks | `cracks.marks[k]` | a short jagged line on the part of `mass_index` (the torso, or the pad of that limb) at polar position (`u * part radius`, `v * 360` degrees), direction `angle`, length `0.15` of the part radius |

- Background: the fixed dark ground `#121218` of `orbits` (C11).
- Draw order, back to front: tendrils, limb segments (root to tip, limb by limb), torso, pads, rings, hatching, cracks, knot, motes.
- No mirrored or rotated copies, no fixed spine (`design.md:135` and `:151`). Bilateral symmetry appears only when the data is balanced.

### Motion

As in stage 4 ("Motion"): one loop of `motion.loop_seconds` (12 s) replays `motion.pulse` (the last 90 days take the final 10% of the loop); the torso and the pads breathe by up to 4% of their size times the pulse; the knot flickers at `0.5 + 2.5 * flicker` Hz; strands move on their own phases. Additionally the limbs sway as in body plan item 6, so `alive` shows as posture (curl) and as speed (sway frequency and amplitude). All randomness in the page comes from mulberry32 seeded with `seeds.effective_seed` modulo 2^32; every frame is a pure function of the scene and the animation time, so the frozen 1.5 s clock of `tools/diversity_report.py` gives the same picture on every run.

### HUD and hover

Same rules and texts as stage 4 (three traits farthest from 0.5, the phrase table, no material, seed or engine version). Hovering a part (the torso, or any segment or pad of a limb) shows the directory of its mass (`.` for root files, `other (merged)` for the merged mass), its file count, its file share and its top hotspot, from `CreatureScene.hover` (one entry per mass, indexed like `spec.masses`). With `caption=False` there is no HUD and no hover box; the drawing is identical.

### Artifacts

`render --representation character --mode live` writes `live-preview.html`, `live-state.json` and `identity-seed.json`, the same file names as before. `live-state.json` now holds the `CreatureScene` JSON (the full `VisualSpec`, the body plan, conclusions and hover); the HTML embeds the same JSON.

## Business rules

1. Determinism: the same features, reference time, identity seed and `caption` give byte-identical `live-state.json` and `live-preview.html`.
2. The page draws only from the embedded scene: no value in the Canvas code depends on the 14 axes, materiality, the emotional state, or the old `geometry`, `dynamics` and `palette` objects. The page source has no spine, rib or `symmetry_order` code.
3. Self-contained: no external URL, script, stylesheet or font; works from `file:///`.
4. No silent fallback: a missing or wrong-type scene is an error, never a switch to the removed renderer. New code adds no `except` that hides errors.
5. Abstract mode unchanged: `--representation abstract` output (page and `live-state.json`) is byte-identical to 0.10.0 apart from the engine version string. This holds even if code is shared with the `creature` page (C10), and a committed 0.10.0 snapshot test guards it.
6. HTML injection: repository and directory names are escaped in the HUD and hover, and the embedded JSON escapes `</`.
7. The body plan is data, not decoration: every part of the creature maps to one mass (or, for tendrils and motes, to a spec field); the page adds no part that has no source in the scene.

## Authorization

`none` - local library, CLI and development scripts with no authorization mechanism and no network.

## Data / API

```python
# src/gitgeist/schemas/live_state.py (frozen, extra="forbid")
class CreatureTorso(BaseModel):
    mass_index: int            # index into scene.spec.masses
    x: float; y: float         # centre, footprint units
    rx: float; ry: float       # semi-axes, rx >= ry
    rotation_deg: float        # direction of the major axis

class CreatureSegment(BaseModel):
    length: float
    half_width: float
    bend_deg: float            # joint bend at the segment's start, at rest

class CreatureLimb(BaseModel):
    mass_index: int
    root_x: float; root_y: float
    root_angle_deg: float      # direction of the first segment, world frame
    segments: list[CreatureSegment]   # 1 to 4
    pad_radius: float
    sway_phase: float          # [0, 1)
    sway_amplitude_deg: float

class CreatureBody(BaseModel):
    torso: CreatureTorso | None       # None when there are no masses
    limbs: list[CreatureLimb]         # one per mass except the torso's

class CreatureScene(BaseModel):
    schema_version: Literal["1"]
    representation: Literal["character"]
    repository_name: str | None
    engine_version: str        # current_engine_version()
    caption: bool
    conclusions: list[str]     # 0 to 3 phrases; [] when caption is False
    hover: list[HoverDetail]   # one per mass; [] when caption is False
    body: CreatureBody
    spec: VisualSpec           # representation "character", style "creature"

# src/gitgeist/render/creature.py
def build_creature_scene(
    features: RepositoryFeatures,
    spec: VisualSpec,
    *,
    repository_name: str | None = None,
    caption: bool = True,
) -> CreatureScene: ...

# src/gitgeist/render/facade.py (C8, recommended option)
def render_live(
    scene: OrbitsScene | CreatureScene,
    output_dir: Path | str | None = None,
    *,
    identity: IdentitySeed,
) -> LiveRenderArtifacts: ...
```

Validators on `CreatureScene`: every index of `spec.masses` appears exactly once in `body` (the torso or one limb); a limb has 1 to 4 segments, equal to `1 + spec.topology.nesting_levels`; `body.torso` is `None` only when `spec.masses` is empty; the farthest point of the rest pose is at most `1 + 1e-9` from the origin.

## Compatibility and migration

- `live-state.json` for the character representation changes shape completely (from `LiveSimulationState` to `CreatureScene`); readers of the old shape break. The abstract file does not change.
- With the recommended C8 and C9 the public functions and models `generate_character_simulation`, `generate_live_html`, `generate_palette`, `generate_dynamics`, `LiveSimulationState`, `ColorPalette`, `MotionDynamics`, `GeometryParameters` and the `profile`, `mode` and `repository_name` parameters of `render_live` disappear (they are also exported from `gitgeist.render` and `gitgeist.schemas`). The CHANGELOG shows the calls before and after.
- `profile.json`, `summary.md`, `prompt.txt` and the image backends do not change.
- New runtime dependencies: none.

## Effect on existing specs

- `docs/features/live-renderers/spec.md` (amended in Polish per R11): the character rules ("Tryb Character") and the remaining parts of "Scope" and "Data / API" point to this spec; the spec then describes only the contract of `render_live` and the artifact names.
- `docs/features/live-renderer-v2/spec.md`: one sentence in its status and non-goals that stage 5 is `character-spec.md`; no change to its decisions.
- `docs/features/traits-visualspec-seeds/visual-spec.md`: one sentence that stage 5 draws the character scene.
- `docs/features/visual-diversity/plan.md`: stage 5 status "spec approved" in the spec PR and "done" after the implementation merge; the reference `html_template.py:217-295` corrected to the removed `drawCharacter`; `design.md:135` mentions `html_template.py:248` (the spine profile) and gets the same note.
- `docs/features/visual-diversity/analysis.md`: unchanged (it records the state at `03741e1`).
- `README.md`: the character live output and the `--caption` flag.
- `tests/golden/live/` (0.9.0 character snapshot): replaced (C9, see "Required tests").

## Edge cases

- One mass (3 of the 12 corpus repositories): a torso with no limbs, rings, tendrils, motes, knot and cracks on it.
- No masses (no scanned files): `body.torso` is `None`; no parts, no knot, no cracks, no hover; tendrils (growing from a small circle of radius 0.2 at the centre) and motes still draw so the page is not empty.
- A mass with `file_share` 0 (a directory with only empty files): pad radius at the minimum `0.12 * R`; a limb never vanishes.
- No history: no rings, constant pulse 0, no `age`, `alive`, `crowd` conclusions (stage 4 rule); `alive` is whatever the traits give (the trait rules are unchanged), so posture and speed still follow it.
- `knot = null`: no knot; the `focus` phrase uses "changes spread across the tree".
- Knot on the torso (the torso owns the top hotspot): knot inside the torso at the knot offset.
- Mass without language: neutral grey part.
- Several limbs of similar size: the fan looks regular, which is intended (data-balanced).
- 40 rings on a small torso: width capped so rings never overlap.
- Very small window (below 200 px): drawing still runs without NaN or division by zero.
- Directory names with HTML or quotes: escaped (business rule 6).
- Large portraits next to the HUD: same rule as stage 4 (the radius is capped by the free area). Sway (up to 12 degrees per joint, compounding along a limb), breathing and edge jitter may let the end of a limb pass the footprint circle by a few percent.

## Errors

- `build_creature_scene`: `spec.representation` not `character` or `spec.style` not `creature`: `ValueError`; `features` not `RepositoryFeatures` or `spec` not `VisualSpec`: `TypeError`; `spec.masses` not matching `features.structure.masses`: `ValueError`.
- `render_live` (C8 recommended): `scene` not an `OrbitsScene` or `CreatureScene`: `TypeError`; `identity` not an `IdentitySeed`: `TypeError`.
- `generate_creature_html`: `scene` not a `CreatureScene`: `TypeError`.
- CLI: unchanged (`--caption` with `--mode prompt-to-image` exits 2).

## Acceptance criteria

1. The character `live-preview.html` is self-contained: no `http:`, `https:` or `//` URLs in `src`, `href` or `url()`, and it opens from `file:///` (plan criterion 1).
2. Contact sheet on the 12-repository corpus of `analysis.md`: nearest-neighbour median D v1 of the character live portraits at least 0.25 (plan criterion 2), and `gitgeist` and `NeKode` are not the closest pair. The baseline 0.091 (closest pair gitgeist / NeKode, 0.039) is reproduced in `docs/evidence/stage-5-baseline-character-d.txt` at `b2a99b2`; the implementation run is remeasured the same way on the same 12 clones and recorded in `docs/evidence/` with the command (R6). The abstract median must stay at 0.409 (the abstract pages are byte-identical, business rule 5).
3. Tomasz's visual review of the character contact sheet and of two live pages of his choice (plan criterion 3).
4. Determinism, channel drawing, body plan and HUD tests below pass offline (R5) on Python 3.11, 3.12 and 3.13 in CI `verify` and in `verify-windows`.
5. Abstract live output is byte-identical to 0.10.0 apart from the engine version, checked by a test against a committed snapshot (`tests/golden/live/`, created from 0.10.0 before any shared code is moved, C10).
6. The old spine code is gone: the character page contains no `spineSegments`, `symmetry_order`, `geometry` or `dynamics` key (checked by a test on the page source).

## Required tests

- `tests/test_creature_body.py` (new): the torso is the mass with the largest file share (ties: lowest index); one limb per other mass; limb segments equal `1 + nesting_levels`; pad radius and reach follow the formulas (a mass with a larger churn share reaches farther); posture is monotone in `alive` (the absolute joint bend falls as `alive` rises); two repositories with the same masses and different identity seeds differ in `beta` and in limb angles; the rest pose fits the unit circle for the 8 golden fixtures; one mass gives no limbs; no masses gives `torso=None`; `sub_seed(.., "body")` does not change the layout, hue, strands or cracks streams (the stage 3 golden snapshots stay identical); determinism.
- `tests/test_creature_scene.py` (new): scene for the 8 golden fixtures; validators (every mass once, segment count, extent); conclusions and hover identical to the ones `build_orbits_scene` gives for the same features and traits (shared code); `caption=False` gives empty conclusions and hover; errors.
- `tests/test_creature_html.py` (new): the embedded JSON parses back to the scene; no external URL; names with `<`, `"` and `</script>` are escaped; the JS source contains no `rotate(` call inside a copy loop and none of the removed keys (criterion 6).
- `tests/test_live_renderers.py` (changed): `render_live` with a creature scene writes the three files; `live-state.json` validates as `CreatureScene`; byte-identical output on two runs; wrong scene type raises `TypeError`; abstract output equals the 0.10.0 snapshot; the tests of the removed character generator are removed.
- `tests/test_live_state_schemas.py` (changed): the old schema tests are removed (C9) and replaced by the scene models.
- `tests/test_cli.py` (changed): `render --representation character --mode live` writes a `CreatureScene`; `--caption off` gives no HUD.
- `tests/golden/live/` (replaced): a snapshot of the abstract live page and `live-state.json` of one fixture at 0.10.0 with the engine version masked (criterion 5), and the committed `CreatureScene` JSON of the same fixture as a regression anchor.
- `tests/test_diversity_report.py` (changed): `run --no-images` on two fixtures still works with the creature path.

No test starts a browser; criterion 2 is checked by the development script with the log in the PR. The existing Node.js check of the drawing code (recording canvas stub, no NaN or infinity for window sizes from 1 px to 1280x720) is extended to the creature page and is skipped when `node` is not installed.

## Risks

- D v1 at least 0.25 is not guaranteed. The old picture scored 0.091 because it was the same ladder for everybody; the creature differs by silhouette (seeded `beta`, the fan of limbs, reach by churn), hue per mass, saturation, rings and cracks, but three corpus repositories have one mass (`is-odd`, `z`, `fresh`) and look like a single ellipse with different hue, size and orientation; `is-odd` and `fresh` are already the closest abstract pair (0.019) and may become the closest creature pair. The acceptance accepts that pair; only gitgeist / NeKode must not be the closest. If the first run misses, the drawing constants (C11) are tuned within this spec (R10) before any target change.
- gitgeist and NeKode are both fully alive (alive 1.00), with one strand and one ring; they differ in mass shares (.43/.27/.19 against .68/.22/.04), size, cracks and hues, so the body plan has to carry the difference. Their separation is the second acceptance condition and the first thing to check in the contact sheet.
- Depth as segments: `nesting_levels` is `round(3 * sprawl)` and `sprawl` is a breadth share since 0.9.0 (stage 3 spec O14), so a branched, wide tree gets more segments and a deep narrow tree fewer; the corpus has 1 to 3 segments per limb. The reading "more segments means a more branched tree" holds; "more segments means a deeper tree" does not. C5 offers a per-mass depth if this reading is not acceptable.
- The image check needs headless Chrome on the machine that runs `tools/diversity_report.py`; on the box it works through `tools/chrome_warm_profile.sh` (stage 4 evidence).
- Canvas `shadowBlur` looks slightly different between browsers; D v1 is always measured in the same Chrome.

## Decisions

Open. Tomasz decides C1-C13 one at a time; the recommended option is first and marked.

C1. Scene schema for the character page. (a) **Recommended:** a new `CreatureScene` next to `OrbitsScene`; `HoverDetail` is shared; `OrbitsScene` does not change. (b) One `PortraitScene` for both representations, with an optional `body`; the orbits JSON changes shape again. Reason: (a) keeps the abstract artifact byte-identical (business rule 5) and each scene validates exactly what its page draws; (b) churns a 0.10.0 file for no gain.

C2. Where the body plan is computed. (a) **Recommended:** in Python by `build_creature_scene` and stored in `CreatureScene.body`; `VisualSpec` and its `schema_version` do not change. (b) In the browser from `VisualSpec`, as `orbits` places its bodies. (c) As new optional fields in `VisualSpec` for the `creature` style (`schema_version` "2", the stage 3 golden snapshots regenerated, a stage 3 amendment). Reason: (a) is tested offline without a browser (R5), is visible in `live-state.json`, and stage 6 can import the same builder for the prompt ("a torso with five limbs"); (b) cannot be unit-tested without Node; (c) changes a merged contract.

C3. How limbs attach to the torso. (a) **Recommended:** a golden-angle fan around the torso from a seeded body axis (limb `k` leaves at `beta + 90 + 137.508 k` degrees). (b) Bilateral pairs along a spine: limbs of rank 1 and 2 on the left and right of the torso, rank 3 and 4 below, and so on, so a balanced repository looks symmetric. (c) Reuse the packed circle positions of `VisualSpec` as limb ends and connect them to the torso. Reason: (a) gives a different silhouette for every repository, which is what D v1 measures and what the old ladder lacked; (b) reads more like an animal but gives every repository the same upright shape, close to the template being removed; (c) needs no new layout but the packed masses are tangent circles around a centre, so the limbs come out short and the creature reads as a cluster of discs.

C4. What sets limb thickness and reach. (a) **Recommended:** thickness from the mass's file share (pad radius), reach from its churn share (directories where change happens reach farther). (b) Both from the file share (a big directory is a big, long limb). (c) Reach by rank only (the largest limb is the longest), independent of the data beyond the order. Reason: (a) uses two factual shares so limbs of the same size can still differ, which adds silhouette variety; (b) is simpler to read but duplicates information; (c) is flat.

C5. Where limb segments come from ("depth as segments"). (a) **Recommended:** `1 + topology.nesting_levels` for every limb (1 to 4); no change to features or `VisualSpec`. (b) A per-directory depth for each limb: a new `max_depth` field on `Mass` in features v2 (a stage 2 amendment, normalization and golden regeneration, `VisualSpec` unchanged apart from reading it) so every limb has its own number of segments. Reason: (a) reuses the topology channel of stage 3 and stage 4 (`nesting_levels`), but it is a breadth-based trait since 0.9.0, so it reads "branched", not "deep" (see Risks); (b) is the literal reading of the plan but reopens two merged stages.

C6. How strands (crowd) are drawn in the creature. (a) **Recommended:** tendrils, thin waving lines growing outward from the torso outline, one per strand, each with its own phase. (b) Orbits: closed loops around the whole creature, as in `orbits`. (c) Threads between the pads of neighbouring limbs, like a web. Reason: (a) reads as part of the creature and stays inside the fit; (b) would make the two styles share a motif and add little to the silhouette; (c) is meaningless for one or two limbs (the web is empty for single-mass repositories).

C7. Posture by `alive`. (a) **Recommended:** limb curl (a dormant creature has tightly curled limbs, an active one has extended, nearly straight limbs) with a fixed torso elongation 1.2, plus sway amplitude and frequency by `alive`. (b) Curl as in (a) and the torso elongation also follows `alive` (round and squat when dormant, long when active: `1 + 0.4 * alive`). (c) Sway speed only (no curl). Reason: (a) is readable at a glance in a still picture, the D check uses a frozen frame, and the torso keeps a stable shape; (b) adds a second signal for the same trait; (c) is invisible in the frozen frame and does not meet the plan ("posture and speed by `alive`").

C8. The `render_live` API after both representations draw scenes. (a) **Recommended:** `render_live(scene, output_dir=None, *, identity)`; the representation comes from the scene type; the `profile`, `mode` and `repository_name` parameters are removed (breaking, CHANGELOG with the calls). (b) Keep `render_live(profile, mode, repository_name, output_dir, *, identity, scene)` with `scene` required for both modes; `profile` stays in the signature, type-checked and unused. Reason: (a) removes a parameter that would be dead and a mode that could contradict the scene (the same reasoning as stage 4 O1); (b) is the smaller break but keeps a misleading argument.

C9. The old character code. (a) **Recommended:** remove `generate_character_simulation`, `character_renderer.py`, `dynamics.py`, `palette.py`, `generate_live_html` and the models `LiveSimulationState`, `ColorPalette`, `MotionDynamics`, `GeometryParameters` (breaking, CHANGELOG), and replace the 0.9.0 character snapshot in `tests/golden/live/` by the abstract 0.10.0 snapshot. (b) Keep them for library callers, marked deprecated, until 1.0. Reason: (a) one path and no dead renderer, nothing in the package would call them (the same decision as stage 4 O1); (b) keeps about 400 lines and their tests for nobody.

C10. Code shared with the `orbits` page. (a) **Recommended:** move what both pages need (CSS, HUD and hover box, mulberry32, pulse replay, outline noise, colour helpers on the page side; `_conclusions` and `_hover` on the Python side, into a shared module) out of the orbits code, guarded by a committed 0.10.0 snapshot test that the abstract page and JSON stay byte-identical (business rule 5, criterion 5). (b) Copy what the creature needs into the creature page and `creature.py`; `orbits` is not touched. Reason: (a) means one HUD and one set of text rules for both pictures (a fix lands once), at the price of one refactor guarded by a byte-identical check; (b) has no risk for the abstract page but duplicates about 150 lines of page code and the phrase table.

C11. Drawing values the design does not give. (a) **Recommended:** accept: ground `#121218` as in `orbits`; torso elongation 1.2; pad radius `R * max(0.12, 0.8 * sqrt(s / s_torso))`; reach `R * (0.8 + 1.6 * sqrt(c))`; segment half-width `0.5 rho` to `0.3 rho`; joint bend `10 + 60 * (1 - alive)` degrees with up to 8 degrees seeded offset; sway `2 + 10 * alive` degrees; segment lightness 38% and torso and pad lightness 45%; tendril length `0.12 + 0.18 * abs(curvature)` and bend `60 * curvature` degrees; breathing 4%; crack length 0.15 of the part radius; the rest of the `orbits` values (ring width 0.5 to 4 px, knot flicker 0.5 to 3 Hz, last 90 days in the final 10% of the loop). (b) Other values named by you. Reason: (a); they can be tuned within this spec if criterion 2 misses, and the first measurement tells which ones to change.

C12. Version. (a) **Recommended:** 0.11.0: the character picture, the `live-state.json` shape and the `render_live` API change. (b) 1.0.0. Reason: (a); 1.0.0 is better kept for the end of the counter strategy (stage 8), as decided in stage 4 O9.

C13. One PR or two. (a) **Recommended:** spec and implementation in one PR, as in stage 4 (stage 4 O10 (b)). (b) The spec in its own PR first and the implementation in a second PR after you approve it, as in stage 3. Reason: (a) is the family approach you chose for stage 4 and the decisions above are visible in the same review; (b) is safer if you expect to change several decisions after seeing the first picture, but costs a second review round.

## Open items outside this spec

- The `summary.md` section "Reading this portrait" (stage 4 spec O8 deferred it to stage 5, once both pictures draw the channels). It needs its own decision (one section for both representations, with the channel-to-trait mapping of `orbits` and `creature`); the options will be offered after this spec's decisions, not mixed into them.

## Relevant SDD / ADR

- `docs/features/visual-diversity/plan.md`, `docs/features/visual-diversity/design.md`, `docs/features/visual-diversity/analysis.md`
- `docs/features/live-renderer-v2/spec.md`
- `docs/features/traits-visualspec-seeds/spec.md`, `docs/features/traits-visualspec-seeds/visual-spec.md`
- `docs/features/live-renderers/spec.md`
- `docs/decisions/0001-trait-per-abstract-channel.md`
- `docs/evidence/stage-5-baseline-character-d.txt`
