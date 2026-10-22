# Gitgeist

A system that presents a Git repository as an emotional visual portrait.

## Status

Prototype, version 0.5.1. The `gitgeist` command line tool (`analyze`, `render`) runs the whole pipeline: rule-based sensors, an emotional model, a visual profile, explanations, and `live` / `prompt-to-image` rendering.

Known gap: the emotional interpretation uses fixed deterministic rules. The semantic interpretation layer that the product document requires (JEV, optionally with a stronger LLM) is not implemented yet. See `docs/product/invariants.md` (entry `jev-real-integration`, status `unmet`).

## Requirements

- Python 3.11 or newer (the development profile targets 3.14)
- Local environment: `venv`

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

The examples below call `.venv/bin/gitgeist` directly; after `source .venv/bin/activate`, plain `gitgeist` is enough. In a native Windows venv, use `.venv\Scripts\` instead of `.venv/bin/`.

## Usage

### Analyze a repository

```bash
.venv/bin/gitgeist analyze /path/to/repo
```

Writes `profile.json` and `summary.md` to `./gitgeist-output/<repo-name>`, relative to the current working directory. Use `-o DIR` for a different directory. When you run the command from inside the analyzed repository, the scan skips `gitgeist-output/`, so earlier artifacts do not change the result. A custom `-o` directory inside the repository is not skipped.

### Live portrait (HTML, no network)

```bash
.venv/bin/gitgeist render /path/to/repo --representation character --mode live
.venv/bin/gitgeist render /path/to/repo --representation abstract --mode live
```

Adds `live-preview.html`, `live-state.json` and `identity-seed.json` next to `profile.json` and `summary.md`. The identity seed comes from the repository's root commits, so new commits do not reshuffle the picture.

### Portrait from an image generator

Offline and deterministic with the default `fake` backend (the same prompt gives identical `portrait.png` bytes). The `fake` backend writes a 16x16 placeholder PNG derived from the prompt hash, not a real portrait:

```bash
.venv/bin/gitgeist render /path/to/repo --representation character --mode prompt-to-image
```

Real generation through the OpenRouter Image API:

```bash
export OPENROUTER_IMAGE_API_KEY="..."
.venv/bin/gitgeist render /path/to/repo --representation character --mode prompt-to-image --backend openrouter
```

The `openrouter` backend reads these environment variables:

- `OPENROUTER_IMAGE_API_KEY`: API key (required),
- `OPENROUTER_IMAGE_API_URL`: full POST endpoint (default `https://openrouter.ai/api/v1/images`),
- `OPENROUTER_IMAGE_MODELS`: comma-separated models; the first entry is used (default `google/gemini-3.1-flash-lite-image`).

You can also set them in a `.env` file, which is loaded on every run. Sources in order of precedence (highest first):

1. The process environment (`export ...`),
2. `.env` in the current directory or its parents (up to the `.git` boundary), or the file named by `GITGEIST_ENV_FILE`,
3. The user file `~/.config/gitgeist/.env` (respects `XDG_CONFIG_HOME`), a global fallback that works from any directory.

An empty value in a `.env` file (for example `OPENROUTER_IMAGE_API_KEY=` copied from `.env.example`) counts as not set, so a lower-priority source can still provide it.

Without a key, the command exits with code 1; it does not silently switch to the `fake` backend. Both backends write `prompt.txt` and a portrait named after the detected byte format: `portrait.png`, `portrait.jpg`, or `portrait.webp`. `render_prompt` also returns the detected media type in the `media_type` field. The `--backend` and `--image-format` options apply only to `--mode prompt-to-image`.

### Convert the portrait to PNG

By default the portrait keeps the format returned by the backend (`--image-format native`). A fixed PNG format needs the optional Pillow dependency and the `--image-format png` flag:

```bash
.venv/bin/pip install -e ".[image]"
.venv/bin/gitgeist render /path/to/repo --representation character --mode prompt-to-image --backend openrouter --image-format png
```

### Check determinism on your own repository

```bash
.venv/bin/gitgeist analyze /path/to/repo -o /tmp/gg-a
.venv/bin/gitgeist analyze /path/to/repo -o /tmp/gg-b
diff /tmp/gg-a/summary.md /tmp/gg-b/summary.md
```

The same repository state gives a byte-identical `summary.md`. `profile.json` differs only in run-specific fields (`calculated_at`, `extracted_at`, `source_commit`, `engine_version`).

## Tests

```bash
.venv/bin/pytest tests
```

## Documentation

The documents are in Polish.

- `docs/product/`: approved product requirements and the invariant register.
- `docs/features/`: behavior contracts of individual features.
