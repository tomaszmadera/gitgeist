"""Deterministic portrait traits and scene descriptions."""

from gitgeist.visual.distance import spec_distance
from gitgeist.visual.spec_builder import build_visual_spec
from gitgeist.visual.styles import registered_styles
from gitgeist.visual.traits import compute_traits

__all__ = ["compute_traits", "build_visual_spec", "registered_styles", "spec_distance"]
