"""Log prompt lines for the 12-repository visual-diversity corpus.

The script reads local checkouts. It does not clone or fetch. A missing name or
a path that is not a directory is an error, and then no log is written.

Usage (from the repository root, with the package importable):

    python tools/prompt_corpus_check.py --out docs/evidence/prompt-composer-v2-corpus.txt NAME=PATH ...

Pass all 12 names from docs/features/visual-diversity/analysis.md: is-odd, click,
flask, requests, gitgeist, z, lua, awesome, alpine, zlib, NeKode, fresh.
`--reference-time` is an ISO 8601 timestamp with a zone. The default is now.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

CORPUS = (
    "is-odd",
    "click",
    "flask",
    "requests",
    "gitgeist",
    "z",
    "lua",
    "awesome",
    "alpine",
    "zlib",
    "NeKode",
    "fresh",
)
REPRESENTATIONS = ("abstract", "character")
FIXED_LINES = {
    "No text, no letters, no logos, no code, no screens, no mascots.",
    "No watermarks and no captions inside the picture.",
}


class CorpusError(Exception):
    """A checkout is missing or the arguments do not name the corpus."""


def parse_repos(raw: list[str]) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for item in raw:
        name, separator, path = item.partition("=")
        if separator != "=" or not name or not path:
            raise CorpusError(f"{item!r} is not NAME=PATH")
        if name not in CORPUS:
            raise CorpusError(f"{name} is not one of the 12 corpus repositories")
        if name in found:
            raise CorpusError(f"{name} is listed twice")
        found[name] = Path(path)
    missing = [name for name in CORPUS if name not in found]
    if missing:
        raise CorpusError("missing checkout arguments: " + ", ".join(missing))
    absent = [f"{name}={found[name]}" for name in CORPUS if not found[name].is_dir()]
    if absent:
        raise CorpusError("checkout is not a directory: " + ", ".join(absent))
    return found


def prompts_for(path: Path, reference_time: datetime) -> dict[str, str]:
    from gitgeist.features.extractor import extract_features
    from gitgeist.ingest.identity import compute_identity_seed
    from gitgeist.render.prompt_composer import compose_prompt
    from gitgeist.visual import build_visual_spec, compute_traits

    features = extract_features(path)
    traits = compute_traits(features, reference_time=reference_time)
    identity = compute_identity_seed(path)
    return {
        mode: compose_prompt(build_visual_spec(features, traits, identity, mode))
        for mode in REPRESENTATIONS
    }


def render_log(prompts: dict[str, dict[str, str]], reference_time: datetime) -> str:
    lines: list[str] = [f"reference_time: {reference_time.isoformat()}", ""]
    occurrences: dict[str, list[str]] = {}
    for name in CORPUS:
        for mode in REPRESENTATIONS:
            text = prompts[name][mode]
            lines.append(f"## {name} {mode}")
            for line in text.splitlines():
                lines.append(line)
                occurrences.setdefault(line, []).append(f"{name} {mode}")
            lines.append("")
    lines.append("## repeated non-fixed lines")
    repeats = [
        (line, where)
        for line, where in occurrences.items()
        if line not in FIXED_LINES and len(where) > 1
    ]
    if not repeats:
        lines.append("(none)")
    else:
        for line, where in repeats:
            lines.append(f"{len(where)} | {line}")
            lines.append("  " + ", ".join(where))
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repos", nargs="+", help="NAME=PATH for every corpus repository")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/evidence/prompt-composer-v2-corpus.txt"),
        help="log path (default: docs/evidence/prompt-composer-v2-corpus.txt)",
    )
    parser.add_argument(
        "--reference-time",
        default=None,
        help="ISO 8601 timestamp with a timezone (default: now)",
    )
    args = parser.parse_args(argv)
    if args.reference_time is None:
        reference_time = datetime.now(timezone.utc)
    else:
        reference_time = datetime.fromisoformat(args.reference_time)
        if reference_time.utcoffset() is None:
            raise CorpusError("--reference-time must include a timezone")
    try:
        repos = parse_repos(args.repos)
        prompts = {name: prompts_for(path, reference_time) for name, path in repos.items()}
    except CorpusError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_log(prompts, reference_time), encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CorpusError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
