"""Command line interface for Gitgeist.

Provides the user-facing entry point from product section 22 (MVP scope):
``gitgeist analyze`` runs the deterministic analysis pipeline and writes the
required artifacts; ``gitgeist render`` additionally produces live or
prompt-to-image generation artifacts.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from gitgeist import __version__
from gitgeist.explain import explain
from gitgeist.features.extractor import extract_features
from gitgeist.interpretation.emotional_model import evaluate_emotional_state
from gitgeist.mapping.latent_mapper import map_emotional_to_latent
from gitgeist.render.facade import render_live, render_prompt
from gitgeist.render.image_backend import (
    API_KEY_ENV,
    FakeImageBackend,
    ImageGenerationBackend,
    OpenAICompatibleBackend,
)
from gitgeist.schemas.emotional import EmotionalState
from gitgeist.schemas.visual_latent import VisualLatentProfile

REPRESENTATION_MODES = ("character", "abstract")
GENERATION_MODES = ("live", "prompt-to-image")
BACKEND_CHOICES = ("fake", "openai-compatible")
DEFAULT_OUTPUT_ROOT = "gitgeist-output"
GIT_TIMEOUT_SECONDS = 30


def _error(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _head_commit(repo_path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    commit = result.stdout.strip()
    if result.returncode != 0 or not commit:
        return None
    return commit


def _build_backend(name: str | None) -> ImageGenerationBackend:
    if name is None or name == "fake":
        return FakeImageBackend()
    if name == "openai-compatible":
        return OpenAICompatibleBackend()
    raise ValueError(f"Unsupported image backend: {name!r}. Must be one of {BACKEND_CHOICES}.")


def _resolve_repo_path(raw_path: str) -> Path | None:
    repo_path = Path(raw_path)
    if not repo_path.is_dir():
        return None
    return repo_path


def _analyze(
    repo_path: Path, repository_name: str, output_dir: Path
) -> tuple[list[Path], EmotionalState, VisualLatentProfile]:
    features = extract_features(repo_path)
    state = evaluate_emotional_state(features, source_commit=_head_commit(repo_path))
    profile = map_emotional_to_latent(state)
    explanation = explain(
        features,
        state,
        profile,
        repository_name=repository_name,
        output_dir=output_dir,
    )
    written = [
        path
        for path in (explanation.profile_path, explanation.summary_path)
        if path is not None
    ]
    return written, state, profile


def _report_written(paths: list[Path]) -> None:
    print(f"{len(paths)} artifacts written:")
    for path in paths:
        print(f"  {path}")


def command_analyze(args: argparse.Namespace) -> int:
    repo_path = _resolve_repo_path(args.repo_path)
    if repo_path is None:
        return _error(f"repository path does not exist or is not a directory: {args.repo_path}")
    repository_name = repo_path.resolve().name
    output_dir = (
        Path(args.output) if args.output else Path.cwd() / DEFAULT_OUTPUT_ROOT / repository_name
    )
    written, _state, _profile = _analyze(repo_path, repository_name, output_dir)
    _report_written(written)
    return 0


def command_render(args: argparse.Namespace) -> int:
    repo_path = _resolve_repo_path(args.repo_path)
    if repo_path is None:
        return _error(f"repository path does not exist or is not a directory: {args.repo_path}")
    repository_name = repo_path.resolve().name
    output_dir = (
        Path(args.output) if args.output else Path.cwd() / DEFAULT_OUTPUT_ROOT / repository_name
    )

    backend: ImageGenerationBackend | None = None
    if args.mode == "prompt-to-image":
        backend = _build_backend(args.backend)
        if isinstance(backend, OpenAICompatibleBackend) and not backend.api_key:
            return _error(
                f"missing API key for image generation backend; set {API_KEY_ENV} "
                "or use --backend fake"
            )
    elif args.backend is not None:
        return _error("--backend applies only to --mode prompt-to-image")

    written, state, profile = _analyze(repo_path, repository_name, output_dir)

    if args.mode == "live":
        artifacts = render_live(
            profile,
            mode=args.representation,
            repository_name=repository_name,
            output_dir=output_dir,
        )
        written.extend(
            path for path in (artifacts.json_path, artifacts.html_path) if path is not None
        )
    else:
        if backend is None:
            return _error("image generation backend is not configured")
        artifacts = render_prompt(
            state,
            profile,
            mode=args.representation,
            backend=backend,
            repository_name=repository_name,
            output_dir=output_dir,
        )
        written.extend(
            path for path in (artifacts.image_path, artifacts.prompt_path) if path is not None
        )
    _report_written(written)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gitgeist",
        description="Emotional repository portrait system.",
    )
    parser.add_argument("--version", action="version", version=f"gitgeist {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(
        "analyze", help="analyze a repository and write profile.json and summary.md"
    )
    analyze.add_argument("repo_path", help="path to the repository directory")
    analyze.add_argument(
        "-o",
        "--output",
        help=(
            "artifact output directory "
            f"(default: ./{DEFAULT_OUTPUT_ROOT}/<repository_name> in the current working directory)"
        ),
    )
    analyze.set_defaults(func=command_analyze)

    render = subparsers.add_parser(
        "render",
        help="analyze a repository and render live or prompt-to-image artifacts",
    )
    render.add_argument("repo_path", help="path to the repository directory")
    render.add_argument(
        "--representation", required=True, choices=REPRESENTATION_MODES, help="representation mode"
    )
    render.add_argument(
        "--mode", required=True, choices=GENERATION_MODES, help="generation mode"
    )
    render.add_argument(
        "-o",
        "--output",
        help=(
            "artifact output directory "
            f"(default: ./{DEFAULT_OUTPUT_ROOT}/<repository_name> in the current working directory)"
        ),
    )
    render.add_argument(
        "--backend",
        default=None,
        choices=BACKEND_CHOICES,
        help="image generation backend for --mode prompt-to-image (default: fake)",
    )
    render.set_defaults(func=command_render)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        return _error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
