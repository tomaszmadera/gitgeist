"""End-to-end tests for the Gitgeist command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gitgeist.cli import main
from gitgeist.render.image_backend import FakeImageBackend
from gitgeist.schemas.emotional import EmotionalState
from gitgeist.schemas.features import RepositoryFeatures
from gitgeist.schemas.visual_latent import VisualLatentProfile

REQUIRED_ARTIFACTS = ("profile.json", "summary.md")
LIVE_ARTIFACTS = ("live-preview.html", "live-state.json")
PROMPT_ARTIFACTS = ("prompt.txt", "portrait.png")


def _assert_required_artifacts(output_dir: Path) -> tuple[dict, dict, dict]:
    for name in REQUIRED_ARTIFACTS:
        assert (output_dir / name).is_file(), f"missing artifact: {name}"
    data = json.loads((output_dir / "profile.json").read_text(encoding="utf-8"))
    RepositoryFeatures.model_validate(data["repository"])
    EmotionalState.model_validate(data["emotional_state"])
    VisualLatentProfile.model_validate(data["visual_latent"])
    return data["repository"], data["emotional_state"], data["visual_latent"]


def test_analyze_git_repo_writes_required_artifacts(
    clean_modular_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    code = main(["analyze", str(clean_modular_repo)])
    assert code == 0
    out_dir = tmp_path / "gitgeist-output" / clean_modular_repo.name
    _assert_required_artifacts(out_dir)
    assert not (clean_modular_repo / "gitgeist-output").exists()
    captured = capsys.readouterr()
    assert str(out_dir / "profile.json") in captured.out
    assert str(out_dir / "summary.md") in captured.out


def test_analyze_non_git_repo(non_git_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    code = main(["analyze", str(non_git_dir)])
    assert code == 0
    _repository, emotional, _visual = _assert_required_artifacts(
        tmp_path / "gitgeist-output" / non_git_dir.name
    )
    assert emotional["source_commit"] is None


def test_analyze_output_dir_override_creates_nested_dirs(
    clean_modular_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "deep" / "nested" / "out"
    code = main(["analyze", str(clean_modular_repo), "-o", str(out_dir)])
    assert code == 0
    _assert_required_artifacts(out_dir)
    assert not (tmp_path / "gitgeist-output").exists()


def test_analyze_rerun_overwrites_with_stable_summary(
    clean_modular_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "gitgeist-output" / clean_modular_repo.name
    assert main(["analyze", str(clean_modular_repo)]) == 0
    summary_first = (out_dir / "summary.md").read_text(encoding="utf-8")
    assert main(["analyze", str(clean_modular_repo)]) == 0
    assert sorted(p.name for p in out_dir.iterdir()) == sorted(REQUIRED_ARTIFACTS)
    assert (out_dir / "summary.md").read_text(encoding="utf-8") == summary_first


@pytest.mark.parametrize("representation", ["character", "abstract"])
def test_render_live_writes_mode_and_required_artifacts(
    clean_modular_repo: Path, representation: str, tmp_path: Path
) -> None:
    out_dir = tmp_path / f"live-{representation}"
    code = main(
        [
            "render",
            str(clean_modular_repo),
            "--representation",
            representation,
            "--mode",
            "live",
            "-o",
            str(out_dir),
        ]
    )
    assert code == 0
    _assert_required_artifacts(out_dir)
    for name in LIVE_ARTIFACTS:
        assert (out_dir / name).is_file(), f"missing artifact: {name}"
    state = json.loads((out_dir / "live-state.json").read_text(encoding="utf-8"))
    assert state["representation_mode"] == representation


@pytest.mark.parametrize("representation", ["character", "abstract"])
def test_render_prompt_writes_mode_and_required_artifacts(
    clean_modular_repo: Path, representation: str, tmp_path: Path
) -> None:
    out_dir = tmp_path / f"prompt-{representation}"
    code = main(
        [
            "render",
            str(clean_modular_repo),
            "--representation",
            representation,
            "--mode",
            "prompt-to-image",
            "-o",
            str(out_dir),
        ]
    )
    assert code == 0
    _assert_required_artifacts(out_dir)
    for name in PROMPT_ARTIFACTS:
        assert (out_dir / name).is_file(), f"missing artifact: {name}"
    prompt = (out_dir / "prompt.txt").read_text(encoding="utf-8")
    assert f"Representation mode: {representation}" in prompt
    assert (out_dir / "portrait.png").stat().st_size > 0


def test_render_openai_backend_without_api_key_fails_clean(
    clean_modular_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("GITGEIST_IMAGE_API_KEY", raising=False)
    out_dir = tmp_path / "should-not-exist"
    code = main(
        [
            "render",
            str(clean_modular_repo),
            "--representation",
            "character",
            "--mode",
            "prompt-to-image",
            "-o",
            str(out_dir),
            "--backend",
            "openai-compatible",
        ]
    )
    assert code == 1
    captured = capsys.readouterr()
    assert "GITGEIST_IMAGE_API_KEY" in captured.err
    assert not out_dir.exists()


class _ExplodingBackend(FakeImageBackend):
    def generate_image(self, prompt: str) -> bytes:
        raise ValueError("image backend exploded")


def test_render_backend_failure_exits_with_message(
    clean_modular_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("gitgeist.cli.FakeImageBackend", _ExplodingBackend)
    out_dir = tmp_path / "backend-failure"
    code = main(
        [
            "render",
            str(clean_modular_repo),
            "--representation",
            "character",
            "--mode",
            "prompt-to-image",
            "-o",
            str(out_dir),
        ]
    )
    assert code == 1
    captured = capsys.readouterr()
    assert "image backend exploded" in captured.err
    assert "Traceback" not in captured.err
    assert (out_dir / "prompt.txt").exists() is False
    assert (out_dir / "portrait.png").exists() is False


def test_missing_repo_path_fails_with_stderr_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["analyze", str(tmp_path / "does-not-exist")])
    assert code == 1
    captured = capsys.readouterr()
    assert "does-not-exist" in captured.err
    assert "Traceback" not in captured.err


def test_output_dir_that_is_a_file_fails_with_stderr_message(
    clean_modular_repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    code = main(["analyze", str(clean_modular_repo), "-o", str(blocker)])
    assert code == 1
    captured = capsys.readouterr()
    assert "blocker" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("backend", ["fake", "openai-compatible"])
def test_render_backend_with_live_mode_fails(
    clean_modular_repo: Path, backend: str, tmp_path: Path
) -> None:
    out_dir = tmp_path / "live-with-backend"
    code = main(
        [
            "render",
            str(clean_modular_repo),
            "--representation",
            "character",
            "--mode",
            "live",
            "--backend",
            backend,
            "-o",
            str(out_dir),
        ]
    )
    assert code == 1
    assert not out_dir.exists()


def test_render_requires_representation_and_mode(clean_modular_repo: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["render", str(clean_modular_repo)])
    assert excinfo.value.code == 2


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert "gitgeist" in capsys.readouterr().out
