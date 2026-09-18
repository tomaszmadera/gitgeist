from pathlib import Path
import pytest
from gitgeist.features.static import compute_static_features
from gitgeist.ingest.repository import scan_repository_tree


def test_scan_repository_tree_ignores_special_dirs(tmp_path: Path) -> None:
    # Create valid files
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "app.py").write_text("print('app')", encoding="utf-8")

    # Create ignored dirs
    for ignored in [".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"]:
        ign_path = tmp_path / ignored
        ign_path.mkdir(parents=True)
        (ign_path / "ignored.py").write_text("print('ignored')", encoding="utf-8")

    scan = scan_repository_tree(tmp_path)
    assert scan.file_count == 1
    assert scan.directory_count == 1
    assert "src/app.py" in [p.as_posix() for p in scan.relative_file_paths]


def test_static_features_clean_modular(clean_modular_repo: Path) -> None:
    scan = scan_repository_tree(clean_modular_repo)
    features = compute_static_features(scan)

    assert features.file_count > 0
    assert features.directory_count >= 3
    assert features.max_directory_depth >= 2
    assert "Python" in features.languages
    assert "Markdown" in features.languages
    assert features.has_tests is True
    assert features.has_documentation is True
    assert features.has_ci is True
    assert features.total_size_bytes > 0
    assert features.avg_file_size_bytes > 0
    assert features.todo_count == 0


def test_static_features_legacy_chaotic(legacy_chaotic_repo: Path) -> None:
    scan = scan_repository_tree(legacy_chaotic_repo)
    features = compute_static_features(scan)

    assert features.max_directory_depth >= 5
    assert features.todo_count >= 5
    assert "Python" in features.languages
    assert "JavaScript" in features.languages or "Shell" in features.languages
    assert features.has_tests is False
    assert features.has_ci is False


def test_static_features_handles_binary_and_large_files(tmp_path: Path) -> None:
    # Binary file
    bin_file = tmp_path / "image.png"
    bin_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"TODO" * 10)

    # Text file with TODO
    txt_file = tmp_path / "code.py"
    txt_file.write_text("# TODO: handle this\n# FIXME: urgent\n", encoding="utf-8")

    scan = scan_repository_tree(tmp_path)
    features = compute_static_features(scan)

    assert features.file_count == 2
    # Binary file shouldn't corrupt TODO search or crash
    assert features.todo_count == 2


def test_scan_repository_case_insensitive_ignored_dirs(tmp_path: Path) -> None:
    # Folders with different casing
    node_mod = tmp_path / "Node_Modules"
    node_mod.mkdir()
    (node_mod / "pkg.js").write_text("console.log('ignored')", encoding="utf-8")

    dist = tmp_path / "DIST"
    dist.mkdir()
    (dist / "bundle.js").write_text("console.log('ignored')", encoding="utf-8")

    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("print('valid')", encoding="utf-8")

    scan = scan_repository_tree(tmp_path)
    assert scan.file_count == 1
    assert scan.directory_count == 1
    assert "src/app.py" in [p.as_posix() for p in scan.relative_file_paths]
