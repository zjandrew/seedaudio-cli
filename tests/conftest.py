# tests/conftest.py
from __future__ import annotations

import base64
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

DEFAULT_AUDIO = b"FAKEAUDIOBYTES"


@dataclass
class FakeStream:
    """Stand-in for synth._stream_chunks. Yields scripted NDJSON chunks."""

    chunks: list[dict[str, Any]] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    calls: list[dict[str, Any]] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]

    def __call__(
        self, *, url: str, headers: dict[str, str], body: dict[str, Any], timeout: float
    ) -> Iterator[dict[str, Any]]:
        self.calls.append({"url": url, "headers": headers, "body": body, "timeout": timeout})
        yield from self.chunks


@pytest.fixture
def fake_tts(monkeypatch: pytest.MonkeyPatch) -> FakeStream:
    fake = FakeStream(
        chunks=[
            {"code": 0, "data": base64.b64encode(DEFAULT_AUDIO).decode("ascii")},
            {"code": 20000000, "usage": {"text_words": 4}},
        ]
    )
    monkeypatch.setattr("seedaudio_cli.core.synth._stream_chunks", fake)
    return fake


@pytest.fixture
def tmp_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr("seedaudio_cli.core.config.DEFAULT_CONFIG_PATH", cfg_path)
    # Provide a fake API key by default so the auth resolver doesn't blow up
    # unless a test explicitly clears the env.
    monkeypatch.setenv("SEEDAUDIO_API_KEY", "sk-test-1234567890")
    monkeypatch.delenv("SEEDAUDIO_PROFILE", raising=False)
    monkeypatch.delenv("SEEDAUDIO_ENDPOINT", raising=False)
    return cfg_path
