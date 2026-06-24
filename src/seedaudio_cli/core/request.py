# src/seedaudio_cli/core/request.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from seedaudio_cli.core.client import MODEL_CHOICES
from seedaudio_cli.framework.errors import CliError

# Documented audio_params.format values for the V3 unidirectional endpoint.
ENCODINGS = {"mp3", "wav", "pcm", "ogg_opus"}
# Map an encoding to the on-disk file extension.
ENCODING_EXT = {"mp3": "mp3", "wav": "wav", "pcm": "pcm", "ogg_opus": "ogg"}
SAMPLE_RATES = {8000, 16000, 22050, 24000, 32000, 44100, 48000}

DEFAULT_ENCODING = "mp3"
DEFAULT_SAMPLE_RATE = 24000


@dataclass
class RequestParams:
    speaker: str | None = None
    model: str | None = None
    ssml: bool = False
    encoding: str = DEFAULT_ENCODING
    sample_rate: int = DEFAULT_SAMPLE_RATE
    bit_rate: int | None = None
    speech_rate: int | None = None
    loudness_rate: int | None = None
    pitch: int | None = None
    enable_subtitle: bool = False
    instruct: list[str] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    silence_ms: int | None = None


def ext_for(encoding: str) -> str:
    return ENCODING_EXT.get(encoding, encoding)


def _check_range(name: str, value: int | None, lo: int, hi: int) -> None:
    if value is not None and not (lo <= value <= hi):
        raise CliError("INVALID_INPUT", f"{name} must be in [{lo}, {hi}]; got {value}")


def build_req_params(*, text: str, params: RequestParams) -> dict[str, Any]:
    """Build the V3 `req_params` object. Raises INVALID_INPUT on bad flags."""
    if not text:
        raise CliError("INVALID_INPUT", "no text: pass -p/--text TEXT (or --text-file PATH)")
    if not params.speaker:
        raise CliError(
            "INVALID_INPUT",
            "no voice: pass --voice ID, set a profile default_voice, "
            "or discover ids with: seedaudio-cli voices",
        )

    if params.encoding not in ENCODINGS:
        raise CliError(
            "INVALID_INPUT",
            f"--encoding must be one of {sorted(ENCODINGS)}; got {params.encoding!r}",
        )
    if params.sample_rate not in SAMPLE_RATES:
        raise CliError(
            "INVALID_INPUT",
            f"--sample-rate must be one of {sorted(SAMPLE_RATES)}; got {params.sample_rate}",
        )
    if params.bit_rate is not None and params.encoding != "mp3":
        raise CliError("INVALID_INPUT", "--bit-rate only applies to --encoding mp3")
    if params.model is not None and params.model not in MODEL_CHOICES:
        raise CliError(
            "INVALID_INPUT",
            f"--model must be one of {sorted(MODEL_CHOICES)}; got {params.model!r}",
        )
    _check_range("--speech-rate", params.speech_rate, -50, 100)
    _check_range("--loudness-rate", params.loudness_rate, -50, 100)
    _check_range("--pitch", params.pitch, -12, 12)
    if params.silence_ms is not None and not (0 <= params.silence_ms <= 30000):
        raise CliError(
            "INVALID_INPUT", f"--silence-ms must be in [0, 30000]; got {params.silence_ms}"
        )

    audio_params: dict[str, Any] = {
        "format": params.encoding,
        "sample_rate": params.sample_rate,
    }
    if params.bit_rate is not None:
        audio_params["bit_rate"] = params.bit_rate
    if params.speech_rate is not None:
        audio_params["speech_rate"] = params.speech_rate
    if params.loudness_rate is not None:
        audio_params["loudness_rate"] = params.loudness_rate
    if params.enable_subtitle:
        audio_params["enable_subtitle"] = True

    req: dict[str, Any] = {"speaker": params.speaker, "audio_params": audio_params}
    if params.ssml:
        req["ssml"] = text
    else:
        req["text"] = text
    if params.model is not None:
        req["model"] = params.model
    if params.pitch is not None:
        req["post_process"] = {"pitch": params.pitch}
    if params.instruct:
        req["context_texts"] = list(params.instruct)
    if params.silence_ms is not None:
        # `additions` is a JSON-encoded string of extra synthesis options.
        req["additions"] = json.dumps({"silence_duration": params.silence_ms})
    return req
