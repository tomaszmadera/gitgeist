"""Tests for the dev tool tools/build_quantile_table.py (offline, local fixtures)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from gitgeist.normalization import QuantileTable

_TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_quantile_table.py"
_spec = importlib.util.spec_from_file_location("build_quantile_table", _TOOL)
builder = importlib.util.module_from_spec(_spec)
sys.modules["build_quantile_table"] = builder
_spec.loader.exec_module(builder)

REFERENCE_TIME = "2026-04-01T00:00:00Z"


def _head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _corpus(tmp_path: Path, entries: dict[str, str]) -> Path:
    corpus = tmp_path / "corpus.toml"
    corpus.write_text(
        "".join(
            f'[[repository]]\nname = "{name}"\nurl = "https://example.invalid/{name}"\ncommit = "{commit}"\n\n'
            for name, commit in entries.items()
        ),
        encoding="utf-8",
    )
    return corpus


def _build(corpus: Path, out: Path, *repos: str, reference_time: str = REFERENCE_TIME) -> int:
    return builder.main(
        ["build", "--corpus", str(corpus), "--reference-time", reference_time, "--out", str(out), *repos]
    )


@pytest.fixture
def two_repos(minimal_repo: Path, legacy_chaotic_repo: Path, tmp_path: Path) -> tuple[Path, list[str]]:
    corpus = _corpus(tmp_path, {"minimal": _head(minimal_repo), "legacy": _head(legacy_chaotic_repo)})
    return corpus, [f"minimal={minimal_repo}", f"legacy={legacy_chaotic_repo}"]


def test_build_is_byte_identical_and_valid(two_repos: tuple[Path, list[str]], tmp_path: Path) -> None:
    corpus, repos = two_repos
    first, second = tmp_path / "first.json", tmp_path / "second.json"

    assert _build(corpus, first, *repos) == 0
    assert _build(corpus, second, *repos) == 0

    content = first.read_bytes()
    assert content == second.read_bytes()
    assert content.endswith(b"}\n")
    assert b"\r\n" not in content
    table = QuantileTable.model_validate_json(content)
    assert table.table_version == "1"
    assert [entry.name for entry in table.corpus] == ["minimal", "legacy"]
    assert table.reference_time.isoformat() == "2026-04-01T00:00:00+00:00"
    # Two repositories: the 0.00 point is the smaller u, the 1.00 point the larger.
    assert table.inputs["depth"][0] == 0.0
    assert table.inputs["depth"][20] == pytest.approx(0.778151, abs=1e-6)  # log10(5 + 1)


def test_quantiles_interpolate_linearly() -> None:
    assert builder.quantiles([4.0, 0.0, 2.0], 5) == [0.0, 1.0, 2.0, 3.0, 4.0]


def _assert_failed(code: int, out: Path, capsys: pytest.CaptureFixture[str], *fragments: str) -> None:
    assert code == 1
    assert not out.exists()
    err = capsys.readouterr().err
    for fragment in fragments:
        assert fragment in err


def test_missing_name_path_fails(
    two_repos: tuple[Path, list[str]], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus, repos = two_repos
    out = tmp_path / "table.json"

    _assert_failed(_build(corpus, out, repos[0]), out, capsys, "legacy", "no NAME=PATH")


def test_unknown_name_fails(
    two_repos: tuple[Path, list[str]], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus, repos = two_repos
    out = tmp_path / "table.json"

    _assert_failed(_build(corpus, out, *repos, f"extra={tmp_path}"), out, capsys, "extra", "not in the corpus")


def test_head_other_than_pinned_commit_fails(
    minimal_repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = _corpus(tmp_path, {"minimal": "0" * 40})
    out = tmp_path / "table.json"

    _assert_failed(_build(corpus, out, f"minimal={minimal_repo}"), out, capsys, "minimal", "pinned commit")


def test_dirty_working_tree_fails(
    two_repos: tuple[Path, list[str]], legacy_chaotic_repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus, repos = two_repos
    (legacy_chaotic_repo / "untracked.py").write_text("x = 1\n", encoding="utf-8")
    out = tmp_path / "table.json"

    _assert_failed(_build(corpus, out, *repos), out, capsys, "legacy", "not clean")


def test_path_that_is_not_a_repository_fails(
    non_git_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = _corpus(tmp_path, {"plain": "0" * 40})
    out = tmp_path / "table.json"

    _assert_failed(_build(corpus, out, f"plain={non_git_dir}"), out, capsys, "plain", "not the root of a Git repository")


def test_reference_time_without_zone_fails(
    two_repos: tuple[Path, list[str]], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus, repos = two_repos
    out = tmp_path / "table.json"

    _assert_failed(
        _build(corpus, out, *repos, reference_time="2026-04-01T00:00:00"), out, capsys, "--reference-time", "no time zone"
    )


def test_write_error_fails(two_repos: tuple[Path, list[str]], tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    corpus, repos = two_repos
    out = tmp_path / "missing-dir" / "table.json"

    _assert_failed(_build(corpus, out, *repos), out, capsys, "cannot write")
