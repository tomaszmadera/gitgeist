"""Pin the language hue table and variety bounds."""

import pytest

from gitgeist.ingest.repository import EXTENSION_LANGUAGE_MAP
from gitgeist.visual.palette import LANGUAGE_HUES, hue_offset, language_hue

EXPECTED_HUES = {
    "Python": 210, "JavaScript": 55, "TypeScript": 220, "HTML": 15, "CSS": 275,
    "JSON": 50, "YAML": 65, "TOML": 35, "Markdown": 170, "reStructuredText": 185,
    "Text": 150, "Shell": 110, "Go": 190, "Rust": 25, "C": 235, "C/C++ Header": 245,
    "C++": 255, "Java": 10, "Ruby": 350, "PHP": 265, "XML": 85, "SQL": 310,
}


def test_language_table_is_complete_and_pinned() -> None:
    assert LANGUAGE_HUES == EXPECTED_HUES
    assert set(LANGUAGE_HUES) == set(EXTENSION_LANGUAGE_MAP.values())


@pytest.mark.parametrize("variety,maximum", [("low", 10), ("medium", 25), ("high", 45)])
def test_offsets_and_wrapping(variety: str, maximum: int) -> None:
    values = [hue_offset(seed, variety) for seed in range(20)]
    assert all(-maximum <= value <= maximum for value in values)
    assert len(set(values)) == 20
    assert hue_offset(42, variety) == hue_offset(42, variety)
    assert language_hue("Ruby", 20) == 10
    assert language_hue(None, 20) is None


def test_palette_errors() -> None:
    with pytest.raises(ValueError, match="variety"):
        hue_offset(1, "missing")
    with pytest.raises(ValueError, match="language"):
        language_hue("unknown", 0)
