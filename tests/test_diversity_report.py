"""Tests for the dev tool tools/diversity_report.py (offline, no Chrome)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_TOOL = Path(__file__).resolve().parents[1] / "tools" / "diversity_report.py"
_spec = importlib.util.spec_from_file_location("diversity_report", _TOOL)
report = importlib.util.module_from_spec(_spec)
sys.modules["diversity_report"] = report
_spec.loader.exec_module(report)


def test_symmetric_eigenvalues_of_known_matrix() -> None:
    values = report.symmetric_eigenvalues([[2.0, 1.0], [1.0, 2.0]])

    assert values == pytest.approx([3.0, 1.0])


def test_spread_of_identical_variables_is_one_dimension() -> None:
    rows = {f"r{i}": {"a": float(i), "b": 2.0 * i + 1, "c": -float(i)} for i in range(5)}

    result = report.spread(rows)

    assert result["participation_ratio"] == pytest.approx(1.0)
    assert len(result["pairs_above_0_8"]) == 3


def test_spread_of_uncorrelated_variables_counts_each_and_lists_constants() -> None:
    values = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    rows = {f"r{i}": {"a": float(a), "b": float(b), "flat": 0.5} for i, (a, b) in enumerate(values)}

    result = report.spread(rows)

    assert result["participation_ratio"] == pytest.approx(2.0)
    assert result["constant"] == ["flat"]
    assert result["pairs_above_0_8"] == []


def _solid(tmp_path: Path, name: str, colour: tuple[int, int, int]) -> Path:
    from PIL import Image

    path = tmp_path / f"{name}.png"
    Image.new("RGB", (64, 64), colour).save(path)
    return path


def test_image_distance_of_identical_images_is_zero(tmp_path: Path) -> None:
    features = report.image_features(_solid(tmp_path, "red", (220, 30, 30)))

    assert report.image_distance(features, features) == pytest.approx(0.0)


def test_image_distance_black_white_is_layout_only(tmp_path: Path) -> None:
    black = report.image_features(_solid(tmp_path, "black", (0, 0, 0)))
    white = report.image_features(_solid(tmp_path, "white", (255, 255, 255)))

    # Layout differs by 1.0 everywhere; neither image has saturated pixels.
    assert report.image_distance(black, white) == pytest.approx(2.0)


def test_image_distance_counts_hue_difference(tmp_path: Path) -> None:
    red = report.image_features(_solid(tmp_path, "red", (200, 0, 0)))
    blue = report.image_features(_solid(tmp_path, "blue", (0, 0, 200)))

    layout = (200 / 255 * 2 / 3) / 0.25 * 0.5
    assert report.image_distance(red, blue) == pytest.approx(layout + 0.5 * 2.0, abs=1e-3)


def test_distance_summary_nearest_neighbours(tmp_path: Path) -> None:
    features = {
        "a": report.image_features(_solid(tmp_path, "a", (0, 0, 0))),
        "b": report.image_features(_solid(tmp_path, "b", (10, 10, 10))),
        "c": report.image_features(_solid(tmp_path, "c", (255, 255, 255))),
    }

    summary = report.distance_summary(features)

    assert summary["closest_pair"][:2] == ["a", "b"]
    assert summary["nearest"]["c"]["closest"] == "b"
    assert len(summary["pairs"]) == 3


def test_prompt_overlap_counts_shared_and_differing_lines() -> None:
    layers = {
        "x": {"prompt_abstract": "same\nx only\nsame end"},
        "y": {"prompt_abstract": "same\ny only\nsame end"},
    }

    result = report.prompt_overlap(layers, "abstract")

    assert result["lines_identical_for_all"] == 2
    assert result["mean_differing_lines"] == 1.0


def test_frozen_copy_injects_the_clock_once(tmp_path: Path) -> None:
    html = tmp_path / "live-preview.html"
    html.write_text("<html><head><title>x</title></head><body></body></html>", encoding="utf-8")

    snapshot = report.frozen_copy(html)

    content = snapshot.read_text(encoding="utf-8")
    assert snapshot.name == "snapshot.html"
    assert content.startswith("<html><head>" + report.FROZEN_CLOCK + "<title>")
    assert "first?1:1501" in content


def test_frozen_copy_rejects_page_without_head(tmp_path: Path) -> None:
    html = tmp_path / "live-preview.html"
    html.write_text("<html><body></body></html>", encoding="utf-8")

    with pytest.raises(SystemExit, match="expected one <head>"):
        report.frozen_copy(html)


def test_run_without_images_writes_normalized_layer(
    minimal_repo: Path, legacy_chaotic_repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"

    code = report.main([
        "run", "--out", str(out), "--no-images", "--reference-time", "2026-03-16T10:00:00Z",
        f"minimal={minimal_repo}", f"legacy={legacy_chaotic_repo}",
    ])

    assert code == 0
    layers = json.loads((out / "layers.json").read_text(encoding="utf-8"))
    for layer in layers.values():
        assert set(layer["normalized"]) == {"absolute", "corpus"}
        assert layer["normalized"]["absolute"]["table_version"] is None
        assert layer["normalized"]["corpus"]["table_version"] == "1"
        assert len(layer["normalized"]["absolute"]["inputs"]) == 13
    data = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert data["reference_time"] == "2026-03-16T10:00:00+00:00"
    assert "ci" not in data["normalized"]["absolute"]
    # Both fixtures have one author: authors sits at the lower anchor without clipping.
    assert data["normalized"]["absolute"]["authors"] == {"zero_or_one": 2, "clipped": 0, "of": 2}
    markdown = (out / "report.md").read_text(encoding="utf-8")
    assert "## Normalized inputs" in markdown
    assert "| authors | 2/2 | 0/2 |" in markdown
    capsys.readouterr()


def test_extract_time_prints_positive_median(minimal_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = report.main(["extract-time", "--runs", "2", str(minimal_repo)])

    assert code == 0
    assert float(capsys.readouterr().out.strip()) > 0


def test_run_writes_traits_specs_and_correlations(minimal_repo: Path, legacy_chaotic_repo: Path,
                                                tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from gitgeist.schemas.traits import TRAIT_NAMES, Traits
    from gitgeist.schemas.visual_spec import VisualSpec

    out = tmp_path / "traits-report"
    assert report.main(["run", "--no-images", "--out", str(out), "--reference-time", "2026-04-16T00:00:00Z",
                        f"minimal={minimal_repo}", f"legacy={legacy_chaotic_repo}"]) == 0
    layers = json.loads((out / "layers.json").read_text(encoding="utf-8"))
    for layer in layers.values():
        for scale in ("absolute", "corpus"):
            traits = Traits.model_validate(layer["traits"][scale])
            assert traits.reference_time.isoformat() == "2026-04-16T00:00:00+00:00"
        assert set(layer["visual_spec"]) == {"abstract", "character"}
        for representation, data in layer["visual_spec"].items():
            spec = VisualSpec.model_validate(data)
            assert spec.representation == representation
            assert spec.traits == Traits.model_validate(layer["traits"]["absolute"])
    data = json.loads((out / "report.json").read_text(encoding="utf-8"))
    for scale in ("absolute", "corpus"):
        summary = data["traits"][scale]
        assert set(summary["correlation_matrix"]) == set(TRAIT_NAMES)
        assert summary["max_abs_r"] == pytest.approx(1.0)
        assert summary["participation_ratio"] >= 1
        assert summary["correlation_matrix"]["size"]["size"] in (None, 1)
    for representation in ("abstract", "character"):
        nearest = data["spec_distance"][representation]
        assert set(nearest["nearest"]) == {"minimal", "legacy"}
        assert nearest["minimum"] > 0
    markdown = (out / "report.md").read_text(encoding="utf-8")
    assert "## Traits" in markdown and "Maximum |r|" in markdown
    assert "Nearest-neighbour spec distance" in markdown
    assert "Correlation matrix (absolute)" in markdown and "Correlation matrix (corpus)" in markdown
    capsys.readouterr()


def test_constant_spread_is_reported_without_division_by_zero() -> None:
    result = report.spread({"a": {"size": 0.0}, "b": {"size": 0.0}})
    assert result["constant"] == ["size"]
    assert result["participation_ratio"] == 0
