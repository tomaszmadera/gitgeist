"""Tests for tools/run_min_env.py, the minimal-environment wrapper for red runs.

The tests start the wrapper as a subprocess, the way it is used for evidence
logs. The child process is a small probe script that reports which variable
names it got and a few values the wrapper itself sets (temp paths). No test
reads, asserts on or prints a value from the real environment.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WRAPPER = REPO / "tools" / "run_min_env.py"
SENTINEL = "GITGEIST_TEST_WRAPPER_SENTINEL"
DOTENV_SENTINEL = "GITGEIST_TEST_DOTENV_SENTINEL"

# Names the child may see (upper-cased: Windows reports environment names in
# upper case). All but LC_CTYPE come from the wrapper; Python itself sets
# LC_CTYPE in the child under the C locale (PEP 538 locale coercion).
ALLOWED_NAMES = {
    "LC_CTYPE",
    "SYSTEMROOT",
    "PATH",
    "TEMP",
    "TMP",
    "TMPDIR",
    "HOME",
    "USERPROFILE",
    "PYTHONPATH",
    "GITGEIST_ENV_FILE",
}

PROBE = f"""\
import json, os, sys
sys.path.insert(0, sys.argv[1])
from gitgeist.env import load_dotenv
home = os.environ.get("HOME", "")
env_file = os.environ.get("GITGEIST_ENV_FILE")
loaded = load_dotenv()
print("PROBE " + json.dumps({{
    "names": sorted(os.environ),
    "sentinel": {SENTINEL!r} in os.environ,
    "dotenv_sentinel": {DOTENV_SENTINEL!r} in os.environ,
    "home": home,
    "home_is_dir": os.path.isdir(home),
    "env_file": env_file,
    "env_file_exists": env_file is not None and os.path.exists(env_file),
    "dotenv_loaded": loaded,
}}))
"""


def _quote(words: list[str]) -> str:
    return subprocess.list2cmdline(words) if os.name == "nt" else shlex.join(words)


def _run_wrapper(tmp_path: Path, child_args: list[str], cwd: Path = REPO) -> tuple[subprocess.CompletedProcess[str], str, list[str]]:
    out = tmp_path / "log.txt"
    argv = [str(WRAPPER), "--cwd", str(cwd), "--out", str(out), "--title", "wrapper test", "--", *child_args]
    proc = subprocess.run([sys.executable, *argv], cwd=REPO, capture_output=True, text=True, timeout=120)
    assert out.is_file(), proc.stderr
    return proc, out.read_text(encoding="utf-8"), argv


def _probe(tmp_path: Path, cwd: Path = REPO) -> tuple[dict, str]:
    script = tmp_path / "probe.py"
    script.write_text(PROBE, encoding="utf-8")
    proc, log, _ = _run_wrapper(tmp_path, [str(script), str(REPO / "src")], cwd=cwd)
    assert proc.returncode == 0, log
    line = next(row for row in log.splitlines() if row.startswith("PROBE "))
    return json.loads(line[len("PROBE ") :]), log


def test_child_gets_only_the_minimal_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SENTINEL, "must-not-reach-the-child")

    data, _ = _probe(tmp_path)

    assert data["sentinel"] is False
    assert {name.upper() for name in data["names"]} <= ALLOWED_NAMES


def test_temp_home_is_created_for_the_run_and_removed_afterwards(tmp_path: Path) -> None:
    data, _ = _probe(tmp_path)

    assert data["home_is_dir"] is True
    assert "gitgeist-min-env-" in data["home"]
    assert not Path(data["home"]).exists()


def test_gitgeist_env_file_points_at_a_missing_file(tmp_path: Path) -> None:
    data, _ = _probe(tmp_path)

    assert data["env_file"] is not None
    assert data["env_file_exists"] is False


def test_dotenv_in_cwd_is_not_loaded(tmp_path: Path) -> None:
    # gitgeist searches for .env upward from the working directory unless
    # GITGEIST_ENV_FILE is set (src/gitgeist/env.py, load_dotenv). The wrapper
    # must block that search, or a real .env next to --cwd reaches the child.
    project = tmp_path / "project"
    project.mkdir()
    (project / ".env").write_text(f"{DOTENV_SENTINEL}=from-a-dotenv-file\n", encoding="utf-8")

    data, _ = _probe(tmp_path, cwd=project)

    assert data["dotenv_loaded"] is False
    assert data["dotenv_sentinel"] is False


def test_header_records_the_real_invocation(tmp_path: Path) -> None:
    child_args = ["-c", "print('hello from the child')"]

    _, log, argv = _run_wrapper(tmp_path, child_args)

    header = log.splitlines()
    assert f"# Wrapper:   {_quote(['python', *argv])}" in header
    assert f"# Command:   {_quote(['python', *child_args])}" in header
    assert "hello from the child" in log


def test_exit_code_of_the_child_is_propagated(tmp_path: Path) -> None:
    proc, log, _ = _run_wrapper(tmp_path, ["-c", "import sys; sys.exit(3)"])

    assert proc.returncode == 3
    assert "# Exit code: 3" in log.splitlines()
