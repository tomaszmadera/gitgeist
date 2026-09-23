"""Tests for environment loading helpers in gitgeist.env."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from gitgeist.env import find_dotenv, load_dotenv, parse_dotenv, user_env_file


def test_parse_dotenv_simple_pairs() -> None:
    content = "KEY1=value1\nKEY2=value2"
    result = parse_dotenv(content)
    assert result == {"KEY1": "value1", "KEY2": "value2"}


def test_parse_dotenv_ignores_comments_and_blank_lines() -> None:
    content = """
    # This is a comment
    KEY1=value1

    # Another comment
    KEY2=value2
    """
    result = parse_dotenv(content)
    assert result == {"KEY1": "value1", "KEY2": "value2"}


def test_parse_dotenv_strips_quotes() -> None:
    content = """
    DOUBLE="double quoted string"
    SINGLE='single quoted string'
    UNQUOTED=no quotes
    """
    result = parse_dotenv(content)
    assert result["DOUBLE"] == "double quoted string"
    assert result["SINGLE"] == "single quoted string"
    assert result["UNQUOTED"] == "no quotes"


def test_parse_dotenv_strips_export_prefix() -> None:
    content = "export OPENROUTER_IMAGE_API_KEY=test-key"
    result = parse_dotenv(content)
    assert result == {"OPENROUTER_IMAGE_API_KEY": "test-key"}


def test_parse_dotenv_preserves_equals_in_value() -> None:
    content = "COMPLEX_VAL=foo=bar=baz"
    result = parse_dotenv(content)
    assert result == {"COMPLEX_VAL": "foo=bar=baz"}


def test_parse_dotenv_handles_empty_values_and_malformed_lines() -> None:
    content = """
    EMPTY=
    =invalid_no_key
    just_a_word_without_equals
    """
    result = parse_dotenv(content)
    assert result == {"EMPTY": ""}


def test_find_dotenv_in_current_dir(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar", encoding="utf-8")
    assert find_dotenv(start_dir=tmp_path) == env_file


def test_find_dotenv_in_parent_dir(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar", encoding="utf-8")
    subdir = tmp_path / "sub1" / "sub2"
    subdir.mkdir(parents=True)
    assert find_dotenv(start_dir=subdir) == env_file


def test_find_dotenv_stops_at_git_boundary(tmp_path: Path) -> None:
    # Root has .env
    (tmp_path / ".env").write_text("FOO=root", encoding="utf-8")
    # Subdir is a git repo without .env
    git_dir = tmp_path / "repo"
    (git_dir / ".git").mkdir(parents=True)
    inner_dir = git_dir / "src"
    inner_dir.mkdir()

    # Searching from inner_dir should stop at repo and not reach tmp_path / .env
    assert find_dotenv(start_dir=inner_dir) is None


def test_load_dotenv_populates_os_environ(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_VAR_A", raising=False)
    monkeypatch.delenv("TEST_VAR_B", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("TEST_VAR_A=alpha\nTEST_VAR_B=beta\n", encoding="utf-8")

    loaded = load_dotenv(path=env_file)
    assert loaded is True
    assert os.environ.get("TEST_VAR_A") == "alpha"
    assert os.environ.get("TEST_VAR_B") == "beta"


def test_load_dotenv_does_not_override_existing_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_EXISTING", "original")
    env_file = tmp_path / ".env"
    env_file.write_text("TEST_EXISTING=overwritten\n", encoding="utf-8")

    load_dotenv(path=env_file)
    assert os.environ["TEST_EXISTING"] == "original"


def test_load_dotenv_overrides_when_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_EXISTING", "original")
    env_file = tmp_path / ".env"
    env_file.write_text("TEST_EXISTING=overwritten\n", encoding="utf-8")

    load_dotenv(path=env_file, override=True)
    assert os.environ["TEST_EXISTING"] == "overwritten"


def test_load_dotenv_returns_false_when_missing(tmp_path: Path) -> None:
    non_existent = tmp_path / "no_such_file.env"
    assert load_dotenv(path=non_existent) is False


def test_load_dotenv_respects_env_override_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom_env = tmp_path / "custom.env"
    custom_env.write_text("CUSTOM_VAR=custom_val\n", encoding="utf-8")
    monkeypatch.setenv("GITGEIST_ENV_FILE", str(custom_env))
    monkeypatch.delenv("CUSTOM_VAR", raising=False)

    loaded = load_dotenv()
    assert loaded is True
    assert os.environ.get("CUSTOM_VAR") == "custom_val"


def test_user_env_file_respects_xdg_config_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/xdg/config")
    assert user_env_file() == Path("/custom/xdg/config/gitgeist/.env")


def test_user_env_file_defaults_to_home_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert user_env_file() == Path.home() / ".config" / "gitgeist" / ".env"


def test_load_dotenv_falls_back_to_user_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("USER_VAR", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    user_file = tmp_path / ".config" / "gitgeist" / ".env"
    user_file.parent.mkdir(parents=True)
    user_file.write_text("USER_VAR=from-user-file\n", encoding="utf-8")

    assert load_dotenv() is True
    assert os.environ.get("USER_VAR") == "from-user-file"


def test_load_dotenv_local_env_takes_precedence_over_user_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SHARED_VAR", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    user_file = tmp_path / ".config" / "gitgeist" / ".env"
    user_file.parent.mkdir(parents=True)
    user_file.write_text("SHARED_VAR=from-user-file\n", encoding="utf-8")

    local_dir = tmp_path / "project"
    local_dir.mkdir()
    (local_dir / ".env").write_text("SHARED_VAR=from-local-file\n", encoding="utf-8")
    monkeypatch.chdir(local_dir)

    assert load_dotenv() is True
    assert os.environ.get("SHARED_VAR") == "from-local-file"
