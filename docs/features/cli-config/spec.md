# CLI and config

Path: `docs/features/cli-config/spec.md`

Status: draft for Tomasz's review (stage 7 of `docs/features/visual-diversity/plan.md`, Plane GITGEIST-21). Open points O1-O7 are not decided yet. Written on 2026-11-11 against `main` at `b4765ec` (tag 0.12.0). Spec only: no code changes on this branch.

## Goal

`gitgeist render` exposes the `VisualSpec` choices that stage 3 built as library keywords (`style`, `user_seed`, `variety`, `scale`) as CLI flags, adds the `seeded` palette that `design.md` promises, and reads the same settings from an optional config file. A user can keep a preferred look in `./gitgeist.toml` or `~/.config/gitgeist/config.toml` and override it per run. The audience of this contract is the implementer of the stage. Target version: 0.13.0.

## Related requirements

- `docs/features/visual-diversity/plan.md:120-129` (stage 7 scope and acceptance; depends only on stage 3).
- `docs/features/visual-diversity/design.md:391-412` ("Configuration and CLI": flag table, defaults, config precedence, unknown keys are an error).
- `docs/features/visual-diversity/design.md:137` (`--palette seeded` drops the language rule for the palette), `:155` (`--style`), `:168` (`--variety`), `:173` (`--seed <int>` or `--seed random`, which prints and records the value).
- `docs/features/traits-visualspec-seeds/spec.md:52-53`, `:91` and O8 (flags and `--palette seeded` deferred to stage 7; `random` is resolved by the flag, not the library).
- `docs/features/live-renderer-v2/spec.md:38` and `character-spec.md:52` (the CLI uses the stage 3 defaults until stage 7).
- `docs/features/prompt-composer-v2/spec.md:182-188` (`--caption` and `--prompt-name` contract, kept).
- `src/gitgeist/cli.py:38-44` (choice constants), `:116-126` (`command_analyze`), `:129-190` (`command_render`), `:193-267` (`_build_parser`), `:270-278` (`main`).
- `src/gitgeist/visual/spec_builder.py:50-61` (`build_visual_spec(..., *, style="auto", user_seed=None, variety="medium")`) and `:69-72` (hue offset and `language_hue`).
- `src/gitgeist/visual/styles.py:25` (`registered_styles`), `:32` (`select_style`), `:48` (`variety_limits`).
- `src/gitgeist/visual/seeds.py:6` (`validate_user_seed`, 0 to 2^63 - 1), `:30` (`sub_seed`).
- `src/gitgeist/visual/palette.py:15-27` (`hue_offset`, `language_hue`).
- `src/gitgeist/schemas/visual_spec.py:51-54` (`Palette.mode: Literal["language"]`).
- `src/gitgeist/visual/traits.py:16` (`compute_traits(features, scale="absolute", ...)`) and `src/gitgeist/normalization/scale.py:17-18` (`ScaleMode = Literal["absolute", "corpus"]`).
- `src/gitgeist/env.py:67-71` (`user_env_file`: `$XDG_CONFIG_HOME/gitgeist/.env`, else `Path.home() / ".config" / "gitgeist" / ".env"`).
- `tests/conftest.py` (`isolated_environ`: every test gets an empty `HOME` and `USERPROFILE`; all other variables, including `XDG_CONFIG_HOME`, are removed).
- `.github/workflows/ci.yml` (required checks `verify` on Python 3.11, 3.12, 3.13 and `verify-windows` on 3.13).

## What exists today

| Flag | State at `b4765ec` | This stage |
|---|---|---|
| `--style` | none; the CLI always passes the library default `style="auto"` | new flag and config key |
| `--seed` | none; `user_seed=None` | new flag and config key; `random` resolved here |
| `--variety` | none; library default `"medium"` | new flag and config key |
| `--scale` | none; `compute_traits(features)` uses `"absolute"` on `analyze` and `render` | new flag on both commands and config key; `absolute` and `corpus` only |
| `--palette` | none; `Palette.mode` can only be `"language"` | new flag, config key and the `seeded` palette code |
| `--caption` | `render`, `choices=("on", "off")`, `default=None` meaning on, both modes | unchanged values; now also a config key |
| `--prompt-name` | `render`, `store_true`; with `--mode live` exits 2 (`cli.py:138-143`) | gains `--no-prompt-name`; now also a config key |

There is no config file handling in the package. `tomllib` is already used by `src/gitgeist/_version.py` and `tools/build_quantile_table.py`; it is in the standard library on every supported Python (`requires-python = ">=3.11"`), so no dependency is added.

## Scope

1. Flags `--style`, `--seed`, `--variety`, `--scale`, `--palette` on `gitgeist render`; `--scale` also on `gitgeist analyze`. `--prompt-name` becomes `argparse.BooleanOptionalAction` (`--prompt-name` / `--no-prompt-name`). All seven render flags default to `None` in argparse, meaning "not given on the command line".
2. New module `src/gitgeist/config.py`: file locations, TOML reading, key and value validation, and per-key resolution (CLI, then `./gitgeist.toml`, then the user file, then defaults).
3. `src/gitgeist/env.py`: a new `user_config_dir() -> Path` (`$XDG_CONFIG_HOME/gitgeist`, else `Path.home() / ".config" / "gitgeist"`). `user_env_file()` returns `user_config_dir() / ".env"`, so its result does not change.
4. `--palette seeded`: `Palette.mode` becomes `Literal["language", "seeded"]`, `build_visual_spec` gains a keyword `palette: Literal["language", "seeded"] = "language"`, and `src/gitgeist/visual/palette.py` gains `seeded_hues` (rule in "Palette").
5. `command_analyze` and `command_render` pass the resolved values to `compute_traits`, `build_visual_spec`, the scene builders and `render_prompt`.
6. Tests listed in "Required tests", README section "Options and config file", CHANGELOG entry and version 0.13.0, in the implementation that follows approval.

## Non-goals

- `--scale portfolio` and the feature store. Plan stage 8 owns them; until then `portfolio` is rejected by argparse like any other unknown choice.
- `--strategy`, `--evaluator`, `--lens`, `--eval-budget`, `--eval-refresh`, the `strategy` key and the `[evaluation]` table. Plan stage 12 owns them. Until then they are unknown keys and therefore errors.
- Config keys for `--representation`, `--mode`, `--backend`, `--image-format` and `-o`. The plan lists only the seven flags above.
- A `--config PATH` flag, a `GITGEIST_CONFIG` variable, a `--no-config` flag, and searching parent directories for `gitgeist.toml`.
- A `visual-spec.json` artifact (stage 3 decision O7 stays; `tests/test_cli.py:46` asserts it is absent).
- Adding the language names to the HUD or caption phrases (`captions.conclusions` stays as in stage 6). See O6.
- New styles (stage 8). Changes to the prompt text contract, the live renderers, `profile.json` fields, or `schema_version`.
- Secrets in the config file. API keys stay in `.env` (`design.md:410`); the config has no key for them.

## Behaviour

### Flags

All validation below runs before analysis, so a rejected run writes nothing.

| Flag | Command | Type and values | Default | Rejected input |
|---|---|---|---|---|
| `--style NAME` | `render` | `auto` or a name from `registered_styles(representation)`; today `orbits` (abstract) and `creature` (character) | `auto` | name not registered for the given `--representation`: exit 2, `error: style 'creature' is not registered for --representation abstract; registered: orbits` |
| `--seed VALUE` | `render` | decimal digits only (regex `[0-9]+`), 0 to 9223372036854775807 (2^63 - 1), or the word `random` | none (identity seed only) | argparse type error, exit 2: `argument --seed: must be an integer from 0 to 9223372036854775807 or 'random'` |
| `--variety LEVEL` | `render` | `low`, `medium`, `high` (`VARIETY_LIMITS`) | `medium` | argparse choice error, exit 2 |
| `--scale MODE` | `analyze`, `render` | `absolute`, `corpus` (`SCALE_MODES`) | `absolute` | argparse choice error, exit 2 (includes `portfolio` until stage 8) |
| `--palette MODE` | `render` | `language`, `seeded` | `language` | argparse choice error, exit 2 |
| `--caption on\|off` | `render` | unchanged | `on` | unchanged (argparse, exit 2) |
| `--prompt-name`, `--no-prompt-name` | `render` | boolean | off | `--prompt-name` with `--mode live` still exits 2 with `error: --prompt-name applies only to --mode prompt-to-image` |

argparse errors keep argparse's own format (`usage: ...` then `gitgeist render: error: ...`) and exit code 2. Errors raised by gitgeist before analysis print `error: <message>` to stderr and return 2, like the existing `--prompt-name` check. The existing exit-1 checks (`--backend` or `--image-format` with `--mode live`, missing repository path, missing API key, runtime failures) do not change.

Interactions:

- `--style` is checked against `--representation` after the config is merged, so a style that comes from a config file fails the same way. The message then names the file: `error: style 'creature' from <path> is not registered for --representation abstract; registered: orbits`. See O2.
- `--style auto` with `--variety` keeps the stage 3 rule: the pool is the first 1, 3 or all fitting styles, chosen with `style_seed(identity, user_seed)`. With one style per representation today, `--seed` and `--variety` cannot change the chosen style until stage 8.
- `--seed N` passes `user_seed=N` to `build_visual_spec`. Layout, hue offset, strands, cracks, the prompt medium and the masked OpenRouter seed all follow the effective seed, as today.
- `--seed random` draws `secrets.randbelow(2**63)` once per run, after config resolution and before analysis, and prints `seed: N` as the first stdout line, before `N artifacts written:`. The value is passed on as an ordinary user seed, so `spec.seeds.user_seed` records it in `live-state.json`. Prompt mode has no spec artifact; there the printed line is the record (O5).
- `--palette seeded` changes only hues. Layout, strands and cracks stay identical for the same seed, because `effective_seed(identity, user_seed, style)` does not include the palette.
- `--scale corpus` uses the quantile table shipped in the package (`normalize_features` with `table=None`). `profile.json` records it as `traits.scale` and `traits.table_version`. In `render` the same `Traits` object feeds `build_visual_spec`, so the picture follows the scale.
- `--caption` applies to both modes, as in stage 6. `--prompt-name` keeps its stage 6 meaning in prompt mode.

### Palette

`--palette language` is the current rule: `language_hue(mass.language, offset)` with the seeded `hue_offset` within the variety limit.

`--palette seeded` (O1):

- `Palette.mode` is `"seeded"` and `Palette.hue_offset` is `0.0`. The `"hue"` sub-seed is not drawn.
- `base = random.Random(sub_seed(effective, "palette")).uniform(0, 360)`.
- Mass `i` (0-based, in `spec.masses` order) with a known language gets hue `(base + i * 137.50776405003785) % 360` (the golden angle, so neighbouring masses never share a hue family).
- A mass whose `language` is `None` keeps `hue=None` (neutral grey), as in the language palette.
- `mass.language` is still recorded, so the language stays visible in `live-state.json`.
- Saturation is unchanged (`0.10 + 0.75 * alive`).

The live pages and the prompt composer read `mass.hue` and `palette.saturation` only, so they need no change. `spec_distance` reads `mass.hue`, so seeded palettes are measured like any other.

### Config files

Two optional files, both TOML 1.0 read with `tomllib.load` in binary mode:

1. Project file: `Path.cwd() / "gitgeist.toml"`. Only the current working directory is checked, not the analysed repository and not its parents (O4).
2. User file: `user_config_dir() / "config.toml"`, which is:
   - `$XDG_CONFIG_HOME/gitgeist/config.toml` when `XDG_CONFIG_HOME` is set and non-empty, on every platform;
   - otherwise `Path.home() / ".config" / "gitgeist" / "config.toml"`. On Linux and macOS `Path.home()` reads `HOME`. On Windows Python ignores `HOME` and uses `USERPROFILE`, so the file is `%USERPROFILE%\.config\gitgeist\config.toml`. This is the same directory as the existing user `.env` (O3).

A missing file is skipped silently. A path that exists but is not a regular file (for example a directory named `gitgeist.toml`) is an error.

Schema: top-level keys only, snake_case, same names as the flags.

| Key | TOML type | Allowed values | Flag |
|---|---|---|---|
| `style` | string | `"auto"` or a registered style name | `--style` |
| `seed` | integer or string | 0 to 9223372036854775807, or `"random"` | `--seed` |
| `variety` | string | `"low"`, `"medium"`, `"high"` | `--variety` |
| `scale` | string | `"absolute"`, `"corpus"` | `--scale` |
| `palette` | string | `"language"`, `"seeded"` | `--palette` |
| `caption` | string | `"on"`, `"off"` | `--caption` |
| `prompt_name` | boolean | `true`, `false` | `--prompt-name` / `--no-prompt-name` |

Example:

```toml
# ./gitgeist.toml
style = "auto"
variety = "high"
palette = "seeded"
seed = 42
caption = "off"
```

Types are strict. A TOML boolean is not an integer for `seed` (Python `bool` is a subclass of `int`, so the check is `type(value) is int`). A float, a date, an array or a table is a type error for every key. An empty file is valid and sets nothing.

Both files are read and fully validated on every `analyze` and `render` run when they exist, even when every key is overridden on the command line. `analyze` uses only `scale`; the other keys are valid there but have no effect.

### Precedence

Each key is resolved on its own, highest first:

1. The command-line flag, when given (argparse value is not `None`).
2. `./gitgeist.toml`.
3. The user `config.toml`.
4. The default from the flag table.

A file never merges partial values into a key: the first source that sets a key wins for that key. Different keys may come from different sources, for example `variety` from the CLI, `palette` from the project file and `seed` from the user file.

`prompt_name = true` from a file with `--mode live` is ignored for that run, not an error (O7). The exit-2 rule applies only to `--prompt-name` given on the command line.

### Errors

Every config error is raised as `ConfigError(ValueError)` from `gitgeist.config`. `main` catches it before the generic `ValueError` handler and returns 2 with one line on stderr: `error: <absolute path>: <message>`. Nothing is analysed or written. Files are checked in lookup order (project file, then user file), and the first error found is reported.

| Case | Message after `error: <path>: ` |
|---|---|
| unknown top-level key | `unknown key 'colour'; allowed keys: caption, palette, prompt_name, scale, seed, style, variety` |
| a table, including `[evaluation]` | `unknown key 'evaluation'; allowed keys: ...` (same message: a table is a key) |
| wrong type | `caption must be a string, got boolean` (TOML type names: string, integer, float, boolean, datetime, date, time, array, table) |
| value not allowed | `variety must be one of low, medium, high, got 'extreme'` |
| seed out of range | `seed must be an integer from 0 to 9223372036854775807 or "random", got -1` |
| malformed TOML | `invalid TOML: <TOMLDecodeError text>` (for example `Invalid value (at line 2, column 7)`) |
| not UTF-8 | `invalid TOML: file is not UTF-8` |
| unreadable or not a regular file | `cannot read config file: <OSError text or "not a file">` |

Several unknown keys: the message names the first one in file order. Key names are compared exactly; `Style` is an unknown key. Tests assert the prefix and key names, not the `TOMLDecodeError` wording, which may change between Python versions.

## Business rules

- One resolution path for both commands: `gitgeist.config.resolve_options` returns every key with its value and its source (`cli`, a file path, or `default`). Sources are used only for error messages.
- The config file never holds secrets and never selects a network backend.
- No silent fallback: an invalid config file stops the run. It is never skipped or partially applied.
- The defaults equal the stage 3 library defaults, so a run with no flags and no config files produces the same artifacts as 0.12.0, apart from the run-specific fields the README lists (`calculated_at`, `extracted_at`, `source_commit`, `engine_version`).

## Authorization

none. Local files and a local CLI, no network in this stage.

## Data / API

```text
# src/gitgeist/env.py
user_config_dir() -> Path

# src/gitgeist/config.py
PROJECT_CONFIG_NAME = "gitgeist.toml"
USER_CONFIG_NAME = "config.toml"
CONFIG_KEYS = ("caption", "palette", "prompt_name", "scale", "seed", "style", "variety")

class ConfigError(ValueError): path: Path
project_config_file(cwd: Path | None = None) -> Path
user_config_file() -> Path
read_config_file(path: Path) -> dict[str, object]          # {} when the file is missing
resolve_options(cli: Mapping[str, object | None], *, cwd: Path | None = None) -> ResolvedOptions

@dataclass(frozen=True)
class ResolvedOptions:
    style: str
    seed: int | Literal["random"] | None
    variety: Literal["low", "medium", "high"]
    scale: Literal["absolute", "corpus"]
    palette: Literal["language", "seeded"]
    caption: Literal["on", "off"]
    prompt_name: bool
    sources: Mapping[str, str]

# src/gitgeist/visual/spec_builder.py
build_visual_spec(features, traits, identity, representation, *, style="auto", user_seed=None,
                  variety="medium", palette="language") -> VisualSpec

# src/gitgeist/visual/palette.py
seeded_hues(seed: int, languages: Sequence[str | None]) -> list[float | None]

# src/gitgeist/schemas/visual_spec.py
Palette.mode: Literal["language", "seeded"]
```

`Palette` gains a validator: `mode == "seeded"` requires `hue_offset == 0.0`. `schema_version` stays `"1"`: the change is additive and every 0.12.0 spec stays valid.

## Compatibility and migration

- Without flags and config files, every artifact equals 0.12.0 apart from the run-specific fields (`calculated_at`, `extracted_at`, `source_commit`, `engine_version`). The golden `VisualSpec` snapshots and the live page snapshots do not change.
- `--prompt-name` keeps working; `--no-prompt-name` is new.
- `build_visual_spec` callers that do not pass `palette` get the language palette, as before.
- A user `~/.config/gitgeist/.env` keeps working. The new `config.toml` sits next to it.
- A `gitgeist.toml` that a user may already have for some other tool in the current directory will now be read; if it has foreign keys the run fails with the unknown-key message. The README says so.
- Version 0.13.0 (minor: new flags, new config file, new palette mode). CHANGELOG entry under "Added".

## Effect on existing specs

- `docs/features/traits-visualspec-seeds/visual-spec.md`: the `palette` row gains `mode` `"seeded"` with `hue_offset` 0.0 (implementation PR).
- `docs/features/live-renderer-v2/spec.md:38` and `character-spec.md:52`: the lines saying the CLI uses the stage 3 defaults stay as history; this spec supersedes them for 0.13.0.
- `docs/features/prompt-composer-v2/spec.md`: unchanged. Its `--prompt-name` and `--caption` rules hold, plus `--no-prompt-name` and the config keys.
- `docs/features/visual-diversity/plan.md`: the stage 7 status line points here.

## Edge cases

- No flags, no files: defaults; output equals 0.12.0 apart from the run-specific fields.
- `seed = "random"` in a file: a new seed every run, printed. `--seed 7` on the command line overrides it.
- `--seed 0`: valid user seed 0, not "no seed". `--seed 007` is accepted as 7. `--seed +7`, `--seed -1`, `--seed 1e3`, `--seed " 7"` are rejected.
- `--seed 9223372036854775808` (2^63): rejected.
- `style = "orbits"` in the user file and `--representation character`: exit 2 naming the user file. `--style auto` on the command line overrides it and the run succeeds.
- `--style auto` with `--variety low`: the first registered style for the representation.
- `--palette seeded` on a repository with no masses: empty `masses`, `palette.mode` `"seeded"`, `hue_offset` 0.0.
- `--palette seeded` with every mass of unknown language: all hues `None`, the picture is grey, as with the language palette.
- Running from inside the analysed repository: `./gitgeist.toml` is both the project config and a tracked or untracked file of that repository; it is scanned like any other file (the scan does not skip it).
- `XDG_CONFIG_HOME` set to an empty string: treated as unset, matching `user_env_file`.
- Project file and user file both set `seed`: the project file wins.
- `analyze` with a user file containing `palette = "rainbow"`: exit 2. Invalid values fail even on commands that do not use the key.

## Pre-merge technical acceptance criteria

Green required CI (`verify` 3.11, 3.12, 3.13 and `verify-windows` 3.13) on the latest PR head and independent Code Reviewer approval are mandatory before merge.

1. Each of the seven flags changes the expected field of the output, and an invalid value exits 2 before any file is written (plan acceptance "CLI tests for each flag").
2. Precedence holds per key: CLI over project file over user file over default (plan acceptance "precedence").
3. An unknown key in either file exits 2 with the file path and key name (plan acceptance "unknown-key error").
4. Malformed TOML, wrong types and out-of-range values exit 2 with the file path.
5. The user file is found through `XDG_CONFIG_HOME`, `HOME` (POSIX) and `USERPROFILE` (Windows), proven on both CI platforms.
6. No flags and no config: golden `VisualSpec` and live snapshots unchanged.
7. `--palette seeded` produces the hues from "Palette"; layout, strands and cracks equal the language-palette spec for the same seed.
8. README updated (plan acceptance).

## Required tests

All in `tests/test_cli.py` unless named. Tests write config files under `tmp_path` and use `monkeypatch.chdir` for the project file; no test reads a real `gitgeist.toml` or a real user config (the `isolated_environ` fixture already gives each test an empty home).

Flags, one or more each:

1. `--style orbits --representation abstract`: `live-state.json` has `spec.style == "orbits"` and `spec.style_requested == "orbits"`; `--style creature --representation abstract` exits 2 with the registered list and writes nothing.
2. `--seed 42`: `spec.seeds.user_seed == 42`; two runs give identical `live-state.json`; `--seed 43` gives a different `effective_seed`. `--seed -1`, `--seed 2**63`, `--seed abc` exit 2.
3. `--seed random`: stdout starts with `seed: N`, and `spec.seeds.user_seed == N` (patch `secrets.randbelow` for a fixed N).
4. `--variety high`: `spec.variety == "high"` and `abs(palette.hue_offset) <= 45`; `--variety extreme` exits 2.
5. `--scale corpus` on `analyze` and on `render`: `profile.json` `traits.scale == "corpus"` with a non-null `table_version`; `--scale portfolio` exits 2.
6. `--palette seeded`: `palette.mode == "seeded"`, `hue_offset == 0.0`, mass hues follow the golden-angle rule; masses, strands and cracks equal the `--palette language` run. Unit tests for `seeded_hues` in `tests/test_visual_schemas.py` or a new `tests/test_palette.py`.
7. `--caption off` from a config file removes the HUD; `--caption on` on the command line overrides it.
8. `prompt_name = true` in a file puts the name in `prompt.txt`; `--no-prompt-name` overrides it; with `--mode live` the file value is ignored (O7) and the command-line flag still exits 2.

Config (new `tests/test_config.py` for the module, plus CLI cases):

9. Precedence matrix: one key set in all four layers, then removed layer by layer; and three keys from three different sources in one run.
10. Unknown key in the project file and in the user file: exit 2, message contains the absolute path and the key; a table `[evaluation]` is reported as unknown key `evaluation`.
11. Malformed TOML (`variety = `): exit 2, message starts with `error: <path>: invalid TOML:`. A non-UTF-8 file: same prefix.
12. Wrong types: `seed = true`, `seed = 1.5`, `caption = false`, `prompt_name = "yes"`.
13. Empty file: valid, defaults apply.
14. `gitgeist.toml` that is a directory: exit 2, `cannot read config file`.
15. Invalid key value on `analyze` (render-only key): exit 2.
16. User path: `XDG_CONFIG_HOME` set wins over home; empty `XDG_CONFIG_HOME` falls back to home. A test sets `HOME` and `USERPROFILE` to two different temp directories, writes `config.toml` under each with different values, and asserts that `USERPROFILE` wins on Windows and `HOME` wins elsewhere (branch on `sys.platform == "win32"`; runs on both CI jobs).
17. `user_env_file()` still returns `<config dir>/.env` (existing env tests keep passing).
18. Golden: existing `tests/test_golden_diversity.py` snapshots and live snapshots pass unchanged.

## README changes

- New section "Options and config file" after "Portrait from an image generator": the flag table (values, defaults), a `gitgeist.toml` example, both file locations including the Windows path `%USERPROFILE%\.config\gitgeist\config.toml` and `XDG_CONFIG_HOME`, the precedence list, and the rule that unknown keys stop the run (with a note about `gitgeist.toml` files of other tools).
- "Analyze a repository": `--scale corpus` next to the sentence about the `absolute` scale.
- `--seed random` printing the seed, and that `live-state.json` records it.
- The `--prompt-name` sentence mentions `--no-prompt-name`.

## Risks

- `gitgeist.toml` in the current directory is a broad trigger: running gitgeist from any directory that holds such a file changes the result. Mitigation: the README states it, and errors name the file.
- Seeded hues can make two unrelated repositories look related by chance; that is the intended trade-off of `design.md:438`.
- Windows path behaviour depends on Python's `Path.home()`. The `verify-windows` job proves it; there is no other Windows coverage.

## Open points for Tomasz

O1. Seeded palette rule (`design.md:137` names the flag, not the rule). (a) As in "Palette": one seeded base hue, the golden angle between masses, unknown-language masses stay grey, `hue_offset` 0. (b) An independent random hue per mass (neighbours may share a family). (c) (a), but unknown-language masses also get a hue. Recommendation: (a).

O2. `style` in a config file versus `--representation`. Styles belong to one representation, and `--representation` is required on every run. (a) One flat key `style`; a mismatch with the run's representation exits 2 and names the file. (b) A per-representation table: `[style]` with `abstract = "orbits"` and `character = "creature"`. That is easier to keep in a user file, but it is not the "same keys" form of `design.md:412`. Recommendation: (a). It mirrors the flag, and while each representation has one style there is nothing to choose yet. Revisit in stage 8.

O3. User config location on Windows. (a) The same directory as the existing user `.env`: `XDG_CONFIG_HOME`, else `Path.home()/.config/gitgeist/` (`%USERPROFILE%\.config\gitgeist\config.toml` on Windows). (b) `%APPDATA%\gitgeist\config.toml` on Windows, which follows the platform convention but differs from the `.env` location. Recommendation: (a).

O4. Which directory `./gitgeist.toml` means. (a) The current working directory only, as the plan says. (b) The analysed repository's root. (c) The current directory and its parents up to the `.git` boundary, like `.env`. Recommendation: (a).

O5. Recording `--seed random` in prompt mode, which writes no spec artifact. (a) Print `seed: N` on stdout only; live mode also has it in `live-state.json`. (b) Also write it into a new artifact, which reverses stage 3 O7 (no `visual-spec.json`). Recommendation: (a).

O6. Language in the caption under `--palette seeded`. `design.md:137` says the seeded palette "keeps it in the caption", but the HUD phrases (`captions.conclusions`) do not name languages in any palette today. (a) Leave the caption unchanged and record the gap in `design.md`; the language stays in `live-state.json`. (b) Add a language phrase to the HUD and the caption strip in this stage. That changes the stage 6 caption contract and the live snapshots. Recommendation: (a).

O7. `prompt_name = true` from a config file with `--mode live`. (a) Ignore it for that run; only the command-line `--prompt-name` exits 2. (b) Exit 2, as for the flag. With (b), a user who sets the key cannot run live mode without `--no-prompt-name`. Recommendation: (a).

Exit codes are not an open point: config and pre-analysis usage errors exit 2, following the existing `--prompt-name` precedent and argparse. Runtime errors keep exit 1.

## Relevant SDD / ADR

- `docs/features/visual-diversity/plan.md`, `docs/features/visual-diversity/design.md`
- `docs/features/traits-visualspec-seeds/spec.md`, `docs/features/traits-visualspec-seeds/visual-spec.md`
- `docs/features/live-renderer-v2/spec.md`, `docs/features/live-renderer-v2/character-spec.md`
- `docs/features/prompt-composer-v2/spec.md`
- `docs/decisions/0002-optional-llm-evaluation-strategy.md` (why `strategy` and `[evaluation]` wait for stage 12)
