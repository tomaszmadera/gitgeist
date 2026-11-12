# Anatomy representation

Path: `docs/features/anatomy-representation/spec.md`

Status: draft for Tomasz's review. Written on 2026-11-12 against `main` at `6fe8c25` (version 0.12.0). Decisions D1-D4 below were taken by Tomasz on 2026-11-12. Spec only: no code changes yet.

## Goal

`gitgeist render <repo> --representation anatomy --mode live` draws the repository as a body built one to one from its raw structure: every source file is a cell, files that depend on each other grow into organs, dependencies between organs are tendons, unconnected code drifts as dust, and vendored code is a grey cyst. The picture carries no score: a reader who looks at it sees how the code is actually wired, how old its lines are, and where it changes, and draws the diagnosis from that. The audience is the owner comparing repositories and the implementer of this feature.

The reference sketch is "Rentgen repozytoriów, wersja 3" (`/home/tomek/Workspace/gitgeist-sketches/rentgen/xray3.py`, local only, built from private repositories). This spec turns it into a product feature and adds what the sketch lacked: line age, change frequency, Python imports, and a live page.

## Related requirements

- ADR `docs/decisions/0003-portrait-as-isomorphic-diagnosis.md` (accepted, option (a)): a separate representation, deterministic, no scores or thresholds in the drawing path.
- ADR `docs/decisions/0001-trait-per-abstract-channel.md` stays in force for `abstract` and `character`; it does not apply to `anatomy`.
- `docs/features/cli-config/spec.md` (stage 7): its `--style`, `--seed`, `--variety`, `--palette` apply only to trait-driven representations (ADR 0003, Consequences).

## Decisions

Taken by Tomasz on 2026-11-12.

- D1. Organs come from the dependency graph (communities), not from the directory tree. This amends ADR 0003 decision 1 in the same change.
- D2. Per-file language facts (typing discipline, superglobals, deprecated calls) are drawn as raw measured facts in a neutral palette. No colour or mark expresses good or bad.
- D3. Graph layout and community detection use `networkx` and `numpy`, shipped as the optional extra `gitgeist[anatomy]`.
- D4. The first output is the live HTML page, like `abstract` and `character`.

## Scope

1. New representation value `anatomy` in `REPRESENTATION_MODES` (`src/gitgeist/cli.py:38`), valid only with `--mode live`.
2. A new ingest step, the anatomy scan, that collects per-file raw facts, the internal dependency graph, line ages from `git blame`, and per-file change counts.
3. A deterministic layout that turns the scan into an `AnatomyScene` (bodies, organs, cells, tendons, dust, cysts) with all coordinates computed in Python.
4. A live page that draws the scene on a canvas, with HUD, legend, hover and a slow uniform breathing motion.
5. The optional extra `anatomy` in `pyproject.toml` with `networkx` and `numpy`.

## Non-goals

- Any score, threshold on quality, norm, ranking or verdict in the scene or on the page. Judgements stay out of this representation entirely; `summary.md` is unchanged.
- `--mode prompt-to-image` for `anatomy`.
- Styles, seeds, variety or palettes for `anatomy` (stage 7 flags).
- Languages other than PHP, TypeScript/JavaScript and Python for dependency edges and language facts. Files in other languages are not scanned.
- Static SVG or PNG export. A later spec may add it.
- Changes to `abstract`, `character`, `profile.json`, the traits, or `live-state.json` of the existing representations.

## Behaviour

### Command line

- `gitgeist render <repo> --representation anatomy --mode live [-o DIR] [--caption on|off]`.
- It writes `profile.json` and `summary.md` exactly as other render runs do, then `live-preview.html`, `live-state.json` and `identity-seed.json` through the same writer as `render_live` (`src/gitgeist/render/facade.py:44`).
- `--mode prompt-to-image` with `anatomy`: exit 2, `error: --representation anatomy supports only --mode live`, no files written.
- After stage 7 lands, `--style`, `--seed`, `--variety` or `--palette` given on the command line with `anatomy`: exit 2 naming the flag (`error: --seed does not apply to --representation anatomy`). The same keys from a config file are ignored for `anatomy`.
- Without the extra: exit 1, `error: --representation anatomy requires networkx and numpy; install them with: pip install gitgeist[anatomy]`, and no `live-*` file written. The import check runs before analysis starts.

### Which files are scanned

- Candidates: `git ls-tree -r HEAD`, regular and executable blobs only (symlinks and submodules are excluded). The index and the working tree never change the scan. A directory that is not a Git repository, or a repository without commits: exit 1 naming the cause. Untracked files are never scanned.
- Scanned extensions: `.php`; `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`; `.py`.
- Never scanned: paths under a `vendor/` or `node_modules/` segment.
- Test files: path has a `test/`, `tests/`, `spec/` or `__tests__/` segment, or the name matches `*Test.php`, `*.test.*`, `*.spec.*`, `test_*.py`, `*_test.py`.
- Foreign (vendored) files are scanned and drawn as cysts, never as organs. A file is foreign when any of these holds: it lies under a directory below the root that has its own `LICENSE*` or `COPYING*` (case-insensitive, only files whose extension is not a scanned extension), `composer.json` or `package.json`; its name matches `*.min.*`; it lies under a `third_party/` or `third-party/` segment; or `.gitattributes` marks it `linguist-vendored`. No list of library names is used.

### Per-file raw facts

Every scanned file records:

- `lines`: newline count plus one.
- `changes`: number of commits reachable from HEAD that touch the path, from `git log --format= --name-only HEAD` (no rename following).
- `line_years`: count of lines per author year from `git blame --line-porcelain -w HEAD -- <path>`.
- Language facts, counts or booleans as measured, never combined:
  - PHP: `namespace` (bool), `strict_types` (bool), `superglobals` (count of `$_GET`, `$_POST`, `$_REQUEST`, `$_COOKIE`, `$_SESSION`, `$_SERVER`, `$_FILES`), `globals` (count of `global $` statements), `deprecated_calls` (count of calls to functions removed from PHP: `mysql_*(`, `ereg*(`, `split(`, `each(`, `create_function(`), `includes` (count of `require`/`include` forms).
  - TypeScript/JavaScript: `typed` (bool: `.ts`/`.tsx` and repository `tsconfig.json` with `"strict": true`), `loose_marks` (count of `: any`, `as any`, `@ts-ignore`, `@ts-nocheck`).
  - Python: `annotated_functions` and `functions` (counts of `def` with and without a `->` return annotation).

### Dependency graph

An undirected graph whose nodes are scanned files and whose edges are resolved internal dependencies. Unresolved references (external packages, dynamic paths) are dropped and counted in the scene as `unresolved_references`.

- PHP: a `use` of a fully qualified class defined in a scanned file; `new X`, `extends X`, `implements X`, `instanceof X`, `X::` where exactly one scanned file defines class `X`; `require`/`include` of a string literal ending in `.php`, matched by the longest path suffix among scanned files.
- TypeScript/JavaScript: `import ... from '<spec>'`, `import('<spec>')`, `require('<spec>')` where the spec is relative or matches a `compilerOptions.paths` alias of the root `tsconfig.json`; resolved by trying the stem, then `.ts`, `.tsx`, `.js`, `.jsx`, then `/index.ts`, `/index.tsx`, `/index.js`.
- Python: `import a.b` and `from a.b import c` (also relative forms) resolved to `a/b.py` or `a/b/__init__.py` relative to the root or to `src/`.
- Self edges are dropped. Parallel references between the same two files count as one edge with weight equal to the reference count.

### Layout

All coordinates are computed in Python and stored in the scene. The same repository commit and the same installed `networkx` and `numpy` versions give a byte-identical `live-state.json`.

- Own files (not foreign) form the own graph. Each connected component with two or more files is a body; a component of one file is dust.
- Organs: Louvain communities of each body (`networkx.community.louvain_communities`, `seed=7`, default resolution). Every body is partitioned, whatever its size; a body may be one organ.
- Cell radius is `0.55 * sqrt(max(lines, 4))` in layout units: cell area grows linearly with line count.
- Inside an organ: spring layout with `seed=7`, scaled to the organ radius `1.15 * sqrt(sum of cell radii squared) + 2`.
- Organs inside a body: spring layout of the condensed organ graph weighted by cross edges, then pairwise separation until no two organs overlap.
- Tendons: one per organ pair with cross edges; width grows with `log1p(cross edges)`.
- Bodies and cysts are packed largest first on a golden-angle spiral around the largest body. Cysts group foreign files by their first three path segments.
- Dust: each file is placed at a position derived from the SHA-1 of its path, so it does not move when other files change.
- Ordering everywhere is by size then path, so equal sizes never depend on dict order.

### What each visual property means

Every mapping is monotonic and has no threshold.

| Visual property | Raw fact |
|---|---|
| Cell area | `lines` |
| Cell membership in an organ, organ outline (one merged skin) | community in the dependency graph |
| Tendon width | number of edges between two organs |
| Separate body | separate connected component |
| Dust speck | file with no internal dependency |
| Grey cyst with dashed outline | foreign files |
| Concentric strata inside a cell | `line_years` share per year; older years innermost and darker, lightness linear over the repository's own first-to-last blame year |
| Surface wear (grain density on the cell edge) | `changes`, square-root scale |
| White rim | test file |
| Thin outer membrane on a non-test cell | number of test files with an edge to it |
| Tissue hue | language (one neutral hue family per language) |
| Tissue texture: solid, hatched, dotted | language discipline facts: PHP `namespace` and `strict_types` both, one, none; TS `typed` without and with `loose_marks`, or untyped JS; Python annotated share drawn as the solid fraction of the cell |
| Light grey dots inside a cell | `superglobals + globals`, one dot per occurrence; dots shrink uniformly so all of them fit inside the cell |
| Hollow dots inside a cell | `deprecated_calls` |

The palette has no red or green and no warm-versus-cold pair that reads as bad versus good. Every mark uses one neutral light colour on the dark ground; hue only tells the language.

### Page

- Built with `page_html` (`src/gitgeist/render/page_common.py:177`) and a new script, title representation `anatomy`.
- HUD (when `--caption on`): repository name and raw counts only: scanned files, edges, bodies, organs in the largest body, dust files, foreign share of lines, first and last blame year, `unresolved_references`. No adjective, no ranking.
- Legend: always shown, lists every row of the table above in one line each.
- Hover on a cell: path, lines, changes, line years, language facts, number of internal edges. Hover on an organ skin: file count and total lines. Hidden with `--caption off`.
- Motion: every body breathes with the same period and amplitude. Motion never encodes a fact.
- The page fits the viewport; the scene is framed on bodies and cysts, not on dust.

## Business rules

- No scene field, colour, size or motion depends on a trait, a score, a norm or a comparison with other repositories.
- Every scanned file appears exactly once in the scene: as a cell of one organ, as dust, or inside one cyst.
- Same commit and same library versions: byte-identical `live-state.json`.
- The anatomy path does not change `profile.json`, `summary.md`, or the outputs of `abstract` and `character`.

## Authorization

none

## Data / API

- New schema `AnatomyScene` in `src/gitgeist/schemas/live_state.py`: `schema_version: "1"`, `representation: "anatomy"`, `repository_name`, `engine_version`, `caption`, `library_versions` (`networkx`, `numpy`), `counts` (HUD numbers), `blame_years` (first, last), `bodies` (each with organs, each organ with cells: path, x, y, r, facts), `tendons`, `dust`, `cysts`, `unresolved_references`. Frozen, `extra="forbid"`, like the existing scenes.
- `render_live` accepts `AnatomyScene` in addition to the two existing scenes.
- New modules: the anatomy scan under `src/gitgeist/ingest/`, the layout under `src/gitgeist/render/`. Only the layout module imports `networkx` and `numpy`.
- `pyproject.toml`: `anatomy = ["networkx>=3.2", "numpy>=1.26"]`; `dev` gains both.
- Version: 0.13.0 if stage 7 has not shipped by then, otherwise the next minor.

## Edge cases

- No scanned file: the scene has no body, dust or cyst; the page shows the HUD, the legend and an empty ground. Exit 0.
- Only foreign files: cysts only.
- A file that `git blame` reports as binary or that cannot be decoded: its `line_years` is empty and its cell has no strata; it is counted in `counts.unblamed`.
- A shallow clone: blame and log stop at the shallow boundary; the HUD shows the blame years it saw. No error.
- Very large repositories: every file is still drawn; no sampling, no aggregation.

## Errors

- Missing extra: exit 1 with the install hint, before analysis.
- `git` missing, not a repository, or no commits: exit 1 naming the cause.
- A `git blame` or `git log` call that fails for a reason other than a binary file, or runs longer than 120 seconds: exit 1 naming the file and the Git error. No partial page is written.
- Invalid flag combination: exit 2 as in "Command line".

No silent fallback: the scan never skips a file or an edge type without counting it in the scene.

## Acceptance criteria

1. `gitgeist render <fixture> --representation anatomy --mode live -o out` writes `profile.json`, `summary.md`, `live-preview.html`, `live-state.json`, `identity-seed.json`, exit 0.
2. Two runs on the same fixture commit give byte-identical `live-state.json`.
3. On the fixture repository, every scanned file appears exactly once in the scene, and the bodies, organs, dust and cysts match the expected partition stored in the test.
4. A PHP `use`, a TS relative import with an alias, and a Python relative import in the fixture each produce the expected edge; an import of an external package produces none and increments `unresolved_references`.
5. Changing only one file's line count changes only that cell's radius and the positions in its own body; dust positions of other files stay the same.
6. `--mode prompt-to-image --representation anatomy` exits 2 and writes nothing. Without `networkx` importable, the run exits 1 with the install hint and writes no `live-*` file.
7. The page contains no colour in the red or green hue ranges (hue 340-20 and 90-150 at saturation above 40 %), checked on the generated CSS and script constants.
8. `--caption off` removes HUD and hover but keeps the legend.
9. Owner check on R1, R2 and R5 (`docs/evidence/`, no repository names or paths published): the owner can tell the older PHP repositories from the recent one by looking at the pages. This is a review gate, not an automated test.

## Required tests

- Scan: language facts, test and foreign detection, `.gitattributes` vendoring, edge resolution per language, unresolved counting, `changes` and `line_years` on a fixture Git repository built in `tmp_path`.
- Layout: partition invariants, determinism, dust stability, ordering ties, empty and foreign-only repositories.
- Schema: `AnatomyScene` round trip and `extra="forbid"`.
- CLI: success path, prompt mode rejection, missing extra (simulated import failure), caption off.
- Page: snapshot of the scene JSON embedded in the HTML with the float tolerance used by the existing live snapshots (`tests/snapshot_helpers.py`), palette check of criterion 7.
- Regression: existing `abstract` and `character` snapshots unchanged.

## Relevant SDD / ADR

- `docs/decisions/0003-portrait-as-isomorphic-diagnosis.md`
- `docs/decisions/0001-trait-per-abstract-channel.md` (does not apply here)
- `docs/features/live-renderer-v2/spec.md` (live page conventions)
- `docs/features/cli-config/spec.md` (stage 7 flags that `anatomy` rejects)
