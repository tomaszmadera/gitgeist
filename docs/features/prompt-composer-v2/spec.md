# Prompt composer v2

Path: `docs/features/prompt-composer-v2/spec.md`

Status: approved by Tomasz on 2026-11-05 (stage 6 of `docs/features/visual-diversity/plan.md`, Plane GITGEIST-19). Caption default is on. The behaviour below is the contract, including the sentence templates and the 0.33/0.66 cutoff.

## Goal

`gitgeist render --mode prompt-to-image` describes the repository's `VisualSpec` in a short prompt and draws a portrait from it. The prompt names visible facts (bodies, placement, palette, medium). It does not list trait scores. With the caption on, Pillow adds the same three conclusions the live HUD uses, under the picture. The audience of this contract is the implementer of that mode. Target version: 0.12.0.

## Related requirements

- `docs/features/visual-diversity/plan.md:100-112` (stage 6 scope and acceptance).
- `docs/features/visual-diversity/design.md:182-208` ("Prompt-to-image": shape, name off by default, fake raster, caption strip).
- `docs/features/visual-diversity/design.md:123-132` (channel readings: vivid or faded, crisp or frayed).
- `docs/features/visual-diversity/design.md:391-408` (CLI table; `--caption` default `on`, `--prompt-name` default off).
- `docs/features/visual-diversity/analysis.md:40` (the 12-repository corpus for the dev check).
- `docs/features/prompt-to-image/spec.md` (media sniffing, OpenRouter errors, `image_format`, artifact names; the composer rules in that file are not this contract).
- `docs/features/traits-visualspec-seeds/spec.md` and `visual-spec.md` (`VisualSpec`, unchanged by this stage).
- `src/gitgeist/schemas/traits.py:10` (`TRAIT_NAMES`).
- `src/gitgeist/render/captions.py:71` (`conclusions`).
- `src/gitgeist/render/page_common.py:86` and `src/gitgeist/render/html_template.py:19` (saturation rounding and lightness 45).
- `src/gitgeist/render/html_template.py:133` (positive y is down).
- `src/gitgeist/render/image_backend.py:125-126` (current JSON body) and `:169` (`encode_png`).
- OpenRouter images API, checked 2026-11-04: `https://openrouter.ai/docs/api/api-reference/images/generate-an-image`. An integer `seed` is accepted. Provider determinism is not guaranteed. Do not call the API to re-check this.

## Scope

1. `compose_prompt(spec, *, include_name=False, repository_name=None) -> str` in `src/gitgeist/render/prompt_composer.py`. It replaces the `EmotionalState` and `VisualLatentProfile` parameters. There is no second function beside it.
2. `render_prompt(spec, *, features, repository_name=None, include_name=False, caption=True, backend=None, output_dir=None, image_format="native")` in `src/gitgeist/render/facade.py`. Same replacement. `PromptRenderArtifacts` keeps its fields.
3. `ImageGenerationBackend.generate_image(prompt, *, spec=None, seed=None)`. `OpenRouterImageBackend` adds `seed` to the existing JSON body when `seed` is not `None`. `FakeImageBackend` draws a 64x64 RGB PNG of the spec through `encode_png`.
4. CLI: `--caption on|off` is valid for `--mode prompt-to-image`. `--prompt-name` is a flag on `render`, default off, valid only for that mode.
5. A dev script that logs whether any non-fixed prompt line repeats across the 12-repository corpus. The log goes under `docs/evidence/`. The script is not part of CI.
6. Version 0.12.0, a CHANGELOG entry, and the README lines for the two flags, in the implementation that follows approval.

## Non-goals

- The paid 12-repository A/B run (plan stage 6, acceptance 2). It stays out until a separate approval.
- `--style`, `--seed`, `--variety`, `--scale`, `--palette`, and the config file. Stage 7 owns them.
- Styles other than `orbits` and `creature`. An unknown `spec.style` is an error, not a fallback.
- `jev-real-integration`.
- Changes to `profile.json`, `summary.md`, live artifacts, `VisualSpec` fields, or `schema_version`.
- Cloning or fetching the corpus.
- Rewriting the stage 4 and stage 5 status lines in `docs/features/visual-diversity/plan.md`.
- A version bump in the spec-only change. 0.12.0 is the implementation version.

## Behaviour

### Prompt text

`compose_prompt` reads `spec` and the two keyword arguments. Identical inputs return identical text. The result has no blank line. Each line is non-empty. The last line ends with a single `\n`.

Line order:

1. Subject sentence.
2. `Repository: {repository_name}.` only when `include_name` is true.
3. Five to seven directive lines, each starting with `- ` (hyphen, space), in `TRAIT_NAMES` order.
4. `Palette: {hexes} on #121218.`
5. `Medium: {name}.`
6. `No text, no letters, no logos, no code, no screens, no mascots.`
7. `No watermarks and no captions inside the picture.`

Lines 6 and 7 are the only lines that may be identical across repositories. The composer does not add a trailing space to any line.

The prompt must not contain a directory name, a file path, a trait number, or the repository name. The exception is the repository line when `include_name` is true: the name is inserted as given. Mass names and `knot.path` are directory names and paths, so they stay out. Body labels are `body 1`, `body 2`, and so on, in `spec.masses` order. Counts, percents, hertz, pixel sizes, and hex colors are allowed. `spec.representation` is not read. The subject and the medium follow `spec.style`.

`include_name=True` with `repository_name is None` or `repository_name == ""` raises `ValueError`. A `spec` that is not a `VisualSpec` raises `TypeError`.

### Which traits become directives

A trait is extreme when its value is `<= 0.33` or `> 0.66`. Distance from the middle is `abs(value - 0.5)`.

Start from the extreme traits. While more than 7 remain, drop the one closest to 0.5. On a tie, drop the later `TRAIT_NAMES` entry (keep the earlier name). While fewer than 5 remain, add the trait not yet selected whose distance from 0.5 is largest (the next most extreme, not the one nearest 0.5). On a tie, add the earlier `TRAIT_NAMES` entry. Emit the selected traits in `TRAIT_NAMES` order.

### Subject

Count words, used for bodies: `one`, `two`, `three`, `four`, `five`, `six`, `seven`, `eight`.

Peak radius is the largest `mass.radius`. A mass is large when `radius >= 0.66 * peak`, small when `radius <= 0.33 * peak`, otherwise medium. Check large before small, so a peak of 0 counts as large. Group masses as large, then medium, then small, and skip an empty group. One mass in a group uses `{word} {size} body`. More than one uses `{word} {size} bodies`. Join groups with a comma and a space, and put ` and ` before the last group.

Placement uses the radius-weighted centroid. `wx = sum(radius * x) / sum(radius)`, `wy = sum(radius * y) / sum(radius)`. Positive x is right and positive y is down (`html_template.py:133`). If there are no masses, or the sum of radii is 0, placement is `centered`. Otherwise:

- `wx <= -0.15`: left. `wx >= 0.15`: right.
- `wy <= -0.15`: top. `wy >= 0.15`: bottom.
- Both axes: `off-center to the {left|right} and toward the {top|bottom}`.
- One axis: `off-center to the {left|right}`, or `off-center toward the {top|bottom}`.
- Neither: `centered`.

`orbits`: `An abstract composition of {bodies}, {placement}, on a dark ground.` With no masses, `{bodies}` is `no bodies` and placement is `centered`.

`creature`, one or more masses: `A creature whose torso is the largest body and whose other bodies are limbs, {placement}, on a dark ground.`

`creature`, no masses: `A creature with no bodies, centered, on a dark ground.`

Any other `spec.style`, including `auto` and the stage 8 names, raises `ValueError`. The message contains the style string.

### Directive lines

Percents, blur, jitter, and hertz use half-up rounding (a tie goes away from zero). A percent is `round_half_up(value * 100)` with no decimal. Hertz and jitter use two digits after the decimal. Blur uses one.

| Trait | High or present | Low or absent |
|---|---|---|
| `size` | `The form covers {coverage}% of the frame and contains {element_count} small marks.` | same sentence |
| `age` | see rings below | see rings below |
| `alive` | `Vivid, moving at {speed_hz} Hz.` when the trait is `>= 0.5` | `Faded, moving at {speed_hz} Hz.` otherwise |
| `crowd` | `One strand crosses the form.` when `strands.count == 1` | `{n} strands cross the form.` otherwise, `n` in digits |
| `focus` | `A bright knot sits on body {index}.` when `knot` is not `None`. `{index}` is `knot.mass_index + 1` | `No focal knot; change is spread across the form.` |
| `care` | `Crisp edges, blur {blur_px} px, jitter {jitter}.` when the trait is `>= 0.5` | `Frayed edges, blur {blur_px} px, jitter {jitter}.` otherwise |
| `sprawl` | see nesting below | see nesting below |
| `prose` | `Fine hatching covers {coverage}% of each body.` | same sentence |
| `debt` | `No cracks.` when `cracks.count == 0`; `One crack.` when it is 1 | `{n} cracks.` otherwise, `n` in digits |

`size` uses `footprint.coverage` and `footprint.element_count`. `alive` uses `motion.speed_hz`. `care` uses `edge.blur_px` and `edge.jitter`. `prose` uses `hatching.coverage`. The high and low columns for `size` and `prose` are the same sentence because the number carries the fact.

Rings (`age`): let `n = len(rings.thickness)`. The thickest ring is the lowest 1-based index of the maximum thickness. `n == 0` gives `No growth rings.` `n == 1` gives `One growth ring.` Otherwise `{n} growth rings, thickest at ring {k}.` with `n` and `k` in digits.

Nesting (`sprawl`): the mass phrase is `One body` or `{word} bodies` with the count words above. `topology.nesting_levels == 0` continues ` with no nested shapes`. `1` continues ` with 1 level of nested shapes`. Any larger `n` continues ` with {n} levels of nested shapes`.

### Palette and medium

Each mass color is CSS HSL at that mass's `hue`, saturation `round_half_up(palette.saturation * 100)` percent, lightness 45. `hue is None` uses saturation 0 (grey). Convert with the CSS hue sector formula and half-up rounding to an integer channel 0-255. Hex is six lowercase digits. List each distinct hex once, in mass order, separated by `, `. Grey at lightness 45 is `#737373`. The ground is `#121218`.

Medium tables, index `random.Random(spec.seeds.effective_seed).randrange(len(table))` from the Python standard library:

| `spec.style` | Table, index 0 first |
|---|---|
| `orbits` | `ink on dark paper`, `cut paper`, `carved and painted stone relief`, `a macro photograph of a physical model` |
| `creature` | `ink drawing`, `painted clay`, `carved wood`, `a studio photograph of a sculpture` |

### Worked example

Fixture `tests/golden/visual_spec/single-script-abstract.json` (`style` `orbits`, effective seed `1522113844098133332`). Nine traits are extreme. Distances from 0.5: `alive` 0.204486, `age` 0.476054, the other seven 0.5. Drop `alive`, then `age`. The subject is one large body (the only radius is the peak) and the centroid stays inside 0.15, so it is centered. Shell hue `134.0307475288586` and saturation `0.6283644999999999` give `#2abb4c`. The seed selects medium index 1.

```text
An abstract composition of one large body, centered, on a dark ground.
- The form covers 25% of the frame and contains 40 small marks.
- One strand crosses the form.
- A bright knot sits on body 1.
- Frayed edges, blur 6.0 px, jitter 0.25.
- One body with no nested shapes.
- Fine hatching covers 0% of each body.
- No cracks.
Palette: #2abb4c on #121218.
Medium: cut paper.
No text, no letters, no logos, no code, no screens, no mascots.
No watermarks and no captions inside the picture.
```

The masked seed for this fixture is `8904369301646676` (`effective_seed & (2**53 - 1)`). It is not part of the prompt.

### Backend

`generate_image` keeps the current return type `GeneratedImage`. A `prompt` that is not a `str` raises `TypeError`.

`OpenRouterImageBackend` sends the current body `model`, `prompt`, `n` = 1, and `size` = `1024x1024` (`image_backend.py:125-126`). When `seed` is not `None`, the body also contains `"seed": seed`. The backend does not mask and does not read `spec`. Tests build this request and do not open a connection.

`render_prompt` passes `seed=spec.seeds.effective_seed & (2**53 - 1)`.

`FakeImageBackend` requires a `VisualSpec`. `spec is None` or a value that is not a `VisualSpec` raises `ValueError`. It ignores `prompt` and `seed` for the pixels: the same spec returns the same bytes. The image is 64 by 64 RGB, encoded with `encode_png`. Footprint `(0, 0)` is the sample point of pixel `(32, 32)`. A point `(x, y)` is `(32 + x * 28, 32 + y * 28)`, positive y down.

Paint in this order, later marks overwriting earlier ones:

1. Fill `#121218` (18, 18, 24).
2. Each mass, in spec order, as a disk. Center `(32 + mass.x * 28, 32 + mass.y * 28)`, radius `mass.radius * 28`, color that mass's palette hex. A pixel `(i, j)` is inside when `(i - cx) ** 2 + (j - cy) ** 2 <= radius ** 2`.
3. The knot, when present, as a disk of color `#f2f2f2`. Center `(32 + (host.x + knot.offset_x) * 28, 32 + (host.y + knot.offset_y) * 28)`, radius `knot.radius * host.radius * 28`, `host = masses[knot.mass_index]`.
4. Each crack mark as one pixel `#d0d0d0` (208, 208, 208). On the host mass, `polar = mark.v * tau`, `px = host_cx + cos(polar) * mark.u * host_radius_px`, `py = host_cy + sin(polar) * mark.u * host_radius_px`. The pixel is `floor(v + 0.5)` on each axis (half up), clamped to `0..63`.

Strands, rings, hatching, and edge are prompt facts. They leave no mark on this raster.

### Caption strip and files

`render_prompt` validates before it writes. A `spec` that is not a `VisualSpec`, or `features` that are not `RepositoryFeatures`, raises `TypeError`. `caption=True` imports Pillow before the backend call. If that import fails, it raises `ValueError` whose message contains `pip install gitgeist[image]`, and it writes no files. `caption=False` does not import Pillow for the strip and returns the backend bytes after the existing `image_format` step.

`caption=True` runs after sniffing and after `image_format` normalization. Those two steps stay as in `docs/features/prompt-to-image/spec.md`. The strip is the strings from `conclusions(features, spec)`, in that order, not the repository name. Draw them with `ImageFont.load_default()` on an RGB strip of width 480 and fill `#121218`, text `#f2f2f2`, left and top at 0, lines stacked with no extra gap. Cut characters from the end of a line until its width is at most 480. Scale the strip with nearest-neighbor so its width equals the portrait width. The scaled height uses half-up rounding. If that height is below `round_half_up(width * 0.12)`, extend the bottom with `#121218`.

Decode the portrait with Pillow, composite any alpha over `#121218`, and convert to RGB. Append the strip below. The portrait's own pixels stay the pixels of that RGB image. Encode the composite back to the media type already chosen: PNG through Pillow, JPEG at quality 95 with `optimize=False` and `progressive=False`, or WebP at quality 90 with `lossless=False`. Tests for a PNG fake portrait check decoded pixels, not Pillow's chunk bytes.

Artifact names (`prompt.txt`, `portrait.png`, `portrait.jpg`, `portrait.webp`), directory creation, and the rule that older portraits of another extension stay on disk remain the old spec. A failure in sniffing, normalization, or the strip writes nothing.

### CLI

`--caption` omitted means on, for live mode and for prompt mode. `--caption off` on prompt mode sets `caption=False`. `--prompt-name` sets `include_name=True` and passes the repository directory name already computed for the render (`repo_path.resolve().name`).

`--prompt-name` with `--mode live` prints `error: --prompt-name applies only to --mode prompt-to-image` to stderr and exits 2, before analysis or writes. Prompt mode accepts `--caption`. The live-mode caption behaviour is unchanged.

The prompt-mode path builds the spec the way live mode does (`compute_traits`, the identity seed, `build_visual_spec`) and calls `render_prompt` with that spec, the features, and the flag values. `profile.json` and `summary.md` stay as they are.

## Business rules

- One composer. Callers of `compose_prompt` and `render_prompt` pass a `VisualSpec`.
- Fixed negative lines are the only prompt lines allowed to repeat across the corpus.
- The fake raster is a function of the spec alone.
- The OpenRouter `seed` is the masked effective seed. A provider may ignore it.
- Pillow stays an optional extra (`image` in `pyproject.toml`, also pulled in by `dev`). The strip and `image_format="png"` are the import sites. There is no silent fallback to an uncaptioned file when the caption was requested.
- `conclusions` is the caption source. This stage does not change its phrases.

## Authorization

none for the composer. The OpenRouter key rule stays in `docs/features/prompt-to-image/spec.md`.

## Data / API

```text
compose_prompt(spec: VisualSpec, *, include_name: bool = False, repository_name: str | None = None) -> str

render_prompt(
    spec: VisualSpec,
    *,
    features: RepositoryFeatures,
    repository_name: str | None = None,
    include_name: bool = False,
    caption: bool = True,
    backend: ImageGenerationBackend | None = None,
    output_dir: Path | str | None = None,
    image_format: Literal["native", "png"] = "native",
) -> PromptRenderArtifacts

ImageGenerationBackend.generate_image(prompt: str, *, spec: VisualSpec | None = None, seed: int | None = None) -> GeneratedImage
```

`backend=None` still selects `FakeImageBackend`. Public names exported from `gitgeist` and `gitgeist.render` stay the same. `2**53 - 1` is `9007199254740991`.

## Compatibility and migration

- `compose_prompt(emotional_state, profile, ...)` and `render_prompt(emotional_state, profile, ...)` raise `TypeError`. This is a breaking change in 0.12.0, recorded in the CHANGELOG with the new calls.
- `OpenRouterImageBackend.generate_image(prompt)` still works: `seed` defaults to `None` and the JSON body is unchanged.
- `FakeImageBackend.generate_image(prompt)` without `spec` raises `ValueError`. Offline tests pass a `VisualSpec`.
- `profile.json`, `summary.md`, and the live page do not change.

## Effect on existing specs

- `docs/features/prompt-to-image/spec.md` keeps media sniffing, OpenRouter errors, `image_format`, and artifact names, and points here for the composer.
- After this spec is approved, the stage 6 line in `docs/features/visual-diversity/plan.md` says the spec is approved. The stage 4 and stage 5 lines stay as written on this branch.
- `README.md` gains `--caption` for prompt mode and `--prompt-name`.
- `docs/product/emotional-repository-portrait-system.md` stays unchanged.

## Edge cases

- No masses: orbits uses `no bodies` and `centered`. Creature uses the empty-creature sentence. The raster is ground fill only, with no knot and no crack pixels.
- One mass: one large body. Its centroid is that mass. Creature uses the torso sentence.
- More than 7 extreme traits: the worked fixture drops the two closest to 0.5.
- Fewer than 5 extreme traits: add the next farthest from 0.5 until 5 lines exist.
- Two masses with the same hex: the palette lists that hex once.
- `hue is None`: `#737373`.
- `knot is None`: the focus line is the fixed sentence, and the raster has no knot disk.
- `cracks.count == 0`: the debt line is `No cracks.` and the raster has no crack pixel.
- A crack coordinate outside the frame clamps to the nearest edge pixel.
- `include_name=True` and a non-empty name: the repository line is second, and the name may appear only there.
- Caption on a 64 px PNG: the strip height is at least `round_half_up(64 * 0.12)` = 8, and the top 64 rows match the uncaptioned RGB image.

## Errors

- `compose_prompt`: `TypeError` for a non-`VisualSpec`. `ValueError` for an unknown style, and for `include_name=True` with a missing name. The style value appears in the message.
- `FakeImageBackend`: `TypeError` for a non-`str` prompt. `ValueError` when `spec` is missing or not a `VisualSpec`.
- `render_prompt`: `TypeError` for a bad `spec` or `features`. `ValueError` naming `pip install gitgeist[image]` when `caption=True` and Pillow is missing, with no files written.
- Sniffing, HTTP, missing API key, and `image_format="png"` without Pillow stay the old spec. Those failures also write no files.
- CLI: `--prompt-name` on live mode exits 2 with the message above. It does not use the exit-1 helper.

## Acceptance criteria

1. The worked fixture produces the prompt in "Worked example", byte for byte, including the final newline. `include_name=True` with repository name `sample` inserts `Repository: sample.` as line 2 and changes nothing else.
2. The fixture prompt contains neither `run.sh`, nor `Shell`, nor a trait value, nor the repository name (unless the flag is on).
3. Trait selection follows the drop and fill rules, including a tie on `TRAIT_NAMES` order, and an unknown style raises `ValueError`.
4. `FakeImageBackend` returns identical PNG bytes for the same spec and a different prompt or seed. A call without a spec raises `ValueError`. The fixture image is 64 by 64, pixel `(32, 32)` is the mass color `#2abb4c`, and a pixel outside every disk is `#121218`.
5. The OpenRouter request for the fixture includes `"seed": 8904369301646676` and the existing `model`, `prompt`, `n`, and `size`. The test does not open a socket.
6. `caption=False` returns the backend bytes and does not import Pillow. `caption=True` on the fake PNG keeps the top 64 rows and adds a strip at least 8 px tall. Missing Pillow raises `ValueError` and leaves the output directory unchanged.
7. `render_prompt` still writes `prompt.txt` and a portrait whose extension matches the sniffed type, and `image_format="png"` still normalizes through Pillow.
8. CLI: prompt mode with `--caption off` leaves the backend bytes uncaptioned; omitting `--caption` captions; `--prompt-name` on live mode exits 2 before a write; `--prompt-name` on prompt mode puts the directory name in the prompt.
9. Sniffing, OpenRouter error, and artifact-name tests from the current suite still pass, updated only where they called the old composer signature.
10. The dev script, given local checkouts of the 12 repositories named in `docs/features/visual-diversity/analysis.md:40`, writes a log under `docs/evidence/` that lists every prompt line and marks any non-fixed line that occurs more than once. It does not clone or fetch. A missing checkout is an error, not a skipped success. This script is not a CI test. The paid A/B run is not required.

## Required tests

- `tests/test_prompt_composer.py`: the worked prompt, selection (more than 7, fewer than 5, ties), placement phrases, palette hex including grey, medium index, forbidden substrings, `include_name`, unknown style, missing name.
- `tests/test_image_backend.py`: fake raster bytes, determinism against prompt and seed, missing spec, disk and crack pixel, OpenRouter JSON including the masked seed, no network. Keep the existing sniffing and HTTP error cases.
- `tests/test_prompt_render.py`: facade signature, artifact names, `caption` on and off, missing Pillow writes nothing, `image_format="png"`.
- `tests/test_cli.py`: prompt-mode caption default and `--caption off`, `--prompt-name` on prompt mode, exit 2 on live mode.
- Dev script, not collected by pytest: corpus log under `docs/evidence/`.

## Risks

- Default `--caption on` makes a default prompt render require the optional Pillow extra. This is the open choice.
- Image models may still ignore the new directives. That is what the paid A/B run would check, and this stage does not run it.
- The corpus log needs the 12 local checkouts. The implementation records the log when they are present and records their absence when they are not. It does not clone them.

## Decisions

Decided by Tomasz on 2026-11-05.

Caption default for `--mode prompt-to-image` is `on` (option a, `design.md:402`). A default prompt render fails without Pillow and tells the user to install `gitgeist[image]`. Live mode stays default on. Option (b), prompt mode default off, was not chosen.

Also decided with the plan:

- One new English spec plus the Polish pointer in `docs/features/prompt-to-image/spec.md`.
- The signatures in Data / API. No parallel v2 function. Implementation version 0.12.0.
- The sentence templates, the 0.33/0.66 cutoff, and the fill rule (add the next farthest from 0.5).
- The empty-creature sentence.
- The masked OpenRouter seed, without a new network check.
- `--prompt-name` in this stage. The other new flags stay in stage 7.
- The paid A/B run stays out of this implementation.

## Relevant SDD / ADR

- `docs/features/visual-diversity/plan.md`, `docs/features/visual-diversity/design.md`, `docs/features/visual-diversity/analysis.md`
- `docs/features/prompt-to-image/spec.md`
- `docs/features/traits-visualspec-seeds/spec.md`, `docs/features/traits-visualspec-seeds/visual-spec.md`
- `docs/decisions/0001-trait-per-abstract-channel.md`
