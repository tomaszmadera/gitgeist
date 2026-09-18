"""Live renderers for Gitgeist portraits (Abstract and Character modes)."""

from gitgeist.render.abstract_renderer import generate_abstract_simulation
from gitgeist.render.character_renderer import generate_character_simulation
from gitgeist.render.dynamics import generate_dynamics
from gitgeist.render.facade import LiveRenderArtifacts, render_live
from gitgeist.render.html_template import generate_live_html
from gitgeist.render.palette import generate_palette

__all__ = [
    "LiveRenderArtifacts",
    "generate_abstract_simulation",
    "generate_character_simulation",
    "generate_dynamics",
    "generate_live_html",
    "generate_palette",
    "render_live",
]
