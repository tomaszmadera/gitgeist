"""Tests for the prompt rendering facade (render_prompt and artifacts)."""

import io
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gitgeist.render.facade import PromptRenderArtifacts, render_prompt
from gitgeist.render.image_backend import (
    FakeImageBackend,
    GeneratedImage,
    detect_media_type,
)
from gitgeist.render.prompt_composer import compose_prompt
from gitgeist.schemas.features import (
    DocsSummaryFeatures,
    GitHistoryFeatures,
    RepositoryFeatures,
    StaticFeatures,
)
from gitgeist.schemas.visual_spec import CrackMark, Cracks, VisualSpec

FIXTURE = Path(__file__).parent / "golden" / "visual_spec" / "single-script-abstract.json"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SAMPLE = b"\xff\xd8\xff\xe0" + b"jpeg-payload"
WEBP_SAMPLE = b"RIFF\x24\x00\x00\x00WEBPVP8 payload"
GARBAGE_SAMPLE = b"not-an-image"
MASKED_SEED = 8904369301646676


def load_spec() -> VisualSpec:
    return VisualSpec.model_validate_json(FIXTURE.read_text(encoding="utf-8"))


def make_features() -> RepositoryFeatures:
    return RepositoryFeatures(
        repository_path="/tmp/sample-repo",
        extracted_at=datetime(2026, 4, 16, tzinfo=timezone.utc),
        static=StaticFeatures(
            code_bytes=1000,
            test_ratio=0.1,
            doc_ratio=0.0,
            todo_density=0,
            top_level_directory_count=1,
            max_directory_depth=1,
        ),
        history=GitHistoryFeatures(
            commit_count=1,
            unique_authors_count=1,
            repository_age_days=10,
            top_author_share=1,
            last_commit_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
        ),
        docs=DocsSummaryFeatures(),
    )


SPEC = load_spec()
FEATURES = make_features()


class StubBackend:
    def __init__(self, media_type: str = "png", payload: bytes | None = None) -> None:
        self.media_type = media_type
        self.payload = payload if payload is not None else PNG_SIGNATURE + b"stub"
        self.seen_prompts: list[str] = []
        self.seen_seeds: list[int | None] = []

    def generate_image(self, prompt: str, *, spec=None, seed=None) -> GeneratedImage:
        self.seen_prompts.append(prompt)
        self.seen_seeds.append(seed)
        return GeneratedImage(image_bytes=self.payload, media_type=self.media_type)


def _render(**kwargs):
    kwargs.setdefault("caption", False)
    return render_prompt(SPEC, features=FEATURES, **kwargs)


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
    artifacts = _render()
    assert isinstance(artifacts, PromptRenderArtifacts)
    assert artifacts.prompt_text == compose_prompt(SPEC)
    assert artifacts.image_bytes is not None
    assert artifacts.image_bytes.startswith(PNG_SIGNATURE)
    assert artifacts.media_type == "png"
    assert artifacts.prompt_path is None
    assert artifacts.image_path is None


def test_render_prompt_passes_the_masked_seed():
    backend = StubBackend()
    artifacts = _render(backend=backend)
    assert backend.seen_prompts == [artifacts.prompt_text]
    assert backend.seen_seeds == [MASKED_SEED]
    assert artifacts.image_bytes == PNG_SIGNATURE + b"stub"


def test_render_prompt_writes_artifacts(tmp_path: Path):
    output_dir = tmp_path / "nested" / "out"
    artifacts = _render(output_dir=output_dir)
    assert artifacts.prompt_path == output_dir / "prompt.txt"
    assert artifacts.image_path == output_dir / "portrait.png"
    assert artifacts.prompt_path.read_text(encoding="utf-8") == artifacts.prompt_text
    assert artifacts.image_path.read_bytes() == artifacts.image_bytes


def test_render_prompt_writes_jpeg_extension_for_jpeg_backend(tmp_path: Path):
    output_dir = tmp_path / "out"
    artifacts = _render(
        backend=StubBackend(media_type="jpeg", payload=JPEG_SAMPLE),
        output_dir=output_dir,
    )
    assert artifacts.image_path == output_dir / "portrait.jpg"
    assert artifacts.media_type == "jpeg"
    assert artifacts.image_path.read_bytes() == JPEG_SAMPLE
    assert detect_media_type(artifacts.image_path.read_bytes()) == "jpeg"


def test_render_prompt_writes_webp_extension_for_webp_backend(tmp_path: Path):
    output_dir = tmp_path / "out"
    artifacts = _render(
        backend=StubBackend(media_type="webp", payload=WEBP_SAMPLE),
        output_dir=output_dir,
    )
    assert artifacts.image_path == output_dir / "portrait.webp"
    assert artifacts.media_type == "webp"
    assert artifacts.image_path.read_bytes() == WEBP_SAMPLE


def test_render_prompt_unknown_media_type_raises_without_image(tmp_path: Path):
    output_dir = tmp_path / "out"
    with pytest.raises(ValueError, match="PNG, JPEG, or WebP"):
        _render(
            backend=StubBackend(media_type="png", payload=GARBAGE_SAMPLE),
            output_dir=output_dir,
        )
    assert not output_dir.exists()


def test_render_prompt_png_normalization_converts_jpeg(tmp_path: Path):
    pytest.importorskip("PIL")
    output_dir = tmp_path / "out"
    artifacts = _render(
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
    output_dir = tmp_path / "out"
    artifacts = _render(
        backend=StubBackend(media_type="webp", payload=make_real_webp_bytes()),
        output_dir=output_dir,
        image_format="png",
    )
    assert artifacts.media_type == "png"
    assert artifacts.image_path == output_dir / "portrait.png"
    assert detect_media_type(artifacts.image_bytes) == "png"


def test_render_prompt_png_normalization_keeps_png_bytes(tmp_path: Path):
    artifacts = _render(
        backend=StubBackend(media_type="png", payload=PNG_SIGNATURE + b"kept"),
        image_format="png",
    )
    assert artifacts.image_bytes == PNG_SIGNATURE + b"kept"
    assert artifacts.media_type == "png"


def test_render_prompt_png_normalization_without_pillow_raises(tmp_path: Path, monkeypatch):
    monkeypatch.setitem(sys.modules, "PIL", None)
    with pytest.raises(ValueError, match="gitgeist\\[image\\]"):
        _render(
            backend=StubBackend(media_type="jpeg", payload=JPEG_SAMPLE),
            image_format="png",
        )


def test_render_prompt_rejects_unknown_image_format():
    with pytest.raises(ValueError):
        _render(image_format="webp")


def test_render_prompt_without_output_writes_nothing(tmp_path: Path):
    _render()
    assert list(tmp_path.iterdir()) == []


def test_render_prompt_leaves_stale_portraits_in_other_formats_untouched(tmp_path: Path):
    output_dir = tmp_path / "out"
    output_dir.mkdir(parents=True)
    stale_path = output_dir / "portrait.webp"
    stale_path.write_bytes(WEBP_SAMPLE)
    artifacts = _render(output_dir=output_dir)
    assert artifacts.image_path == output_dir / "portrait.png"
    assert stale_path.read_bytes() == WEBP_SAMPLE


def test_render_prompt_backend_failure_writes_nothing(tmp_path: Path):
    class FailingBackend:
        def generate_image(self, prompt: str, *, spec=None, seed=None) -> GeneratedImage:
            raise ValueError("backend exploded")

    output_dir = tmp_path / "out"
    with pytest.raises(ValueError):
        _render(backend=FailingBackend(), output_dir=output_dir)
    assert not output_dir.exists()


def test_render_prompt_write_failure_raises_oserror(tmp_path: Path):
    blocker = tmp_path / "occupied"
    blocker.write_text("not a directory", encoding="utf-8")
    with pytest.raises(OSError):
        _render(output_dir=blocker)


def test_render_prompt_is_bounded_to_the_composer():
    artifacts = _render()
    assert artifacts.prompt_text == compose_prompt(SPEC)
    directives = [line for line in artifacts.prompt_text.splitlines() if line.startswith("- ")]
    assert 5 <= len(directives) <= 7
    assert len(artifacts.prompt_text) < 8000


def test_render_prompt_rejects_wrong_types():
    with pytest.raises(TypeError):
        render_prompt("not-a-spec", features=FEATURES, caption=False)
    with pytest.raises(TypeError):
        render_prompt(SPEC, features=object(), caption=False)


def test_render_prompt_rejects_unknown_style():
    bad = SPEC.model_copy(update={"style": "surreal"})
    with pytest.raises(ValueError, match="surreal"):
        render_prompt(bad, features=FEATURES, caption=False)


def test_render_prompt_deterministic_image():
    first = _render(backend=FakeImageBackend())
    second = _render(backend=FakeImageBackend())
    assert first.image_bytes == second.image_bytes
    assert first.prompt_text == second.prompt_text


def test_caption_off_does_not_need_pillow(monkeypatch):
    monkeypatch.setitem(sys.modules, "PIL", None)
    artifacts = _render(backend=FakeImageBackend())
    assert artifacts.image_bytes.startswith(PNG_SIGNATURE)


def test_caption_on_missing_pillow_writes_nothing(tmp_path: Path, monkeypatch):
    monkeypatch.setitem(sys.modules, "PIL", None)
    output_dir = tmp_path / "out"

    class CalledBackend:
        def generate_image(self, prompt: str, *, spec=None, seed=None) -> GeneratedImage:
            raise AssertionError("backend ran before the Pillow check")

    with pytest.raises(ValueError, match="pip install gitgeist\\[image\\]"):
        render_prompt(
            SPEC,
            features=FEATURES,
            caption=True,
            backend=CalledBackend(),
            output_dir=output_dir,
        )
    assert not output_dir.exists()


def test_caption_strip_keeps_the_top_rows_and_meets_the_minimum():
    pytest.importorskip("PIL")
    from PIL import Image

    raw = FakeImageBackend().generate_image("ignored", spec=SPEC).image_bytes
    artifacts = render_prompt(SPEC, features=FEATURES, caption=True, backend=FakeImageBackend())
    raw_image = Image.open(io.BytesIO(raw)).convert("RGB")
    captioned = Image.open(io.BytesIO(artifacts.image_bytes)).convert("RGB")
    assert raw_image.size == (64, 64)
    assert captioned.size[0] == 64
    assert captioned.size[1] >= 72
    assert list(captioned.crop((0, 0, 64, 64)).getdata()) == list(raw_image.getdata())


def test_crack_pixel_is_painted_last():
    pytest.importorskip("PIL")
    from PIL import Image

    spec = SPEC.model_copy(
        update={"cracks": Cracks(count=1, marks=[CrackMark(mass_index=0, u=0, v=0, angle=0)])}
    )
    image = FakeImageBackend().generate_image("ignored", spec=spec)
    opened = Image.open(io.BytesIO(image.image_bytes))
    host = spec.masses[0]
    pixel = (
        min(63, max(0, int(32 + host.x * 28 + 0.5))),
        min(63, max(0, int(32 + host.y * 28 + 0.5))),
    )
    assert opened.getpixel(pixel) == (208, 208, 208)
