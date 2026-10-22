"""Regression tests for the suite-wide environment isolation in tests/conftest.py.

None of these tests puts os.environ itself in an assert: on failure pytest would
print its full contents.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

SENTINEL_NAME = "GITGEIST_TEST_SENTINEL_SECRET"
SENTINEL_VALUE = "fake-sentinel-value-not-a-real-secret"


@pytest.fixture(scope="module")
def real_environ_sentinel() -> Iterator[None]:
    # Module scope runs before the function-scoped isolated_environ fixture,
    # so this sets the sentinel in the real process environment.
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv(SENTINEL_NAME, SENTINEL_VALUE)
        yield


def test_tests_do_not_see_the_real_environment(real_environ_sentinel: None) -> None:
    sentinel_visible = SENTINEL_NAME in os.environ
    assert not sentinel_visible, "a test sees the real process environment"


def test_child_processes_do_not_see_the_real_environment(real_environ_sentinel: None) -> None:
    child = subprocess.run(
        [sys.executable, "-c", f"import os; print({SENTINEL_NAME!r} in os.environ)"],
        capture_output=True,
        text=True,
        check=True,
    )
    sentinel_visible_in_child = child.stdout.strip() == "True"
    assert not sentinel_visible_in_child, "a child process sees the real process environment"


def test_home_is_an_empty_temp_dir_and_no_env_file_is_configured() -> None:
    # os.environ.get, not os.environ[...]: a KeyError traceback would show the
    # whole mapping as a local of the os module frame.
    home_value = os.environ.get("HOME")
    env_file_value = os.environ.get("GITGEIST_ENV_FILE")
    assert home_value is not None, "HOME is not set by the isolation fixture"
    assert env_file_value is not None, "GITGEIST_ENV_FILE is not set by the isolation fixture"
    home = Path(home_value)
    assert Path.home() == home
    assert list(home.iterdir()) == []
    env_file = Path(env_file_value)
    assert env_file.parent == home
    assert not env_file.exists()
