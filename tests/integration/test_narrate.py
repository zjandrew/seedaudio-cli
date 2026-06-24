# tests/integration/test_narrate.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from seedaudio_cli.__main__ import root
from tests.conftest import DEFAULT_AUDIO, FakeStream


def _envelope(output: str) -> dict[str, Any]:
    # narrate streams per-segment progress to stderr, which CliRunner mixes into
    # output; the JSON envelope is the trailing object, so parse from its start.
    return json.loads(output[output.index("{") :])


def _data(output: str) -> dict[str, Any]:
    payload = _envelope(output)
    assert payload["ok"] is True, payload
    return payload["data"]


def test_dry_run_reports_segments(tmp_config: Path) -> None:
    runner = CliRunner()
    res = runner.invoke(
        root,
        [
            "--dry-run",
            "narrate",
            "-p",
            "第一句。第二句。第三句。",
            "--voice",
            "vv",
            "--max-bytes",
            "12",
        ],
    )
    assert res.exit_code == 0, res.output
    data = _data(res.output)
    assert data["segments"] == 3
    assert len(data["preview"]) == 3


def test_narrate_concats_segments(
    tmp_config: Path, tmp_path: Path, fake_tts: FakeStream, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force the dependency-free raw path so fake (non-audio) bytes concat cleanly.
    monkeypatch.setattr("seedaudio_cli.core.concat.have_ffmpeg", lambda: False)
    out = tmp_path / "story.pcm"
    res = runner_invoke(
        [
            "narrate",
            "-p",
            "甲。乙。丙。",
            "--voice",
            "vv",
            "--encoding",
            "pcm",
            "--max-bytes",
            "6",
            "--out",
            str(out),
        ]
    )
    assert res.exit_code == 0, res.output
    data = _data(res.output)
    assert data["segments"] == 3
    assert data["concat"] == "pcm"
    assert data["usage"]["text_words"] == 12  # 3 segments * 4 (fake usage)
    assert out.read_bytes() == DEFAULT_AUDIO * 3


def test_narrate_mp3_without_ffmpeg_fails_fast(
    tmp_config: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("seedaudio_cli.core.concat.have_ffmpeg", lambda: False)
    res = runner_invoke(
        [
            "narrate",
            "-p",
            "甲。乙。",
            "--voice",
            "vv",
            "--encoding",
            "mp3",
            "--max-bytes",
            "6",
            "--out",
            str(tmp_path / "x.mp3"),
        ]
    )
    assert res.exit_code == 2
    assert _envelope(res.output)["error"]["code"] == "INVALID_INPUT"


def test_narrate_keep_segments(
    tmp_config: Path, tmp_path: Path, fake_tts: FakeStream, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("seedaudio_cli.core.concat.have_ffmpeg", lambda: False)
    out = tmp_path / "kept.pcm"
    res = runner_invoke(
        [
            "narrate",
            "-p",
            "甲。乙。",
            "--voice",
            "vv",
            "--encoding",
            "pcm",
            "--max-bytes",
            "6",
            "--keep-segments",
            "--out",
            str(out),
        ]
    )
    assert res.exit_code == 0, res.output
    data = _data(res.output)
    assert len(data["segment_paths"]) == 2
    assert all(Path(p).exists() for p in data["segment_paths"])


def runner_invoke(args: list[str]):  # type: ignore[no-untyped-def]
    return CliRunner().invoke(root, args)
