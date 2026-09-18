"""Static feature calculator."""

from __future__ import annotations

from gitgeist.ingest.repository import FileScanResult
from gitgeist.schemas.features import StaticFeatures


def compute_static_features(scan: FileScanResult) -> StaticFeatures:
    """Compute StaticFeatures model from raw file tree scan result."""
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
    )
