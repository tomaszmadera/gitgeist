"""Static feature calculator."""

from __future__ import annotations

from gitgeist.ingest.repository import CODE_LANGUAGES, DOC_LANGUAGES, FileScanResult, is_test_path
from gitgeist.schemas.features import LanguageShare, StaticFeatures

MAX_LANGUAGE_SHARES = 5


def compute_static_features(scan: FileScanResult) -> StaticFeatures:
    """Compute StaticFeatures model from raw file tree scan result."""
    code_files = [f for f in scan.files if f.language in CODE_LANGUAGES]
    code_file_count = len(code_files)
    test_file_count = sum(1 for f in code_files if is_test_path(f.path))
    known_count = sum(1 for f in scan.files if f.language is not None)
    doc_count = sum(1 for f in scan.files if f.language in DOC_LANGUAGES)

    ranked = sorted(scan.languages.items(), key=lambda item: (-item[1], item[0]))
    language_shares = [
        LanguageShare(name=name, file_count=count, share=round(count / known_count, 4))
        for name, count in ranked[:MAX_LANGUAGE_SHARES]
    ]

    return StaticFeatures(
        file_count=scan.file_count,
        directory_count=scan.directory_count,
        max_directory_depth=scan.max_directory_depth,
        languages=scan.languages,
        total_size_bytes=scan.total_size_bytes,
        avg_file_size_bytes=scan.avg_file_size_bytes,
        has_tests=scan.has_tests,
        has_documentation=scan.has_documentation,
        has_ci=scan.has_ci,
        todo_count=scan.todo_count,
        code_bytes=sum(f.size_bytes for f in code_files),
        code_file_count=code_file_count,
        test_file_count=test_file_count,
        test_ratio=round(min(1.0, test_file_count / code_file_count), 4) if code_file_count else 0.0,
        doc_ratio=round(doc_count / known_count, 4) if known_count else 0.0,
        todo_density=round(scan.todo_count * 1000 / scan.file_count, 2) if scan.file_count else 0.0,
        top_level_directory_count=len(scan.top_level_directories),
        language_shares=language_shares,
    )
