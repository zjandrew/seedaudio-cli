# tests/integration/test_synthesize.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from seedaudio_cli.__main__ import root
from tests.conftest import DEFAULT_AUDIO, FakeStream


def _data(result_output: str) -> dict[str, Any]:
    payload = json.loads(result_output)
    assert payload["ok"] is True, payload
    return payload["data"]


def test_dry_run_prints_request(tmp_config: Path) -> None:
    runner = CliRunner()
    res = runner.invoke(
        root,
        ["--dry-run", "synthesize", "-p", "你好", "--voice", "zh_female_vv_uranus_bigtts"],
    )
    assert res.exit_code == 0, res.output
    data = _data(res.output)
    assert data["would_call"].endswith("/api/v3/tts/unidirectional")
    assert data["request"]["req_params"]["text"] == "你好"
    assert data["request"]["req_params"]["speaker"] == "zh_female_vv_uranus_bigtts"


def test_synthesize_writes_file(tmp_config: Path, tmp_path: Path, fake_tts: FakeStream) -> None:
    out = tmp_path / "hello.mp3"
    runner = CliRunner()
    res = runner.invoke(
        root,
        ["synthesize", "-p", "你好", "--voice", "vv", "--out", str(out)],
    )
    assert res.exit_code == 0, res.output
    data = _data(res.output)
    assert data["audio_path"] == str(out)
    assert data["bytes"] == len(DEFAULT_AUDIO)
    assert data["voice"] == "vv"
    assert data["usage"] == {"text_words": 4}
    assert out.read_bytes() == DEFAULT_AUDIO
    # header carried the X-Api-Key + resource id
    assert fake_tts.calls[0]["headers"]["X-Api-Resource-Id"] == "seed-tts-2.0"


def test_missing_voice_is_invalid_input(tmp_config: Path) -> None:
    runner = CliRunner()
    res = runner.invoke(root, ["synthesize", "-p", "你好"])
    assert res.exit_code == 2
    assert json.loads(res.output)["error"]["code"] == "INVALID_INPUT"


def test_missing_key_is_config_missing(
    tmp_config: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SEEDAUDIO_API_KEY", raising=False)
    runner = CliRunner()
    res = runner.invoke(
        root, ["synthesize", "-p", "你好", "--voice", "vv", "--out", str(tmp_path / "x.mp3")]
    )
    assert res.exit_code == 2
    assert json.loads(res.output)["error"]["code"] == "CONFIG_MISSING"


def test_subtitle_writes_words(
    tmp_config: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import base64

    out = tmp_path / "clip.mp3"
    fake = FakeStream(
        chunks=[
            {
                "code": 0,
                "data": base64.b64encode(b"AUD").decode("ascii"),
                "sentence": {"words": [{"word": "你好", "startTime": 0.0, "endTime": 0.4}]},
            }
        ]
    )
    monkeypatch.setattr("seedaudio_cli.core.synth._stream_chunks", fake)
    runner = CliRunner()
    res = runner.invoke(
        root,
        ["synthesize", "-p", "你好", "--voice", "vv", "--subtitle", "--out", str(out)],
    )
    assert res.exit_code == 0, res.output
    data = _data(res.output)
    sub = Path(data["subtitle_path"])
    assert sub.exists()
    assert json.loads(sub.read_text())[0]["word"] == "你好"


def test_default_voice_from_profile(tmp_config: Path, tmp_path: Path, fake_tts: FakeStream) -> None:
    # Seed a config with a default_voice so synthesize works without --voice.
    runner = CliRunner()
    assert runner.invoke(root, ["config", "set", "default_voice", "prof_voice"]).exit_code == 0
    res = runner.invoke(root, ["synthesize", "-p", "hi", "--out", str(tmp_path / "a.mp3")])
    assert res.exit_code == 0, res.output
    assert _data(res.output)["voice"] == "prof_voice"
