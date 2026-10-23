"""Fixed language hue families and a labelled seeded hue offset."""

from random import Random

from gitgeist.visual.styles import variety_limits

LANGUAGE_HUES: dict[str, int] = {
    "Python": 210, "JavaScript": 55, "TypeScript": 220, "HTML": 15, "CSS": 275,
    "JSON": 50, "YAML": 65, "TOML": 35, "Markdown": 170, "reStructuredText": 185,
    "Text": 150, "Shell": 110, "Go": 190, "Rust": 25, "C": 235, "C/C++ Header": 245,
    "C++": 255, "Java": 10, "Ruby": 350, "PHP": 265, "XML": 85, "SQL": 310,
}


def hue_offset(seed: int, variety: str) -> float:
    """Choose one hue offset for the whole scene, within the variety limit."""
    maximum, _ = variety_limits(variety)
    return Random(seed).uniform(-maximum, maximum)


def language_hue(language: str | None, offset: float) -> float | None:
    """Return a hue in [0, 360), or neutral when no language is known."""
    if language is None:
        return None
    if language not in LANGUAGE_HUES:
        raise ValueError(f"unknown language {language!r}")
    return (LANGUAGE_HUES[language] + offset) % 360
