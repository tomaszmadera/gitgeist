"""Image generation backends for the prompt_to_image generation mode."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import urllib.request
import zlib
from abc import ABC, abstractmethod

DEFAULT_API_URL = "https://openrouter.ai/api/v1/images"
DEFAULT_MODEL = "google/gemini-3.1-flash-lite-image"
DEFAULT_TIMEOUT = 120.0
API_KEY_ENV = "OPENROUTER_IMAGE_API_KEY"
API_URL_ENV = "OPENROUTER_IMAGE_API_URL"
MODELS_ENV = "OPENROUTER_IMAGE_MODELS"


class ImageGenerationBackend(ABC):
    """Interface for backends turning a prompt into PNG image bytes."""

    @abstractmethod
    def generate_image(self, prompt: str) -> bytes:
        """Return PNG image bytes generated from the prompt."""
        raise NotImplementedError


def _first_env_model() -> str | None:
    raw = os.environ.get(MODELS_ENV)
    if not raw:
        return None
    return next((entry.strip() for entry in raw.split(",") if entry.strip()), None)


class OpenRouterImageBackend(ImageGenerationBackend):
    """Backend calling the OpenRouter Image API over HTTP."""

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.api_url = (
            api_url if api_url is not None else os.environ.get(API_URL_ENV) or DEFAULT_API_URL
        ).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)
        self.model = model if model is not None else _first_env_model() or DEFAULT_MODEL
        self.timeout = timeout

    def generate_image(self, prompt: str) -> bytes:
        if not isinstance(prompt, str):
            raise TypeError(f"Expected str prompt, got {type(prompt).__name__}")
        if not self.api_key:
            raise ValueError(
                f"Missing API key for image generation backend; set {API_KEY_ENV} "
                "or pass api_key explicitly"
            )
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "n": 1, "size": "1024x1024"}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.api_url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return self._extract_image_bytes(body)

    def _extract_image_bytes(self, body: dict) -> bytes:
        data = body.get("data") if isinstance(body, dict) else None
        if not data:
            raise ValueError("Image backend response contains no data entries")
        entry = data[0]
        if not isinstance(entry, dict):
            raise ValueError("Image backend response entry is not an object")
        b64 = entry.get("b64_json")
        if isinstance(b64, str):
            return base64.b64decode(b64)
        url = entry.get("url")
        if isinstance(url, str):
            image_request = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(image_request, timeout=self.timeout) as response:
                return response.read()
        raise ValueError("Image backend response contains neither b64_json nor url")


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def encode_png(width: int, height: int, raw_rgb: bytes) -> bytes:
    """Encode raw RGB bytes into a minimal valid PNG image."""
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    scanlines = bytearray()
    row_stride = width * 3
    for y in range(height):
        scanlines.append(0)
        scanlines.extend(raw_rgb[y * row_stride : (y + 1) * row_stride])
    idat = zlib.compress(bytes(scanlines), 9)
    return signature + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")


class FakeImageBackend(ImageGenerationBackend):
    """Deterministic offline backend producing a valid PNG from the prompt."""

    _SIZE = 16

    def generate_image(self, prompt: str) -> bytes:
        if not isinstance(prompt, str):
            raise TypeError(f"Expected str prompt, got {type(prompt).__name__}")
        width = height = self._SIZE
        needed = width * height * 3
        seed = hashlib.sha256(prompt.encode("utf-8")).digest()
        stream = bytearray()
        counter = 0
        while len(stream) < needed:
            stream.extend(hashlib.sha256(seed + counter.to_bytes(4, "big")).digest())
            counter += 1
        return encode_png(width, height, bytes(stream[:needed]))
