# src/seedaudio_cli/core/synth.py
from __future__ import annotations

import base64
import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import httpx

from seedaudio_cli.core.client import Auth
from seedaudio_cli.framework.errors import CliError

# Type of the injectable streaming seam (overridden in tests).
StreamFn = Callable[..., Iterator[dict[str, Any]]]


@dataclass
class SynthResult:
    audio_path: Path
    audio_bytes: int
    words: list[dict[str, Any]] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    usage: dict[str, Any] | None = None


def _stream_chunks(
    *, url: str, headers: dict[str, str], body: dict[str, Any], timeout: float
) -> Iterator[dict[str, Any]]:
    """POST to the unidirectional endpoint and yield each JSON chunk (NDJSON)."""
    with httpx.stream("POST", url, json=body, headers=headers, timeout=timeout) as r:
        if r.status_code != 200:
            detail = r.read().decode("utf-8", "replace")
            raise CliError(
                "API_ERROR",
                f"TTS request failed: HTTP {r.status_code}",
                details={"status": r.status_code, "body": detail[:2000]},
            )
        for line in r.iter_lines():
            line = line.strip()
            if line:
                yield json.loads(line)


def synthesize(
    *,
    auth: Auth,
    request_id: str,
    req_params: dict[str, Any],
    out_path: Path,
    timeout: float = 60.0,
    stream: StreamFn | None = None,
) -> SynthResult:
    headers = {
        "X-Api-Key": auth.api_key,
        "X-Api-Resource-Id": auth.resource_id,
        "X-Api-Request-Id": request_id,
        "X-Control-Require-Usage-Tokens-Return": "*",
    }
    body = {"req_params": req_params}
    stream_fn = stream or _stream_chunks

    audio = bytearray()
    words: list[dict[str, Any]] = []
    usage: dict[str, Any] | None = None
    last_message: str | None = None
    last_code: Any = None

    for chunk in stream_fn(url=auth.tts_url, headers=headers, body=body, timeout=timeout):
        if (msg := chunk.get("message")) is not None:
            last_message = msg
        if (code := chunk.get("code")) is not None:
            last_code = code
        if data := chunk.get("data"):
            audio.extend(base64.b64decode(data))
        sentence = chunk.get("sentence")
        if isinstance(sentence, dict):
            chunk_words: Any = cast("dict[str, Any]", sentence).get("words")
            if isinstance(chunk_words, list):
                words.extend(cast("list[dict[str, Any]]", chunk_words))
        if (u := chunk.get("usage")) is not None:
            usage = u

    # We don't hard-code the success/terminal status codes (they vary across API
    # generations); instead we treat "HTTP 200 but zero audio" as the failure
    # signal and surface whatever message/code the server sent.
    if not audio:
        raise CliError(
            "API_ERROR",
            f"TTS returned no audio: {last_message or last_code or 'empty response'}",
            details={"code": last_code, "message": last_message},
        )

    tmp = out_path.with_suffix(out_path.suffix + ".part")
    tmp.write_bytes(bytes(audio))
    tmp.replace(out_path)
    return SynthResult(audio_path=out_path, audio_bytes=len(audio), words=words, usage=usage)
