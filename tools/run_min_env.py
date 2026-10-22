"""Run a Python command in a deliberately minimal environment and write a raw log.

Used for red-run evidence (review/rules.md R2, R6) when the code under test can
print environment variables on failure. The child process gets only these
variables, so no real secret is in the process at all:

    SystemRoot (Windows only), PATH (this Python's directory, git's directory
    and the system binary directory), TEMP, TMP, TMPDIR, HOME and USERPROFILE
    (an empty temp directory) and PYTHONPATH (<cwd>/src).

The log file gets a header with the command, the wrapper invocation, the
directory, the commit, the date and the exit code, followed by the unedited
stdout+stderr of the command (line endings normalized to LF). No environment
value other than the paths above is written.

Example (red run of a test file in a worktree at the commit before a fix):

    python tools/run_min_env.py --cwd ../gitgeist-red --out red.txt \\
        --title "New tests at the commit before the fix" \\
        -- -m pytest -q -p no:cacheprovider tests/test_environ_isolation.py

Everything after "--" is passed to this Python interpreter. Standard library
only.
"""

from __future__ import annotations

import argparse
import datetime
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def minimal_env(cwd: Path, home: Path, tmp: Path) -> dict[str, str]:
    """Return the environment for the child process."""
    git = shutil.which("git")
    path_dirs = [str(Path(sys.executable).parent)]
    if git:
        path_dirs.append(str(Path(git).parent))
    env: dict[str, str] = {}
    if os.name == "nt":
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        env["SystemRoot"] = system_root
        path_dirs.append(str(Path(system_root) / "System32"))
    else:
        path_dirs.extend(["/usr/bin", "/bin"])
    env["PATH"] = os.pathsep.join(dict.fromkeys(path_dirs))
    env["TEMP"] = env["TMP"] = env["TMPDIR"] = str(tmp)
    env["HOME"] = env["USERPROFILE"] = str(home)
    env["PYTHONPATH"] = str(cwd / "src")
    return env


def git_head(cwd: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "(not a git checkout)"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--" not in argv:
        print("usage: run_min_env.py --cwd DIR --out FILE --title TEXT -- <python args>", file=sys.stderr)
        return 2
    split = argv.index("--")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cwd", required=True, type=Path, help="checkout to run in (its src/ goes on PYTHONPATH)")
    parser.add_argument("--out", required=True, type=Path, help="log file to write")
    parser.add_argument("--title", required=True, help="first header line of the log")
    args = parser.parse_args(argv[:split])
    child_args = argv[split + 1 :]
    if not child_args:
        parser.error("no command after --")

    cwd = args.cwd.resolve()
    with tempfile.TemporaryDirectory(prefix="gitgeist-min-env-") as base_dir:
        base = Path(base_dir)
        home, tmp = base / "home", base / "tmp"
        home.mkdir()
        tmp.mkdir()
        return _run(args, child_args, argv, cwd, minimal_env(cwd, home, tmp))


def _run(args: argparse.Namespace, child_args: list[str], argv: list[str], cwd: Path, env: dict[str, str]) -> int:

    module = subprocess.run(
        [sys.executable, "-c", "import gitgeist; print(gitgeist.__file__)"],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    ).stdout.strip() or "(gitgeist not importable)"
    started = datetime.datetime.now().astimezone()
    proc = subprocess.run([sys.executable, *child_args], cwd=cwd, env=env, capture_output=True)
    output = (proc.stdout + proc.stderr).decode("utf-8", errors="replace").replace("\r\n", "\n")

    words = ["python", "tools/run_min_env.py", *argv]
    wrapper = subprocess.list2cmdline(words) if os.name == "nt" else shlex.join(words)
    header = "\n".join(
        [
            f"# {args.title}",
            "#",
            f"# Command:   python {' '.join(child_args)}",
            f"#            (python = {sys.executable})",
            f"# Wrapper:   {wrapper}",
            f"# Directory: {cwd}",
            f"# Commit:    {git_head(cwd)}",
            f"# Date:      {started.isoformat(timespec='seconds')}",
            f"# Exit code: {proc.returncode}",
            f"# gitgeist imported from: {module}",
            "#",
            "# The environment was deliberately minimal to prevent secret leaks: the",
            f"# child process got only {', '.join(env)}.",
            "# HOME and USERPROFILE point to an empty temp directory. The output below",
            "# is the unedited stdout+stderr of the command (line endings normalized to LF).",
            "#",
            "",
        ]
    )
    args.out.write_text(header + output, encoding="utf-8", newline="\n")
    print(f"exit code: {proc.returncode} | log: {args.out}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
