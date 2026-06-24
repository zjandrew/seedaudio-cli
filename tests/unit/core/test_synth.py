# tests/unit/core/test_synth.py
from __future__ import annotations

import base64
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from seedaudio_cli.core.client import Auth
from seedaudio_cli.core.synth import (
    _stream_chunks,  # pyright: ignore[reportPrivateUsage]
    synthesize,
)
from seedaudio_cli.framework.errors import CliError

AUTH = Auth(api_key="k", endpoint="https://h", resource_id="seed-tts-2.0")


def _stream_of(chunks: list[dict[str, Any]]):  # type: ignore[no-untyped-def]
    def _s(
        *, url: str, headers: dict[str, str], body: dict[str, Any], timeout: float
    ) -> Iterator[dict[str, Any]]:
        yield from chunks

    return _s


def test_synthesize_writes_file_and_returns_meta(tmp_path: Path) -> None:
    out = tmp_path / "a.mp3"
    chunks = [
        {"code": 0, "data": base64.b64encode(b"HELLO").decode("ascii")},
        {"code": 0, "data": base64.b64encode(b"WORLD").decode("ascii")},
        {"code": 20000000, "usage": {"text_words": 7}},
    ]
    result = synthesize(
        auth=AUTH,
        request_id="rid",
        req_params={"text": "hi", "speaker": "v"},
        out_path=out,
        stream=_stream_of(chunks),
    )
    assert out.read_bytes() == b"HELLOWORLD"
    assert result.audio_bytes == 10
    assert result.usage == {"text_words": 7}


def test_synthesize_collects_words(tmp_path: Path) -> None:
    out = tmp_path / "a.mp3"
    chunks = [
        {
            "code": 0,
            "data": base64.b64encode(b"X").decode("ascii"),
            "sentence": {"words": [{"word": "hi", "startTime": 0.0, "endTime": 0.3}]},
        },
    ]
    result = synthesize(
        auth=AUTH, request_id="rid", req_params={}, out_path=out, stream=_stream_of(chunks)
    )
    assert result.words == [{"word": "hi", "startTime": 0.0, "endTime": 0.3}]


def test_synthesize_no_audio_raises(tmp_path: Path) -> None:
    out = tmp_path / "a.mp3"
    chunks = [{"code": 40000001, "message": "invalid speaker"}]
    with pytest.raises(CliError) as ei:
        synthesize(
            auth=AUTH, request_id="rid", req_params={}, out_path=out, stream=_stream_of(chunks)
        )
    assert ei.value.code == "API_ERROR"
    assert "invalid speaker" in ei.value.message
    assert not out.exists()


@respx.mock
def test_stream_chunks_parses_ndjson() -> None:
    body = '{"code":0,"data":"QQ=="}\n\n{"code":20000000}\n'
    respx.post("https://h/api/v3/tts/unidirectional").mock(
        return_value=httpx.Response(200, text=body)
    )
    chunks = list(
        _stream_chunks(url=AUTH.tts_url, headers={}, body={"req_params": {}}, timeout=5.0)
    )
    assert chunks[0]["data"] == "QQ=="
    assert chunks[1]["code"] == 20000000


@respx.mock
def test_stream_chunks_non_200_raises() -> None:
    respx.post("https://h/api/v3/tts/unidirectional").mock(
        return_value=httpx.Response(401, text="unauthorized")
    )
    with pytest.raises(CliError) as ei:
        list(_stream_chunks(url=AUTH.tts_url, headers={}, body={}, timeout=5.0))
    assert ei.value.code == "API_ERROR"
    assert ei.value.details is not None
    assert ei.value.details["status"] == 401
