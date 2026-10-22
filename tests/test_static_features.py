from pathlib import Path
import pytest
from gitgeist.features.static import compute_static_features
from gitgeist.ingest.repository import is_test_path, scan_repository_tree


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


def test_scan_repository_tree_skips_default_output_dir(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('app')", encoding="utf-8")
    output_dir = tmp_path / "gitgeist-output" / tmp_path.name
    output_dir.mkdir(parents=True)
    (output_dir / "summary.md").write_text("# TODO: earlier run\n", encoding="utf-8")
    (output_dir / "profile.json").write_text("{}", encoding="utf-8")

    scan = scan_repository_tree(tmp_path)

    assert [p.as_posix() for p in scan.relative_file_paths] == ["app.py"]
    assert scan.directory_count == 0
    assert scan.todo_count == 0


def _shares(features) -> list[tuple[str, int, float]]:
    return [(s.name, s.file_count, s.share) for s in features.language_shares]


def test_static_v2_minimal(minimal_repo: Path) -> None:
    features = compute_static_features(scan_repository_tree(minimal_repo))

    assert features.code_bytes == 65
    assert features.code_file_count == 2
    assert features.test_ratio == 0.0
    assert features.doc_ratio == 0.0
    assert features.top_level_directory_count == 0
    assert _shares(features) == [("Python", 2, 1.0)]


def test_static_v2_clean_modular(clean_modular_repo: Path) -> None:
    features = compute_static_features(scan_repository_tree(clean_modular_repo))

    assert features.code_file_count == 4
    assert features.test_file_count == 2
    assert features.test_ratio == 0.5
    assert features.doc_ratio == 0.2857
    assert features.top_level_directory_count == 4
    assert _shares(features) == [("Python", 4, 0.5714), ("Markdown", 2, 0.2857), ("YAML", 1, 0.1429)]


def test_static_v2_legacy_chaotic(legacy_chaotic_repo: Path) -> None:
    features = compute_static_features(scan_repository_tree(legacy_chaotic_repo))

    assert features.todo_count == 5
    assert features.todo_density == 1000.0
    assert features.test_ratio == 0.0
    assert _shares(features) == [
        ("Python", 2, 0.4),
        ("JSON", 1, 0.2),
        ("JavaScript", 1, 0.2),
        ("Shell", 1, 0.2),
    ]


def test_static_v2_wide(wide_repo: Path) -> None:
    features = compute_static_features(scan_repository_tree(wide_repo))

    assert features.code_file_count == 55
    assert features.doc_ratio == 0.0179
    assert features.top_level_directory_count == 10


def test_language_shares_keep_top_five(tmp_path: Path) -> None:
    for ext in (".py", ".js", ".ts", ".go", ".rs", ".c"):
        (tmp_path / f"file{ext}").write_text("x\n", encoding="utf-8")
    (tmp_path / "extra.py").write_text("x\n", encoding="utf-8")

    features = compute_static_features(scan_repository_tree(tmp_path))

    assert [s.name for s in features.language_shares] == ["Python", "C", "Go", "JavaScript", "Rust"]
    assert features.language_shares[0].share == 0.2857


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("testes/a.c", True),
        ("spec/a_spec.rb", True),
        ("src/foo_test.py", True),
        ("latest/x.py", True),  # documented false positive of the "test" substring
        ("src/contest.py", False),  # the substring in the file name does not count
        ("README.md", False),
    ],
)
def test_is_test_path(path: str, expected: bool) -> None:
    assert is_test_path(path) is expected


def test_large_code_file_counts_bytes_but_not_todos(tmp_path: Path) -> None:
    big = tmp_path / "big.py"
    content = b"# TODO: never counted\n" + b"x" * (10 * 1024 * 1024)
    big.write_bytes(content)

    features = compute_static_features(scan_repository_tree(tmp_path))

    assert features.code_bytes == len(content)
    assert features.code_file_count == 1
    assert features.todo_count == 0
    assert features.todo_density == 0.0


def test_static_v2_empty_directory(tmp_path: Path) -> None:
    features = compute_static_features(scan_repository_tree(tmp_path))

    assert features.code_bytes == 0
    assert features.test_ratio == 0.0
    assert features.doc_ratio == 0.0
    assert features.todo_density == 0.0
    assert features.language_shares == []


def test_top_level_directory_without_files_is_counted(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    (tmp_path / "only-ignored" / "node_modules").mkdir(parents=True)
    (tmp_path / "only-ignored" / "node_modules" / "x.js").write_text("x\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "app.py").write_text("x\n", encoding="utf-8")

    scan = scan_repository_tree(tmp_path)

    assert scan.top_level_directories == ["empty", "only-ignored"]
    assert compute_static_features(scan).top_level_directory_count == 2
