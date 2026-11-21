# 0003: The portrait as an isomorphic diagnosis

Status: accepted

Date: 2026-11-12

Decided by: Tomasz Madera, 2026-11-12, option (a) below

## Context

On 2026-11-11 the owner compared portraits of PHP repositories of different quality: decade-old repositories and modern framework-agnostic ones looked the same. The owner's conclusion: if gitgeist assesses the repository before it draws, the picture adds nothing. The picture should be the diagnosis itself. It may be hard to read at first, but a careful look should show what is wrong.

The current pipeline loses the structure before drawing:

- `compute_traits` reduces all features to nine scores in 0-1 (`src/gitgeist/visual/traits.py:31-35`, `src/gitgeist/schemas/traits.py:13-28`).
- The prompt keeps only traits at or below 0.33 or above 0.66, between five and seven of them (`src/gitgeist/render/prompt_composer.py:65-85`).
- Debt is the TODO and FIXME regex count per 1000 files (`src/gitgeist/ingest/repository.py:114`, `src/gitgeist/features/static.py:41`). No code-quality signal exists.
- Ingest collects no import or include graph and calls no `git blame` (no match for either in `src/gitgeist/ingest/`).
- The image model draws a free interpretation of the prompt, so the same prompt does not give a reproducible picture.

ADR 0001 lets each trait own one abstract channel. That keeps the score layer: two repositories with similar scores get similar pictures whatever their internal structure.

## Decision

1. Add a portrait drawn isomorphically from raw repository structure. Each repository element maps to one body element, and each measured quantity maps to a visual quantity through a monotonic function with no thresholds:
   - file: a cell, area by line count;
   - group of mutually dependent files (a community in the dependency graph): an organ with one skin. Directories do not shape the body. Amended on 2026-11-12 (was "directory: a limb following the tree"); see `docs/features/anatomy-representation/spec.md`, decision D1;
   - import, include or `use` edges between organs: a sinew (tendon) between them;
   - line age from `git blame`: tissue strata, old lines darker and deeper;
   - test file covering a module: covering tissue over that module;
   - change frequency (hotspots): wear on the segment surface.
2. The drawing path contains no norms, scores, thresholds, or symptom dictionaries. Judgements ("this is bad") stay in the caption and `summary.md`, never in the geometry.
3. A deterministic renderer is the source of truth for this portrait. The same commit gives the same picture. Prompt-to-image may decorate it later but never replaces it.
4. Large repositories are aggregated only along the existing structure (a directory collapses into one segment whose size is the sum of its files), never by score.
5. The isomorphic portrait is a separate representation next to the existing ones (working name `--representation anatomy`), option (a) below. ADR 0001 keeps covering the trait-driven representations. Replacing them needs a new decision, based on a comparison on evaluation repositories R1-R5.

## Options considered

- (a) A separate representation next to the existing ones (working name `--representation anatomy`). ADR 0001 keeps covering the trait-driven representations. Consequence: both paths are maintained; the new one can be compared on evaluation repositories R1-R5 before any replacement.
- (b) Replace the trait-driven representations. ADR 0001 is superseded; stages 7 and 8 of `docs/features/visual-diversity/plan.md` lose most of their scope. Consequence: one path, but no proof yet that the new portrait reads better.
- (c) Reject and keep ADR 0001 only. Consequence: the observed sameness stays; improvements remain limited to scores and prompts.

Chosen: (a). It tests the direction on R1 and R2 (older PHP) against R5 (recent PHP) without discarding working code. Replacing follows only if the comparison shows a visible difference.

## Consequences

- Ingest needs two new, slower data sources: an import graph per language and `git blame`. The first language set and a time budget for large repositories need a spec.
- Stage 7 (`docs/features/cli-config/spec.md`, PR #27) adds a seeded random palette and `--variety`. Randomness breaks "same commit, same picture", so both apply only to the trait-driven representations. The isomorphic representation ignores them.
- The product document and `docs/product/invariants.md` need a pointer to this record once it is accepted.
- Open points for the spec: which languages get an import graph first (PHP `include`, `require`, `use` is the minimum for R1-R5); how a segment is drawn when a file has no history; whether the live HTML page or a static SVG is the first output.
