"""Tests for image generation backends (fake and OpenRouter)."""

import base64
import json
import sys
import urllib.error
import urllib.request

import pytest

from gitgeist.render.image_backend import (
    DEFAULT_API_URL,
    DEFAULT_MODEL,
    FakeImageBackend,
    GeneratedImage,
    OpenRouterImageBackend,
    detect_media_type,
    normalize_to_png,
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SAMPLE = b"\xff\xd8\xff\xe0" + b"jpeg-payload"
WEBP_SAMPLE = b"RIFF\x24\x00\x00\x00WEBPVP8 payload"
GARBAGE_SAMPLE = b"not-an-image"


def make_png_payload(suffix: bytes = b"") -> bytes:
    return PNG_SIGNATURE + suffix


def make_url_response(payload: dict):
    body = json.dumps(payload).encode("utf-8")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return body

    return FakeResponse()


def make_bytes_response(payload: bytes):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return payload

    return FakeResponse()


class TestDetectMediaType:
    def test_detects_png(self):
        assert detect_media_type(make_png_payload(b"data")) == "png"

    def test_detects_jpeg(self):
        assert detect_media_type(JPEG_SAMPLE) == "jpeg"

    def test_detects_webp(self):
        assert detect_media_type(WEBP_SAMPLE) == "webp"

    def test_rejects_unknown_bytes(self):
        with pytest.raises(ValueError, match="PNG, JPEG, or WebP"):
            detect_media_type(GARBAGE_SAMPLE)

    def test_rejects_empty_payload(self):
        with pytest.raises(ValueError):
            detect_media_type(b"")

    def test_short_payload_is_not_webp(self):
        with pytest.raises(ValueError):
            detect_media_type(b"RIFFWEBP")


class TestNormalizeToPng:
    def test_missing_pillow_raises_value_error_with_hint(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "PIL", None)
        with pytest.raises(ValueError, match="gitgeist\\[image\\]"):
            normalize_to_png(JPEG_SAMPLE)


class TestFakeImageBackend:
    def test_deterministic_same_prompt(self):
        backend = FakeImageBackend()
        first = backend.generate_image("a portrait of a calm repository")
        second = backend.generate_image("a portrait of a calm repository")
        assert first == second

    def test_different_prompts_differ(self):
        backend = FakeImageBackend()
        first = backend.generate_image("prompt one")
        second = backend.generate_image("prompt two")
        assert first != second

    def test_produces_valid_png(self):
        backend = FakeImageBackend()
        image = backend.generate_image("any prompt")
        assert isinstance(image, GeneratedImage)
        assert image.media_type == "png"
        assert image.image_bytes.startswith(PNG_SIGNATURE)
        assert image.image_bytes.rstrip().endswith(b"IEND\xaeB`\x82")

    def test_rejects_non_string_prompt(self):
        backend = FakeImageBackend()
        with pytest.raises(TypeError):
            backend.generate_image(123)


class TestOpenRouterImageBackend:
    def test_request_shape_and_b64_response(self, monkeypatch):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["url"] = request.full_url
            captured["method"] = request.method
            captured["headers"] = dict(request.header_items())
            captured["body"] = request.data
            captured["timeout"] = timeout
            return make_url_response(
                {"data": [{"b64_json": base64.b64encode(PNG_SIGNATURE + b"image").decode()}]}
            )

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        monkeypatch.delenv("OPENROUTER_IMAGE_MODELS", raising=False)
        backend = OpenRouterImageBackend(api_url=DEFAULT_API_URL, api_key="test-key")
        result = backend.generate_image("draw the repo")
        assert result.image_bytes == make_png_payload(b"image")
        assert result.media_type == "png"
        assert captured["url"] == DEFAULT_API_URL
        assert captured["method"] == "POST"
        assert captured["timeout"] == 120.0
        authorization = captured["headers"]["Authorization"]
        assert authorization == "Bearer test-key"
        body = json.loads(captured["body"])
        assert body["prompt"] == "draw the repo"
        assert body["model"] == DEFAULT_MODEL
        assert "test-key" not in captured["body"].decode()

    def test_custom_model_and_timeout(self, monkeypatch):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["timeout"] = timeout
            captured["body"] = request.data
            return make_url_response(
                {"data": [{"b64_json": base64.b64encode(make_png_payload(b"abc")).decode()}]}
            )

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenRouterImageBackend(
            api_key="k", model="custom-model", timeout=5.0
        )
        backend.generate_image("p")
        assert captured["timeout"] == 5.0
        assert json.loads(captured["body"])["model"] == "custom-model"

    def test_b64_jpeg_response_is_detected_as_jpeg(self, monkeypatch):
        monkeypatch.setattr(
            urllib.request,
            "urlopen",
            lambda r, timeout=None: make_url_response(
                {"data": [{"b64_json": base64.b64encode(JPEG_SAMPLE).decode()}]}
            ),
        )
        backend = OpenRouterImageBackend(api_key="k")
        result = backend.generate_image("p")
        assert result.image_bytes == JPEG_SAMPLE
        assert result.media_type == "jpeg"

    def test_b64_webp_response_is_detected_as_webp(self, monkeypatch):
        monkeypatch.setattr(
            urllib.request,
            "urlopen",
            lambda r, timeout=None: make_url_response(
                {"data": [{"b64_json": base64.b64encode(WEBP_SAMPLE).decode()}]}
            ),
        )
        backend = OpenRouterImageBackend(api_key="k")
        result = backend.generate_image("p")
        assert result.image_bytes == WEBP_SAMPLE
        assert result.media_type == "webp"

    def test_b64_unknown_format_raises(self, monkeypatch):
        monkeypatch.setattr(
            urllib.request,
            "urlopen",
            lambda r, timeout=None: make_url_response(
                {"data": [{"b64_json": base64.b64encode(GARBAGE_SAMPLE).decode()}]}
            ),
        )
        backend = OpenRouterImageBackend(api_key="k")
        with pytest.raises(ValueError, match="PNG, JPEG, or WebP"):
            backend.generate_image("p")

    def test_api_key_from_environment(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_IMAGE_API_KEY", "env-key")

        def fake_urlopen(request, timeout=None):
            headers = dict(request.header_items())
            assert headers["Authorization"] == "Bearer env-key"
            return make_url_response(
                {"data": [{"b64_json": base64.b64encode(make_png_payload(b"x")).decode()}]}
            )

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenRouterImageBackend()
        assert backend.generate_image("p").image_bytes == make_png_payload(b"x")

    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_IMAGE_API_KEY", raising=False)
        backend = OpenRouterImageBackend(api_key=None)
        with pytest.raises(ValueError):
            backend.generate_image("p")

    def test_first_env_model_is_used(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_IMAGE_MODELS", " a/b , c/d ")
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["body"] = request.data
            return make_url_response(
                {"data": [{"b64_json": base64.b64encode(make_png_payload(b"x")).decode()}]}
            )

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenRouterImageBackend(api_key="k")
        backend.generate_image("p")
        assert backend.model == "a/b"
        assert json.loads(captured["body"])["model"] == "a/b"

    def test_explicit_model_overrides_env(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_IMAGE_MODELS", "a/b,c/d")
        backend = OpenRouterImageBackend(api_key="k", model="x/y")
        assert backend.model == "x/y"

    def test_models_env_without_entries_uses_default(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_IMAGE_MODELS", " , ")
        backend = OpenRouterImageBackend(api_key="k")
        assert backend.model == DEFAULT_MODEL

    def test_api_url_from_environment(self, monkeypatch):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["url"] = request.full_url
            return make_url_response(
                {"data": [{"b64_json": base64.b64encode(make_png_payload(b"x")).decode()}]}
            )

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setenv("OPENROUTER_IMAGE_API_URL", "https://proxy.example.com/v1/images")
        backend = OpenRouterImageBackend(api_key="k")
        backend.generate_image("p")
        assert captured["url"] == "https://proxy.example.com/v1/images"

    def test_url_response_is_downloaded(self, monkeypatch):
        calls = []

        def fake_urlopen(request, timeout=None):
            calls.append(request)
            if len(calls) == 1:
                return make_url_response({"data": [{"url": "https://img.example.com/portrait.png"}]})
            return make_bytes_response(make_png_payload(b"downloaded"))

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenRouterImageBackend(api_key="k")
        result = backend.generate_image("p")
        assert result.image_bytes == make_png_payload(b"downloaded")
        assert result.media_type == "png"
        assert calls[1].full_url == "https://img.example.com/portrait.png"
        assert calls[1].get_method() == "GET"
        assert "Authorization" not in dict(calls[1].header_items())

    def test_empty_data_raises(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen", lambda r, timeout=None: make_url_response({"data": []}))
        backend = OpenRouterImageBackend(api_key="k")
        with pytest.raises(ValueError):
            backend.generate_image("p")

    def test_unsupported_image_payload_raises(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen", lambda r, timeout=None: make_url_response({"data": [{}]}))
        backend = OpenRouterImageBackend(api_key="k")
        with pytest.raises(ValueError):
            backend.generate_image("p")

    def test_http_error_propagates(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.HTTPError(
                request.full_url, 401, "Unauthorized", hdrs=None, fp=None
            )

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenRouterImageBackend(api_key="k")
        with pytest.raises(urllib.error.HTTPError):
            backend.generate_image("p")

    def test_url_error_propagates(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.URLError("name resolution failed")

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenRouterImageBackend(api_key="k")
        with pytest.raises(urllib.error.URLError):
            backend.generate_image("p")

    def test_timeout_error_propagates(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            raise TimeoutError("connection timed out")

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenRouterImageBackend(api_key="k", timeout=1.0)
        with pytest.raises(TimeoutError):
            backend.generate_image("p")
