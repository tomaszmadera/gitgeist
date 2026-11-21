"""Anatomy scan: raw per-file facts and the internal dependency graph of a fixture repository."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from gitgeist.ingest import anatomy
from gitgeist.ingest.anatomy import AnatomyScanError, scan_anatomy
from gitgeist.schemas.anatomy import AnatomyEdge, AnatomyFile, AnatomyScan, PythonFacts
from tests.fixtures.builder import create_anatomy_repo, create_minimal_repo, create_source_repo

EXPECTED_PATHS = [
    "app/Http/Controller.php",
    "app/Models/User.php",
    "app/license_check.php",
    "generated/schema.js",
    "legacy/helpers.php",
    "legacy/latin.php",
    "lib/acme/Acme.php",
    "src/pkg/__init__.py",
    "src/pkg/blob.py",
    "src/pkg/cli.py",
    "src/pkg/core.py",
    "tests/test_core.py",
    "web/app.ts",
    "web/dist/app.min.js",
    "web/legacy.js",
    "web/lib/format.ts",
    "web/lib/math.ts",
]

EXPECTED_EDGES = [
    ("app/Http/Controller.php", "app/Models/User.php", 2),
    ("app/Http/Controller.php", "legacy/helpers.php", 1),
    ("legacy/helpers.php", "lib/acme/Acme.php", 1),
    ("src/pkg/cli.py", "src/pkg/core.py", 3),
    ("src/pkg/core.py", "tests/test_core.py", 1),
    ("web/app.ts", "web/lib/format.ts", 1),
    ("web/app.ts", "web/lib/math.ts", 2),
    ("web/legacy.js", "web/lib/format.ts", 1),
]


@pytest.fixture(scope="module")
def scan(tmp_path_factory: pytest.TempPathFactory) -> AnatomyScan:
    return scan_anatomy(create_anatomy_repo(tmp_path_factory.mktemp("anatomy") / "repo"))


def _file(scan: AnatomyScan, path: str) -> AnatomyFile:
    return next(f for f in scan.files if f.path == path)


def test_scans_only_supported_tracked_files_outside_vendor_and_node_modules(scan: AnatomyScan) -> None:
    assert [f.path for f in scan.files] == EXPECTED_PATHS


def test_marks_test_files(scan: AnatomyScan) -> None:
    assert [f.path for f in scan.files if f.test] == ["tests/test_core.py"]


def test_marks_foreign_files_by_license_dir_min_name_and_gitattributes(scan: AnatomyScan) -> None:
    assert [f.path for f in scan.files if f.foreign] == [
        "generated/schema.js",
        "lib/acme/Acme.php",
        "web/dist/app.min.js",
    ]


def test_licence_markers_are_license_and_copying_names_that_are_not_source_files() -> None:
    paths = [
        "a/LICENSE",
        "b/LICENSE.md",
        "c/License.txt",
        "d/COPYING",
        "e/copying.lesser",
        "f/license_check.php",
        "g/LicenseService.ts",
        "h/licensing.py",
        "i/README.md",
        "LICENSE",
    ]
    assert anatomy._foreign_roots(paths) == {"a", "b", "c", "d", "e"}


def test_lines_is_newline_count_plus_one(scan: AnatomyScan) -> None:
    assert _file(scan, "app/Models/User.php").lines == 9
    assert _file(scan, "src/pkg/__init__.py").lines == 1


def test_changes_count_commits_touching_each_path(scan: AnatomyScan) -> None:
    changed_twice = {f.path for f in scan.files if f.changes == 2}
    assert changed_twice == {"app/Models/User.php", "web/app.ts"}
    assert all(f.changes == 1 for f in scan.files if f.path not in changed_twice)


def test_line_years_come_from_blame(scan: AnatomyScan) -> None:
    assert _file(scan, "app/Models/User.php").line_years == {2019: 7, 2024: 1}
    assert _file(scan, "web/app.ts").line_years == {2019: 6, 2024: 1}
    assert _file(scan, "legacy/helpers.php").line_years == {2019: 10}
    assert _file(scan, "src/pkg/__init__.py").line_years == {}


def test_non_utf8_text_is_blamed(scan: AnatomyScan) -> None:
    latin = _file(scan, "legacy/latin.php")
    assert latin.unblamed is False
    assert latin.line_years == {2019: 3}


def test_only_binary_files_are_unblamed_and_counted(scan: AnatomyScan) -> None:
    unblamed = [f.path for f in scan.files if f.unblamed]
    assert unblamed == ["src/pkg/blob.py"]
    assert scan.unblamed == 1
    assert _file(scan, "src/pkg/blob.py").line_years == {}
    assert _file(scan, "src/pkg/blob.py").facts == PythonFacts(language="python", functions=0, annotated_functions=0)


def test_php_facts(scan: AnatomyScan) -> None:
    helpers = _file(scan, "legacy/helpers.php").facts.model_dump()
    assert helpers == {
        "language": "php",
        "namespace": False,
        "strict_types": False,
        "superglobals": 2,
        "globals": 1,
        "deprecated_calls": 2,
        "includes": 1,
    }
    controller = _file(scan, "app/Http/Controller.php").facts.model_dump()
    assert controller["namespace"] is True
    assert controller["strict_types"] is True
    assert controller["includes"] == 1
    user = _file(scan, "app/Models/User.php").facts.model_dump()
    assert (user["namespace"], user["strict_types"], user["superglobals"]) == (True, False, 1)
    # Non-UTF-8 text is still read for facts.
    assert _file(scan, "legacy/latin.php").facts.model_dump()["globals"] == 1


def test_script_facts(scan: AnatomyScan) -> None:
    facts = {f.path: f.facts.model_dump() for f in scan.files if f.facts.language in ("typescript", "javascript")}
    assert facts["web/lib/math.ts"] == {"language": "typescript", "typed": True, "loose_marks": 2}
    assert facts["web/app.ts"] == {"language": "typescript", "typed": True, "loose_marks": 1}
    assert facts["web/legacy.js"] == {"language": "javascript", "typed": False, "loose_marks": 0}


def test_python_facts_count_defs_with_and_without_return_annotation(scan: AnatomyScan) -> None:
    assert _file(scan, "src/pkg/core.py").facts.model_dump() == {
        "language": "python",
        "functions": 2,
        "annotated_functions": 1,
    }
    # A signature split over several lines is still annotated.
    assert _file(scan, "src/pkg/cli.py").facts.model_dump()["annotated_functions"] == 1


def test_edges_per_language_with_reference_count_weights(scan: AnatomyScan) -> None:
    assert [(e.source, e.target, e.weight) for e in scan.edges] == EXPECTED_EDGES


def test_unresolved_references_count_external_and_dynamic(scan: AnatomyScan) -> None:
    # Psr\Log\LoggerInterface, include $dynamic, 'react', os, require(name), import(`./locale/${lang}`).
    assert scan.unresolved_references == 6


def test_scan_is_deterministic(scan: AnatomyScan, tmp_path: Path) -> None:
    again = scan_anatomy(create_anatomy_repo(tmp_path / "repo"))
    assert again.model_dump_json() == scan.model_dump_json()


def test_tsconfig_without_strict_leaves_typescript_untyped(tmp_path: Path) -> None:
    repo = create_minimal_repo(tmp_path / "repo")
    (repo / "tsconfig.json").write_text('{"compilerOptions": {}}\n', encoding="utf-8")
    (repo / "a.ts").write_text("export const a = 1;\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "ts"],
        cwd=repo,
        check=True,
    )
    result = scan_anatomy(repo)
    assert _file(result, "a.ts").facts.model_dump() == {"language": "typescript", "typed": False, "loose_marks": 0}


def test_not_a_repository_raises(tmp_path: Path) -> None:
    with pytest.raises(AnatomyScanError, match="not a Git repository"):
        scan_anatomy(tmp_path)


def test_repository_without_commits_raises(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    with pytest.raises(AnatomyScanError, match="no commits"):
        scan_anatomy(tmp_path)


def test_blame_failure_names_the_file_and_git_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = create_minimal_repo(tmp_path / "repo")
    real_run = subprocess.run

    def failing_blame(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if "blame" in args:
            return subprocess.CompletedProcess(args, 128, b"", b"fatal: simulated blame error\n")
        return real_run(args, **kwargs)

    monkeypatch.setattr(anatomy.subprocess, "run", failing_blame)
    with pytest.raises(AnatomyScanError, match=r"helper\.py.*simulated blame error"):
        scan_anatomy(repo)


def test_git_timeout_names_the_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = create_minimal_repo(tmp_path / "repo")
    real_run = subprocess.run

    def slow_blame(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if "blame" in args:
            assert kwargs["timeout"] == 120
            raise subprocess.TimeoutExpired(args, 120)
        return real_run(args, **kwargs)

    monkeypatch.setattr(anatomy.subprocess, "run", slow_blame)
    with pytest.raises(AnatomyScanError, match=r"helper\.py.*120 s"):
        scan_anatomy(repo)


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (subprocess.TimeoutExpired(["git"], 120), r"rev-parse.*120 s"),
        (FileNotFoundError("git"), "git is not installed"),
    ],
)
def test_head_probe_errors_are_scan_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception, message: str
) -> None:
    repo = create_minimal_repo(tmp_path / "repo")
    real_run = subprocess.run

    def failing_head(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if "--verify" in args:
            raise error
        return real_run(args, **kwargs)

    monkeypatch.setattr(anatomy.subprocess, "run", failing_head)
    with pytest.raises(AnatomyScanError, match=message):
        scan_anatomy(repo)


def test_missing_git_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    with pytest.raises(AnatomyScanError, match="git is not installed"):
        scan_anatomy(tmp_path)


def test_schema_rejects_unknown_fields_and_inconsistent_scans() -> None:
    with pytest.raises(ValidationError):
        AnatomyEdge(source="b", target="a", weight=1)
    with pytest.raises(ValidationError):
        AnatomyScan(files=[], edges=[AnatomyEdge(source="a", target="b", weight=1)], unresolved_references=0, unblamed=0)
    with pytest.raises(ValidationError):
        AnatomyScan.model_validate({"files": [], "edges": [], "unresolved_references": 0, "unblamed": 0, "x": 1})


def test_scan_round_trips_through_json(scan: AnatomyScan) -> None:
    assert AnatomyScan.model_validate_json(scan.model_dump_json()) == scan


def _edges(scan: AnatomyScan) -> list[tuple[str, str, int]]:
    return [(e.source, e.target, e.weight) for e in scan.edges]


# --- PHP code view: comments, strings and inline HTML are not code (F1) ---


def test_php_comments_strings_and_inline_html_create_no_references(tmp_path: Path) -> None:
    repo = create_source_repo(
        tmp_path / "repo",
        {
            "app/User.php": "<?php\nnamespace App;\nclass User {}\n",
            "app/Svc.php": (
                "<h1>Create a new user, include the header</h1>\n"
                "<?php\n"
                "namespace App;\n"
                "// Create a new user\n"
                "# include the header\n"
                "/**\n"
                " * Returns a new connection.\n"
                " * global $db; mysql_query($q); $_GET User::x\n"
                " */\n"
                "class Svc\n"
                "{\n"
                "    public function label() { return 'new account' . \"require User::x\" . 'mysql_query($q)'; }\n"
                "    public function text() { return <<<EOT\n"
                "    new User and include 'x.php'\n"
                "    EOT;\n"
                "    }\n"
                "}\n"
                "?>\n"
                "<p>new User() :: include it</p>\n"
            ),
        },
    )
    result = scan_anatomy(repo)
    assert result.edges == []
    assert result.unresolved_references == 0
    facts = _file(result, "app/Svc.php").facts.model_dump()
    assert (facts["includes"], facts["globals"], facts["deprecated_calls"], facts["superglobals"]) == (0, 0, 0, 0)


def test_php_include_literals_and_interpolated_superglobals_still_count(tmp_path: Path) -> None:
    repo = create_source_repo(
        tmp_path / "repo",
        {
            "lib/helpers.php": "<?php\nfunction h() {}\n",
            "app/page.php": (
                "<?php\n"
                "require_once __DIR__ . '/../lib/helpers.php';\n"
                "$x = include('lib/helpers.php');\n"
                "function load() { return require 'lib/helpers.php'; }\n"
                "echo \"Hello $_GET[name]\";\n"
                "#[Attribute]\n"
                "class Page { public function include() {} }\n"
                "?>\n"
                "<p>html</p>\n"
                "<?php include 'lib/helpers.php'; ?>\n"
            ),
        },
    )
    result = scan_anatomy(repo)
    facts = _file(result, "app/page.php").facts.model_dump()
    assert (facts["includes"], facts["superglobals"]) == (4, 1)
    assert _edges(result) == [("app/page.php", "lib/helpers.php", 4)]
    assert result.unresolved_references == 0


def test_php_short_open_tag_is_code_and_xml_declaration_is_html(tmp_path: Path) -> None:
    repo = create_source_repo(
        tmp_path / "repo",
        {
            "b.php": "<?php\nclass B {}\n",
            "a.php": "<?xml version=\"1.0\"?>\n<p>new B</p>\n<? include 'b.php'; $x = new B(); ?>\n",
        },
    )
    result = scan_anatomy(repo)
    assert _edges(result) == [("a.php", "b.php", 2)]
    assert result.unresolved_references == 0
    assert _file(result, "a.php").facts.model_dump()["includes"] == 1


# --- PHP resolution (F4) ---


def test_php_extends_implements_and_instanceof_resolve(tmp_path: Path) -> None:
    repo = create_source_repo(
        tmp_path / "repo",
        {
            "src/Base.php": "<?php\nnamespace App;\nclass Base {}\n",
            "src/Shape.php": "<?php\nnamespace App;\ninterface Shape {}\n",
            "src/Other.php": "<?php\nnamespace App;\nclass Other {}\n",
            "src/Circle.php": (
                "<?php\n"
                "namespace App;\n"
                "class Circle extends Base implements Shape\n"
                "{\n"
                "    public function same($o) { return $o instanceof Other; }\n"
                "}\n"
            ),
        },
    )
    result = scan_anatomy(repo)
    assert _edges(result) == [
        ("src/Base.php", "src/Circle.php", 1),
        ("src/Circle.php", "src/Other.php", 1),
        ("src/Circle.php", "src/Shape.php", 1),
    ]
    assert result.unresolved_references == 0


def test_php_ambiguous_short_class_name_is_unresolved(tmp_path: Path) -> None:
    repo = create_source_repo(
        tmp_path / "repo",
        {
            "a/Dup.php": "<?php\nnamespace A;\nclass Dup {}\n",
            "b/Dup.php": "<?php\nnamespace B;\nclass Dup {}\n",
            "c.php": "<?php\n$d = new Dup();\n",
        },
    )
    result = scan_anatomy(repo)
    assert result.edges == []
    assert result.unresolved_references == 1


def test_php_tied_include_suffix_is_unresolved(tmp_path: Path) -> None:
    repo = create_source_repo(
        tmp_path / "repo",
        {
            "a/x.php": "<?php\n",
            "b/x.php": "<?php\n",
            "c.php": "<?php\nrequire 'x.php';\n",
        },
    )
    result = scan_anatomy(repo)
    assert result.edges == []
    assert result.unresolved_references == 1


def test_self_references_create_no_edge(tmp_path: Path) -> None:
    repo = create_source_repo(
        tmp_path / "repo",
        {"a/Node.php": "<?php\nnamespace A;\nclass Node { public function next() { return new Node(); } }\n"},
    )
    result = scan_anatomy(repo)
    assert result.edges == []
    assert result.unresolved_references == 0


# --- TypeScript / JavaScript (F2, F4) ---


def test_script_index_resolution_and_dynamic_calls(tmp_path: Path) -> None:
    repo = create_source_repo(
        tmp_path / "repo",
        {
            "web/lib/index.ts": "export const a = 1;\n",
            "web/main.ts": (
                "import { a } from './lib';\n"
                "const b = require(name);\n"
                "const c = import(`./locale/${lang}`);\n"
                "const d = import(pick());\n"
            ),
        },
    )
    result = scan_anatomy(repo)
    assert _edges(result) == [("web/lib/index.ts", "web/main.ts", 1)]
    assert result.unresolved_references == 3


def test_script_comments_and_strings_create_no_references(tmp_path: Path) -> None:
    repo = create_source_repo(
        tmp_path / "repo",
        {
            "b.ts": "export const b = 1;\n",
            "a.ts": (
                "// import { b } from './b';\n"
                "/* const c = require('./b'); */\n"
                "const s = \"import x from './b'\";\n"
                "// Call require() lazily, then import() the chunk\n"
            ),
        },
    )
    result = scan_anatomy(repo)
    assert result.edges == []
    assert result.unresolved_references == 0


def test_script_code_view_keeps_real_references_templates_and_regex_literals(tmp_path: Path) -> None:
    repo = create_source_repo(
        tmp_path / "repo",
        {
            "b.ts": "export const b = 1;\n",
            "a.ts": (
                "import { b } from './b'; // @ts-ignore import('./b')\n"
                "const c = require('./b');\n"
                "const t = `require('./b') ${import('./b')} import(x)`;\n"
                "const re = /require\\(|import\\(\"/g;\n"
                "const half = b / 2 / 1; const q = 'it\\'s /';\n"
                "const d = import(pick());\n"
            ),
        },
    )
    result = scan_anatomy(repo)
    assert _edges(result) == [("a.ts", "b.ts", 3)]
    assert result.unresolved_references == 1
    assert _file(result, "a.ts").facts.model_dump()["loose_marks"] == 1


# --- Classification and file selection (F4) ---


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("app/UserTest.php", True),
        ("web/app.test.ts", True),
        ("web/app.spec.js", True),
        ("pkg/core_test.py", True),
        ("spec/models/user.rb.php", True),
        ("web/__tests__/app.ts", True),
        ("app/User.php", False),
        ("web/testing.ts", False),
    ],
)
def test_is_test(path: str, expected: bool) -> None:
    assert anatomy._is_test(path) is expected


@pytest.mark.parametrize(
    ("path", "all_paths", "expected"),
    [
        ("pkg/src/a.php", ["pkg/composer.json"], True),
        ("js/lib/a.js", ["js/package.json"], True),
        ("composer/a.php", ["composer.json"], False),
        ("src/third_party/a.py", [], True),
        ("src/third-party/a.py", [], True),
        ("src/party/a.py", [], False),
    ],
)
def test_is_foreign(path: str, all_paths: list[str], expected: bool) -> None:
    assert anatomy._is_foreign(path, anatomy._foreign_roots([*all_paths, path]), set()) is expected


def test_untracked_files_are_not_scanned(tmp_path: Path) -> None:
    repo = create_source_repo(tmp_path / "repo", {"a.py": "x = 1\n"})
    (repo / "b.py").write_text("import a\n", encoding="utf-8")
    result = scan_anatomy(repo)
    assert [f.path for f in result.files] == ["a.py"]


# --- Git environment and errors (F3, F4) ---


def test_user_and_system_git_config_do_not_change_the_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = create_anatomy_repo(tmp_path / "repo")
    clean = scan_anatomy(repo)
    hostile = tmp_path / "hostile.gitconfig"
    hostile.write_text(
        "[log]\n\tshowRoot = false\n[blame]\n\tignoreRevsFile = missing-revs\n"
        f"[core]\n\tattributesFile = {tmp_path / 'attrs'}\n",
        encoding="utf-8",
    )
    (tmp_path / "attrs").write_text("*.php linguist-vendored\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(hostile))
    assert scan_anatomy(repo).model_dump_json() == clean.model_dump_json()


def test_git_log_failure_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = create_minimal_repo(tmp_path / "repo")
    real_run = subprocess.run

    def failing_log(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if "log" in args:
            return subprocess.CompletedProcess(args, 128, b"", b"fatal: simulated log error\n")
        return real_run(args, **kwargs)

    monkeypatch.setattr(anatomy.subprocess, "run", failing_log)
    with pytest.raises(AnatomyScanError, match=r"git log.*simulated log error"):
        scan_anatomy(repo)
