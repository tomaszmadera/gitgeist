"""Live and prompt renderers for Gitgeist portraits (Abstract and Character modes)."""

from gitgeist.render.abstract_renderer import generate_abstract_simulation
from gitgeist.render.character_renderer import generate_character_simulation
from gitgeist.render.dynamics import generate_dynamics
from gitgeist.render.facade import LiveRenderArtifacts, PromptRenderArtifacts, render_live, render_prompt
from gitgeist.render.html_template import generate_live_html
from gitgeist.render.image_backend import (
    FakeImageBackend,
    GeneratedImage,
    ImageGenerationBackend,
    OpenRouterImageBackend,
    detect_media_type,
    normalize_to_png,
)
from gitgeist.render.palette import generate_palette
from gitgeist.render.prompt_composer import compose_prompt

__all__ = [
    "FakeImageBackend",
    "GeneratedImage",
    "ImageGenerationBackend",
    "LiveRenderArtifacts",
    "OpenRouterImageBackend",
    "PromptRenderArtifacts",
    "compose_prompt",
    "detect_media_type",
    "generate_abstract_simulation",
    "generate_character_simulation",
    "generate_dynamics",
    "generate_live_html",
    "generate_palette",
    "normalize_to_png",
    "render_live",
    "render_prompt",
]
