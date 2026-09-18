"""Documentation and metadata ingestor."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocsSummaryResult:
    """Raw result of documentation and license analysis."""

    has_readme: bool
    readme_length_chars: int
    readme_snippet: str
    license_type: str | None


def _detect_license_type(content: str) -> str:
    """Detect license type from file content using standard identifiers."""
    upper = content.upper()
    if "APACHE LICENSE" in upper and ("VERSION 2.0" in upper or "2.0" in upper):
        return "Apache-2.0"
    if "MIT LICENSE" in upper or "PERMISSION IS HEREBY GRANTED, FREE OF CHARGE" in upper:
        return "MIT"
    if "GNU LESSER GENERAL PUBLIC LICENSE" in upper:
        return "LGPL"
    if "GNU GENERAL PUBLIC LICENSE" in upper:
        if "VERSION 3" in upper:
            return "GPL-3.0"
        if "VERSION 2" in upper:
            return "GPL-2.0"
        return "GPL"
    if "BSD 3-CLAUSE" in upper:
        return "BSD-3-Clause"
    if "BSD 2-CLAUSE" in upper:
        return "BSD-2-Clause"
    if "MOZILLA PUBLIC LICENSE" in upper:
        return "MPL-2.0"
    if "THE UNLICENSE" in upper:
        return "Unlicense"
    return "Custom"


def _find_candidate_file(root_path: Path, candidates: list[str]) -> Path | None:
    """Find the highest-priority candidate file existing in root_path."""
    try:
        existing_files: dict[str, Path] = {}
        for item in sorted(root_path.iterdir()):
            if item.is_file():
                existing_files.setdefault(item.name.lower(), item)
    except OSError:
        return None

    for cand in candidates:
        cand_lower = cand.lower()
        if cand_lower in existing_files:
            return existing_files[cand_lower]
    return None


def extract_docs_summary(root_path: Path) -> DocsSummaryResult:
    """Extract documentation characteristics and license from repository root."""
    has_readme = False
    readme_length_chars = 0
    readme_snippet = ""
    license_type: str | None = None

    # Check README in defined priority order
    readme_candidates = ["README.md", "README.rst", "README.txt", "README"]
    readme_path = _find_candidate_file(root_path, readme_candidates)

    if readme_path and readme_path.is_file():
        try:
            content = readme_path.read_text(encoding="utf-8", errors="replace")
            has_readme = True
            readme_length_chars = len(content)
            readme_snippet = content[:500].strip()
        except OSError:
            pass

    # Check LICENSE in defined priority order
    license_candidates = ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "COPYING.txt"]
    license_path = _find_candidate_file(root_path, license_candidates)

    if license_path and license_path.is_file():
        try:
            content = license_path.read_text(encoding="utf-8", errors="replace")
            license_type = _detect_license_type(content)
        except OSError:
            pass

    return DocsSummaryResult(
        has_readme=has_readme,
        readme_length_chars=readme_length_chars,
        readme_snippet=readme_snippet,
        license_type=license_type,
    )
