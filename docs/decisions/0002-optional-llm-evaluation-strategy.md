# 0002: Optional LLM rubric evaluation strategy

Status: accepted

Date: 2026-10-22

Decided by: Tomasz Madera, stage 0 of `docs/features/visual-diversity/plan.md`

## Context

`docs/features/visual-diversity/design.md` "Strategy 2: rubric evaluation" proposes a second way to drive the portrait: a language model scores the repository against a fixed rubric, and the scores become the same traits and `VisualSpec` as the counter strategy. The current specs (`docs/features/feature-extraction/spec.md`, `docs/features/emotional-state-model/spec.md`) describe a deterministic-only interpretation, and `docs/product/invariants.md` records the JEV integration (`jev-real-integration`) as `unmet`.

## Decision

1. gitgeist gets an optional LLM interpretation path, the `evaluation` strategy, selected with `--strategy evaluation` (config key `strategy`).
2. The default stays `--strategy counters`. A run without the flag never calls a model.
3. The evaluation strategy is not JEV. `jev-real-integration` stays `unmet`, and the existence of this path must not be reported as meeting it.
4. The feature-extraction and emotional-state-model specs stay deterministic-only. The evaluation path gets its own spec (plan stages 9 to 12).
5. The first evaluator backend is the Antigravity CLI `agy` (Google Gemini models), adapter id `agy`, called non-interactively as `agy -p --print-timeout <seconds>`. The owner refers to this path as "gemini-cli"; the `gemini` binary is not used. `command`, `grok-cli`, `openrouter` and `fake` follow as in the design.
6. No silent fallback: a failed evaluation stops the run with an error naming the backend and cause, and never falls back to `counters` or another backend.

## Consequences

- Evaluation runs use the owner's Antigravity subscription quota and send a sample of the repository to Google. Every run on the owner's repositories needs his yes.
- Model output is not deterministic. Results are cached by the key in `design.md` "Caching" so a run can be reproduced.
- Tests use the `fake` evaluator and a stub executable; CI never calls a model.
