"""Tests for image generation backends (fake and OpenAI-compatible)."""

import base64
import json
import urllib.error
import urllib.request

import pytest

from gitgeist.render.image_backend import FakeImageBackend, OpenAICompatibleBackend

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


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
        assert image.startswith(PNG_SIGNATURE)
        assert image.rstrip().endswith(b"IEND\xaeB`\x82")

    def test_rejects_non_string_prompt(self):
        backend = FakeImageBackend()
        with pytest.raises(TypeError):
            backend.generate_image(123)


class TestOpenAICompatibleBackend:
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
        backend = OpenAICompatibleBackend(base_url="https://api.example.com/v1", api_key="test-key")
        result = backend.generate_image("draw the repo")
        assert result == PNG_SIGNATURE + b"image"
        assert captured["url"] == "https://api.example.com/v1/images/generations"
        assert captured["method"] == "POST"
        assert captured["timeout"] == 120.0
        authorization = captured["headers"]["Authorization"]
        assert authorization == "Bearer test-key"
        body = json.loads(captured["body"])
        assert body["prompt"] == "draw the repo"
        assert body["model"] == "gpt-image-1"
        assert "test-key" not in captured["body"].decode()

    def test_custom_model_and_timeout(self, monkeypatch):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["timeout"] = timeout
            captured["body"] = request.data
            return make_url_response({"data": [{"b64_json": base64.b64encode(b"abc").decode()}]})

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenAICompatibleBackend(
            api_key="k", model="custom-model", timeout=5.0
        )
        backend.generate_image("p")
        assert captured["timeout"] == 5.0
        assert json.loads(captured["body"])["model"] == "custom-model"

    def test_api_key_from_environment(self, monkeypatch):
        monkeypatch.setenv("GITGEIST_IMAGE_API_KEY", "env-key")

        def fake_urlopen(request, timeout=None):
            headers = dict(request.header_items())
            assert headers["Authorization"] == "Bearer env-key"
            return make_url_response({"data": [{"b64_json": base64.b64encode(b"x").decode()}]})

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenAICompatibleBackend()
        assert backend.generate_image("p") == b"x"

    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("GITGEIST_IMAGE_API_KEY", raising=False)
        backend = OpenAICompatibleBackend(api_key=None)
        with pytest.raises(ValueError):
            backend.generate_image("p")

    def test_url_response_is_downloaded(self, monkeypatch):
        calls = []

        def fake_urlopen(request, timeout=None):
            calls.append(request)
            if len(calls) == 1:
                return make_url_response({"data": [{"url": "https://img.example.com/portrait.png"}]})
            return make_bytes_response(PNG_SIGNATURE + b"downloaded")

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenAICompatibleBackend(api_key="k")
        result = backend.generate_image("p")
        assert result == PNG_SIGNATURE + b"downloaded"
        assert calls[1].full_url == "https://img.example.com/portrait.png"
        assert calls[1].get_method() == "GET"
        assert "Authorization" not in dict(calls[1].header_items())

    def test_empty_data_raises(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen", lambda r, timeout=None: make_url_response({"data": []}))
        backend = OpenAICompatibleBackend(api_key="k")
        with pytest.raises(ValueError):
            backend.generate_image("p")

    def test_unsupported_image_payload_raises(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen", lambda r, timeout=None: make_url_response({"data": [{}]}))
        backend = OpenAICompatibleBackend(api_key="k")
        with pytest.raises(ValueError):
            backend.generate_image("p")

    def test_http_error_propagates(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.HTTPError(
                request.full_url, 401, "Unauthorized", hdrs=None, fp=None
            )

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenAICompatibleBackend(api_key="k")
        with pytest.raises(urllib.error.HTTPError):
            backend.generate_image("p")

    def test_url_error_propagates(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.URLError("name resolution failed")

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenAICompatibleBackend(api_key="k")
        with pytest.raises(urllib.error.URLError):
            backend.generate_image("p")

    def test_timeout_error_propagates(self, monkeypatch):
        def fake_urlopen(request, timeout=None):
            raise TimeoutError("connection timed out")

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        backend = OpenAICompatibleBackend(api_key="k", timeout=1.0)
        with pytest.raises(TimeoutError):
            backend.generate_image("p")
