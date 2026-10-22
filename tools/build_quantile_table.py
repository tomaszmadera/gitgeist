"""Build the quantile table of the corpus scale mode (dev tool, not part of the package).

Reads a corpus file (tools/quantile-corpus.toml: [[repository]] with name, url
and commit as a full SHA) and one local clone per entry, checked out at the
pinned commit with a clean working tree. For every repository it runs
extract_features and the same raw inputs and transforms as
gitgeist.normalization, then writes the values u at the probabilities 0.00,
0.05, ..., 1.00 (linear interpolation over the sorted values, q = p * (n - 1)).

The output is JSON with sorted keys, indent 2, LF and a final newline, so the
same corpus and reference time give a byte-identical file. The script never
clones, fetches or connects to the network, and writes only the --out file.

Usage (from the repository root, with the package importable):

    python tools/build_quantile_table.py build --corpus tools/quantile-corpus.toml \\
        --reference-time 2026-10-22T00:00:00Z \\
        --out src/gitgeist/normalization/data/quantiles-v1.json NAME=PATH [NAME=PATH ...]

Errors (missing or unknown NAME=PATH, not a repository, dirty working tree,
HEAD other than the pinned commit, --reference-time without a zone, write
failure) print a message to stderr and exit with code 1 without an output file.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TABLE_VERSION = "1"
GIT_TIMEOUT_SECONDS = 60
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class BuildError(Exception):
    """Input problem reported as one line on stderr with exit code 1."""


def read_corpus(path: Path) -> list[dict[str, str]]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise BuildError(f"cannot read corpus {path}: {error}") from error
    entries = data.get("repository")
    if not isinstance(entries, list) or not entries:
        raise BuildError(f"corpus {path} has no [[repository]] entries")
    corpus: list[dict[str, str]] = []
    for index, entry in enumerate(entries):
        name = entry.get("name") if isinstance(entry, dict) else None
        label = name if isinstance(name, str) else f"entry {index + 1}"
        if not isinstance(entry, dict) or any(not isinstance(entry.get(k), str) for k in ("name", "url", "commit")):
            raise BuildError(f"{label}: corpus entry needs string fields name, url and commit")
        if not FULL_SHA.match(entry["commit"]):
            raise BuildError(f"{label}: commit must be a full lowercase SHA, got {entry['commit']!r}")
        if any(e["name"] == name for e in corpus):
            raise BuildError(f"{label}: duplicate name in the corpus")
        corpus.append({"name": entry["name"], "url": entry["url"], "commit": entry["commit"]})
    return corpus


def parse_reference_time(text: str) -> datetime:
    try:
        moment = datetime.fromisoformat(text)
    except ValueError as error:
        raise BuildError(f"--reference-time {text!r} is not ISO 8601") from error
    if moment.utcoffset() is None:
        raise BuildError(f"--reference-time {text!r} has no time zone")
    return moment.astimezone(timezone.utc)


def parse_paths(raw: list[str], corpus: list[dict[str, str]]) -> dict[str, Path]:
    names = {entry["name"] for entry in corpus}
    paths: dict[str, Path] = {}
    for item in raw:
        name, sep, path = item.partition("=")
        if not sep or not name or not path:
            raise BuildError(f"{item}: expected NAME=PATH")
        if name not in names:
            raise BuildError(f"{name}: not in the corpus")
        if name in paths:
            raise BuildError(f"{name}: path given twice")
        paths[name] = Path(path)
    for entry in corpus:
        if entry["name"] not in paths:
            raise BuildError(f"{entry['name']}: no NAME=PATH given")
    return paths


def _git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # --no-optional-locks: git status must not refresh (write) the index.
    return subprocess.run(
        ["git", "--no-optional-locks", *args],
        cwd=path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )


def check_repository(name: str, path: Path, commit: str) -> None:
    if not path.is_dir():
        raise BuildError(f"{name}: {path} is not a directory")
    toplevel = _git(path, "rev-parse", "--show-toplevel")
    if toplevel.returncode != 0 or Path(toplevel.stdout.strip()).resolve() != path.resolve():
        raise BuildError(f"{name}: {path} is not the root of a Git repository")
    status = _git(path, "status", "--porcelain", "--untracked-files=all")
    if status.returncode != 0:
        raise BuildError(f"{name}: git status failed: {status.stderr.strip()}")
    if status.stdout.strip():
        raise BuildError(f"{name}: working tree of {path} is not clean")
    head = _git(path, "rev-parse", "HEAD")
    if head.returncode != 0:
        raise BuildError(f"{name}: cannot resolve HEAD: {head.stderr.strip()}")
    if head.stdout.strip() != commit:
        raise BuildError(f"{name}: HEAD is {head.stdout.strip()}, expected the pinned commit {commit}")


def quantiles(values: list[float], count: int) -> list[float]:
    """Linear interpolation quantiles at p = i / (count - 1), q = p * (n - 1)."""
    s = sorted(values)
    result = []
    for i in range(count):
        q = i * (len(s) - 1) / (count - 1)
        lo, hi = math.floor(q), math.ceil(q)
        result.append(s[lo] + (s[hi] - s[lo]) * (q - lo))
    return result


def build_table(corpus: list[dict[str, str]], paths: dict[str, Path], reference_time: datetime) -> dict[str, Any]:
    from pydantic import ValidationError

    from gitgeist.features.extractor import extract_features
    from gitgeist.normalization.inputs import INPUTS_BY_NAME, TABLE_INPUT_NAMES, raw_inputs, transformed
    from gitgeist.normalization.table import QUANTILE_PROBABILITIES, QuantileTable

    for entry in corpus:
        check_repository(entry["name"], paths[entry["name"]], entry["commit"])

    values: dict[str, list[float]] = {name: [] for name in TABLE_INPUT_NAMES}
    for entry in corpus:
        print(f"extracting {entry['name']} ({paths[entry['name']]})", file=sys.stderr)
        raw = raw_inputs(extract_features(paths[entry["name"]]), reference_time)
        for name in TABLE_INPUT_NAMES:
            x = raw[name]
            if x is None:
                raise BuildError(f"{entry['name']}: input {name} has no value (no commit history)")
            values[name].append(transformed(INPUTS_BY_NAME[name], x))

    data = {
        "table_version": TABLE_VERSION,
        "probabilities": list(QUANTILE_PROBABILITIES),
        "reference_time": reference_time.isoformat(),
        "corpus": corpus,
        "inputs": {name: quantiles(v, len(QUANTILE_PROBABILITIES)) for name, v in values.items()},
    }
    try:
        QuantileTable.model_validate(data)
    except ValidationError as error:
        raise BuildError(f"built table is invalid: {error}") from error
    return data


def render(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, sort_keys=True, indent=2) + "\n").encode("utf-8")


def command_build(args: argparse.Namespace) -> int:
    try:
        reference_time = parse_reference_time(args.reference_time)
        corpus = read_corpus(Path(args.corpus))
        paths = parse_paths(args.repos, corpus)
        content = render(build_table(corpus, paths, reference_time))
    except BuildError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    try:
        # Bytes, so the file has LF on every platform.
        Path(args.out).write_bytes(content)
    except OSError as error:
        print(f"error: cannot write {args.out}: {error}", file=sys.stderr)
        return 1
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="build the quantile table from local clones of the corpus")
    build.add_argument("repos", nargs="+", help="NAME=PATH for every corpus entry")
    build.add_argument("--corpus", required=True, help="corpus TOML file (tools/quantile-corpus.toml)")
    build.add_argument("--reference-time", required=True, help="ISO 8601 time with a zone, e.g. 2026-10-22T00:00:00Z")
    build.add_argument("--out", required=True, help="output JSON file")
    build.set_defaults(func=command_build)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
