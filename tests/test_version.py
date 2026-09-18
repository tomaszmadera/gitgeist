import tomllib
from pathlib import Path

import gitgeist


def test_version() -> None:
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
    expected_version = pyproject["project"]["version"]
    assert gitgeist.__version__ == expected_version
    base_version = expected_version.split("-")[0]
    parts = base_version.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
