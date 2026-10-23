"""Registered styles, fitting pools and variety limits."""

import pytest

from gitgeist.visual import styles


@pytest.mark.parametrize("representation,name", [("abstract", "orbits"), ("character", "creature")])
def test_registered_and_auto(representation: str, name: str) -> None:
    assert styles.registered_styles(representation) == (name,)
    for variety in ("low", "medium", "high"):
        assert styles.select_style(None, representation, "auto", variety, 123) == name
        assert styles.select_style(None, representation, name, variety, 456) == name


def test_pool_sizes_and_fit_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = {name: styles.Style("abstract", lambda f: True) for name in ("d", "b", "a", "c")}
    registry["excluded"] = styles.Style("abstract", lambda f: False)
    monkeypatch.setattr(styles, "STYLES", registry)
    for variety, expected in (("low", set("a")), ("medium", set("abc")), ("high", set("abcd"))):
        selected = {styles.select_style(None, "abstract", "auto", variety, seed) for seed in range(100)}
        assert selected == expected


def test_variety_limits() -> None:
    assert [styles.variety_limits(v) for v in ("low", "medium", "high")] == [(10, 0.02), (25, 0.05), (45, 0.10)]


@pytest.mark.parametrize("representation,style,variety", [
    ("abstract", "missing", "medium"), ("abstract", "creature", "medium"),
    ("other", "auto", "medium"), ("character", "auto", "other"),
])
def test_errors(representation: str, style: str, variety: str) -> None:
    with pytest.raises(ValueError):
        styles.select_style(None, representation, style, variety, 0)
