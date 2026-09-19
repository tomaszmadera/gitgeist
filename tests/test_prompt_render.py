"""Tests for the prompt rendering facade (render_prompt and artifacts)."""

import io
import sys
from pathlib import Path

import pytest

from gitgeist.render.facade import PromptRenderArtifacts, render_prompt
from gitgeist.render.image_backend import (
    FakeImageBackend,
    GeneratedImage,
    detect_media_type,
)
from gitgeist.render.prompt_composer import compose_prompt
from gitgeist.schemas.emotional import (
    ChoiceDistribution,
    EmotionalChoices,
    EmotionalNouls,
    EmotionalScores,
    EmotionalState,
)
from gitgeist.schemas.visual_latent import (
    MaterialityDistribution,
    VisualLatentAxes,
    VisualLatentProfile,
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SAMPLE = b"\xff\xd8\xff\xe0" + b"jpeg-payload"
WEBP_SAMPLE = b"RIFF\x24\x00\x00\x00WEBPVP8 payload"
GARBAGE_SAMPLE = b"not-an-image"


def make_emotional_state() -> EmotionalState:
    scores = EmotionalScores(
        coherence=0.81,
        maturity=0.72,
        volatility=0.25,
        fragility=0.2,
        novelty=0.5,
        discipline=0.77,
        tension=0.3,
        chaos=0.15,
        identity_strength=0.69,
        internal_conflict=0.31,
    )
    choices = EmotionalChoices(
        temperament=ChoiceDistribution(
            weights={"calm": 0.4, "restless": 0.2, "proud": 0.2, "anxious": 0.2},
            dominant="calm",
        ),
        visual_tone=ChoiceDistribution(
            weights={"luminous": 0.5, "austere": 0.3, "dense": 0.2},
            dominant="luminous",
        ),
        energy_profile=ChoiceDistribution(
            weights={"focused": 0.6, "static": 0.4},
            dominant="focused",
        ),
    )
    return EmotionalState(scores=scores, nouls=EmotionalNouls(), choices=choices)


def make_profile() -> VisualLatentProfile:
    axes = VisualLatentAxes(
        form_complexity=0.7,
        symmetry=0.6,
        fragmentation=0.3,
        tension_curvature=0.4,
        texture_density=0.5,
        luminosity=0.6,
        contrast=0.7,
        sharpness=0.8,
        visual_rhythm=0.75,
        compositional_balance=0.8,
        biological_vs_mechanical=0.7,
        ornamental_load=0.2,
        opacity=0.85,
        layering=0.6,
    )
    materiality = MaterialityDistribution(
        weights={"organic": 0.1, "mechanical": 0.6, "crystalline": 0.2, "ethereal": 0.1},
        dominant="mechanical",
    )
    return VisualLatentProfile(
        axes=axes,
        materiality=materiality,
        dominant_features=["sharpness", "compositional_balance"],
    )


class StubBackend:
    def __init__(self, media_type: str = "png", payload: bytes | None = None) -> None:
        self.media_type = media_type
        self.payload = payload if payload is not None else PNG_SIGNATURE + b"stub"
        self.seen_prompts: list[str] = []

    def generate_image(self, prompt: str) -> GeneratedImage:
        self.seen_prompts.append(prompt)
        return GeneratedImage(image_bytes=self.payload, media_type=self.media_type)


def make_real_jpeg_bytes() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), (250, 120, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


def make_real_webp_bytes() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), (40, 200, 90)).save(buffer, format="WEBP")
    return buffer.getvalue()


def test_render_prompt_default_backend():
    state = make_emotional_state()
    profile = make_profile()
    artifacts = render_prompt(state, profile, mode="character")
    assert isinstance(artifacts, PromptRenderArtifacts)
    assert artifacts.prompt_text == compose_prompt(state, profile, mode="character")
    assert artifacts.image_bytes is not None
    assert artifacts.image_bytes.startswith(PNG_SIGNATURE)
    assert artifacts.media_type == "png"
    assert artifacts.prompt_path is None
    assert artifacts.image_path is None


def test_render_prompt_uses_provided_backend():
    state = make_emotional_state()
    profile = make_profile()
    backend = StubBackend()
    artifacts = render_prompt(state, profile, backend=backend, repository_name="repo-x")
    assert artifacts.image_bytes == PNG_SIGNATURE + b"stub"
    assert artifacts.media_type == "png"
    assert backend.seen_prompts == [artifacts.prompt_text]


def test_render_prompt_writes_artifacts(tmp_path: Path):
    state = make_emotional_state()
    profile = make_profile()
    output_dir = tmp_path / "nested" / "out"
    artifacts = render_prompt(state, profile, output_dir=output_dir)
    assert artifacts.prompt_path == output_dir / "prompt.txt"
    assert artifacts.image_path == output_dir / "portrait.png"
    assert artifacts.prompt_path.read_text(encoding="utf-8") == artifacts.prompt_text
    assert artifacts.image_path.read_bytes() == artifacts.image_bytes


def test_render_prompt_writes_jpeg_extension_for_jpeg_backend(tmp_path: Path):
    state = make_emotional_state()
    profile = make_profile()
    output_dir = tmp_path / "out"
    artifacts = render_prompt(
        state,
        profile,
        backend=StubBackend(media_type="jpeg", payload=JPEG_SAMPLE),
        output_dir=output_dir,
    )
    assert artifacts.image_path == output_dir / "portrait.jpg"
    assert artifacts.media_type == "jpeg"
    assert artifacts.image_path.read_bytes() == JPEG_SAMPLE
    assert detect_media_type(artifacts.image_path.read_bytes()) == "jpeg"


def test_render_prompt_writes_webp_extension_for_webp_backend(tmp_path: Path):
    state = make_emotional_state()
    profile = make_profile()
    output_dir = tmp_path / "out"
    artifacts = render_prompt(
        state,
        profile,
        backend=StubBackend(media_type="webp", payload=WEBP_SAMPLE),
        output_dir=output_dir,
    )
    assert artifacts.image_path == output_dir / "portrait.webp"
    assert artifacts.media_type == "webp"
    assert artifacts.image_path.read_bytes() == WEBP_SAMPLE


def test_render_prompt_unknown_media_type_raises_without_image(tmp_path: Path):
    state = make_emotional_state()
    profile = make_profile()
    output_dir = tmp_path / "out"
    with pytest.raises(ValueError, match="PNG, JPEG, or WebP"):
        render_prompt(
            state,
            profile,
            backend=StubBackend(media_type="png", payload=GARBAGE_SAMPLE),
            output_dir=output_dir,
        )
    assert not output_dir.exists()


def test_render_prompt_png_normalization_converts_jpeg(tmp_path: Path):
    pytest.importorskip("PIL")
    state = make_emotional_state()
    profile = make_profile()
    output_dir = tmp_path / "out"
    artifacts = render_prompt(
        state,
        profile,
        backend=StubBackend(media_type="jpeg", payload=make_real_jpeg_bytes()),
        output_dir=output_dir,
        image_format="png",
    )
    assert artifacts.media_type == "png"
    assert artifacts.image_path == output_dir / "portrait.png"
    assert artifacts.image_bytes.startswith(PNG_SIGNATURE)
    assert detect_media_type(artifacts.image_path.read_bytes()) == "png"


def test_render_prompt_png_normalization_converts_webp(tmp_path: Path):
    pytest.importorskip("PIL")
    state = make_emotional_state()
    profile = make_profile()
    output_dir = tmp_path / "out"
    artifacts = render_prompt(
        state,
        profile,
        backend=StubBackend(media_type="webp", payload=make_real_webp_bytes()),
        output_dir=output_dir,
        image_format="png",
    )
    assert artifacts.media_type == "png"
    assert artifacts.image_path == output_dir / "portrait.png"
    assert detect_media_type(artifacts.image_bytes) == "png"


def test_render_prompt_png_normalization_keeps_png_bytes(tmp_path: Path):
    state = make_emotional_state()
    profile = make_profile()
    artifacts = render_prompt(
        state,
        profile,
        backend=StubBackend(media_type="png", payload=PNG_SIGNATURE + b"kept"),
        image_format="png",
    )
    assert artifacts.image_bytes == PNG_SIGNATURE + b"kept"
    assert artifacts.media_type == "png"


def test_render_prompt_png_normalization_without_pillow_raises(tmp_path: Path, monkeypatch):
    monkeypatch.setitem(sys.modules, "PIL", None)
    state = make_emotional_state()
    profile = make_profile()
    with pytest.raises(ValueError, match="gitgeist\\[image\\]"):
        render_prompt(
            state,
            profile,
            backend=StubBackend(media_type="jpeg", payload=JPEG_SAMPLE),
            image_format="png",
        )


def test_render_prompt_rejects_unknown_image_format():
    state = make_emotional_state()
    profile = make_profile()
    with pytest.raises(ValueError):
        render_prompt(state, profile, image_format="webp")


def test_render_prompt_without_output_writes_nothing(tmp_path: Path):
    state = make_emotional_state()
    profile = make_profile()
    render_prompt(state, profile)
    assert list(tmp_path.iterdir()) == []


def test_render_prompt_leaves_stale_portraits_in_other_formats_untouched(tmp_path: Path):
    state = make_emotional_state()
    profile = make_profile()
    output_dir = tmp_path / "out"
    output_dir.mkdir(parents=True)
    stale_path = output_dir / "portrait.webp"
    stale_path.write_bytes(WEBP_SAMPLE)
    artifacts = render_prompt(state, profile, output_dir=output_dir)
    assert artifacts.image_path == output_dir / "portrait.png"
    assert stale_path.read_bytes() == WEBP_SAMPLE


def test_render_prompt_backend_failure_writes_nothing(tmp_path: Path):
    class FailingBackend:
        def generate_image(self, prompt: str) -> GeneratedImage:
            raise ValueError("backend exploded")

    state = make_emotional_state()
    profile = make_profile()
    output_dir = tmp_path / "out"
    with pytest.raises(ValueError):
        render_prompt(state, profile, backend=FailingBackend(), output_dir=output_dir)
    assert not output_dir.exists()


def test_render_prompt_write_failure_raises_oserror(tmp_path: Path):
    state = make_emotional_state()
    profile = make_profile()
    blocker = tmp_path / "occupied"
    blocker.write_text("not a directory", encoding="utf-8")
    with pytest.raises(OSError):
        render_prompt(state, profile, output_dir=blocker)


def test_render_prompt_long_profile_produces_bounded_prompt():
    state = make_emotional_state()
    axes = VisualLatentAxes(
        form_complexity=1.0,
        symmetry=1.0,
        fragmentation=1.0,
        tension_curvature=1.0,
        texture_density=1.0,
        luminosity=1.0,
        contrast=1.0,
        sharpness=1.0,
        visual_rhythm=1.0,
        compositional_balance=1.0,
        biological_vs_mechanical=1.0,
        ornamental_load=1.0,
        opacity=1.0,
        layering=1.0,
    )
    profile = VisualLatentProfile(
        axes=axes,
        materiality=MaterialityDistribution(weights={"organic": 1.0}, dominant="organic"),
        dominant_features=[f"feature_{i}" for i in range(50)],
    )
    artifacts = render_prompt(state, profile)
    assert len(artifacts.prompt_text) < 8000
    assert artifacts.prompt_text.count("feature_") == 50


def test_render_prompt_rejects_wrong_types():
    state = make_emotional_state()
    profile = make_profile()
    with pytest.raises(TypeError):
        render_prompt("not-a-state", profile)
    with pytest.raises(TypeError):
        render_prompt(state, "not-a-profile")


def test_render_prompt_rejects_unknown_mode():
    state = make_emotional_state()
    profile = make_profile()
    with pytest.raises(ValueError):
        render_prompt(state, profile, mode="surreal")


def test_render_prompt_deterministic_image(tmp_path: Path):
    state = make_emotional_state()
    profile = make_profile()
    first = render_prompt(state, profile, backend=FakeImageBackend())
    second = render_prompt(state, profile, backend=FakeImageBackend())
    assert first.image_bytes == second.image_bytes
    assert first.prompt_text == second.prompt_text
