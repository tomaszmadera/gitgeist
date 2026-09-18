"""Repository file tree ingestor."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".eggs",
    "dist",
    "build",
    ".idea",
    ".vscode",
}

BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".pyc",
    ".pyo",
    ".pyd",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp3",
    ".mp4",
    ".wav",
}

EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".txt": "Text",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".hpp": "C/C++ Header",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".xml": "XML",
    ".sql": "SQL",
}

TODO_REGEX = re.compile(r"\b(TODO|FIXME)\b")
MAX_TEXT_SCAN_BYTES = 10 * 1024 * 1024  # 10 MB


@dataclass(frozen=True)
class FileScanResult:
    """Raw scan result of repository directory tree."""

    root_path: Path
    file_count: int
    directory_count: int
    max_directory_depth: int
    languages: dict[str, int]
    total_size_bytes: int
    avg_file_size_bytes: float
    has_tests: bool
    has_documentation: bool
    has_ci: bool
    todo_count: int
    relative_file_paths: list[Path] = field(default_factory=list)


def is_binary_content(sample: bytes) -> bool:
    """Check if byte sample contains null bytes indicating binary content."""
    return b"\x00" in sample


def scan_repository_tree(root_path: Path) -> FileScanResult:
    """Deterministically scan repository directory tree and compute file metrics."""
    if not root_path.exists():
        raise FileNotFoundError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root_path}")

    file_paths: list[Path] = []
    dir_paths: set[Path] = set()
    languages: dict[str, int] = {}
    total_size_bytes = 0
    max_depth = 0
    has_tests = False
    has_documentation = False
    has_ci = False
    todo_count = 0

    for current_root, dirs, files in os.walk(root_path):
        current_path = Path(current_root)
        rel_dir = current_path.relative_to(root_path)

        # Filter out ignored directories in-place and sort deterministically
        dirs[:] = sorted([d for d in dirs if d.lower() not in IGNORED_DIRS])
        files.sort()

        if rel_dir != Path("."):
            dir_paths.add(rel_dir)
            depth = len(rel_dir.parts)
            if depth > max_depth:
                max_depth = depth

            # Detect test directory
            dir_name_lower = current_path.name.lower()
            if dir_name_lower in {"tests", "test", "__tests__", "spec"}:
                has_tests = True

            # Detect docs directory
            if dir_name_lower in {"docs", "doc", "documentation"}:
                has_documentation = True

            # Detect CI directory
            if ".github" in rel_dir.parts and "workflows" in rel_dir.parts:
                has_ci = True
            elif ".gitlab" in rel_dir.parts or ".circleci" in rel_dir.parts:
                has_ci = True

        for file_name in files:
            full_path = current_path / file_name
            rel_file = full_path.relative_to(root_path)
            file_paths.append(rel_file)

            # File size
            try:
                stat = full_path.stat()
                file_size = stat.st_size
            except OSError:
                file_size = 0
            total_size_bytes += file_size

            # Language mapping
            ext = full_path.suffix.lower()
            lang = EXTENSION_LANGUAGE_MAP.get(ext)
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

            # Detect tests by filename
            file_lower = file_name.lower()
            if (
                file_lower.startswith("test_")
                or file_lower.endswith("_test.py")
                or file_lower.endswith(".test.js")
                or file_lower.endswith(".test.ts")
                or file_lower.endswith(".spec.js")
                or file_lower.endswith(".spec.ts")
            ):
                has_tests = True

            # Detect documentation by filename
            if file_lower.startswith("readme") or ext in {".md", ".rst"}:
                has_documentation = True

            # Detect CI files at root
            if file_lower in {".gitlab-ci.yml", "azure-pipelines.yml", "jenkinsfile"}:
                has_ci = True

            # Scan TODO/FIXME in text files
            if ext not in BINARY_EXTENSIONS and file_size <= MAX_TEXT_SCAN_BYTES:
                try:
                    with open(full_path, "rb") as f:
                        header = f.read(1024)
                        if not is_binary_content(header):
                            f.seek(0)
                            content = f.read().decode("utf-8", errors="replace")
                            matches = len(TODO_REGEX.findall(content))
                            todo_count += matches
                except OSError:
                    pass

    file_count = len(file_paths)
    avg_size = (total_size_bytes / file_count) if file_count > 0 else 0.0

    return FileScanResult(
        root_path=root_path,
        file_count=file_count,
        directory_count=len(dir_paths),
        max_directory_depth=max_depth,
        languages=dict(sorted(languages.items(), key=lambda item: (-item[1], item[0]))),
        total_size_bytes=total_size_bytes,
        avg_file_size_bytes=round(avg_size, 2),
        has_tests=has_tests,
        has_documentation=has_documentation,
        has_ci=has_ci,
        todo_count=todo_count,
        relative_file_paths=file_paths,
    )
