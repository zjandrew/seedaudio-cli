# tests/unit/core/test_request.py
from __future__ import annotations

import json

import pytest

from seedaudio_cli.core.request import RequestParams, build_req_params, ext_for
from seedaudio_cli.framework.errors import CliError


def _params(**over: object) -> RequestParams:
    p = RequestParams(speaker="zh_female_vv_uranus_bigtts")
    for k, v in over.items():
        setattr(p, k, v)
    return p


def test_basic_text() -> None:
    req = build_req_params(text="你好", params=_params())
    assert req["text"] == "你好"
    assert req["speaker"] == "zh_female_vv_uranus_bigtts"
    assert req["audio_params"] == {"format": "mp3", "sample_rate": 24000}


def test_ssml_routes_to_ssml_field() -> None:
    req = build_req_params(text="<speak>hi</speak>", params=_params(ssml=True))
    assert req["ssml"] == "<speak>hi</speak>"
    assert "text" not in req


def test_missing_text_raises() -> None:
    with pytest.raises(CliError) as ei:
        build_req_params(text="", params=_params())
    assert ei.value.code == "INVALID_INPUT"


def test_missing_voice_raises() -> None:
    with pytest.raises(CliError) as ei:
        build_req_params(text="hi", params=RequestParams(speaker=None))
    assert ei.value.code == "INVALID_INPUT"


def test_invalid_sample_rate() -> None:
    with pytest.raises(CliError):
        build_req_params(text="hi", params=_params(sample_rate=12345))


def test_bit_rate_requires_mp3() -> None:
    with pytest.raises(CliError):
        build_req_params(text="hi", params=_params(encoding="wav", bit_rate=64000))


def test_ranges_enforced() -> None:
    with pytest.raises(CliError):
        build_req_params(text="hi", params=_params(speech_rate=200))
    with pytest.raises(CliError):
        build_req_params(text="hi", params=_params(pitch=20))


def test_invalid_model() -> None:
    with pytest.raises(CliError):
        build_req_params(text="hi", params=_params(model="seed-tts-99"))


def test_instruct_and_pitch_and_silence() -> None:
    req = build_req_params(
        text="hi",
        params=_params(instruct=["用开心的语气说"], pitch=3, silence_ms=500),
    )
    assert req["context_texts"] == ["用开心的语气说"]
    assert req["post_process"] == {"pitch": 3}
    assert json.loads(req["additions"]) == {"silence_duration": 500}


def test_audio_param_passthrough() -> None:
    req = build_req_params(
        text="hi",
        params=_params(encoding="mp3", bit_rate=128000, speech_rate=10, loudness_rate=-5),
    )
    ap = req["audio_params"]
    assert ap["bit_rate"] == 128000
    assert ap["speech_rate"] == 10
    assert ap["loudness_rate"] == -5


def test_ext_for() -> None:
    assert ext_for("mp3") == "mp3"
    assert ext_for("ogg_opus") == "ogg"
    assert ext_for("pcm") == "pcm"
