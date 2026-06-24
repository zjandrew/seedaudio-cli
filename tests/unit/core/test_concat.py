# tests/unit/core/test_concat.py
from __future__ import annotations

import wave
from pathlib import Path

import pytest

from seedaudio_cli.core.concat import check_concat_support, concat_audio, have_ffmpeg
from seedaudio_cli.framework.errors import CliError


def _write_wav(path: Path, frames: bytes, *, rate: int = 24000) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)


def test_check_support_mp3_without_ffmpeg_raises() -> None:
    with pytest.raises(CliError) as ei:
        check_concat_support("mp3", ffmpeg=False)
    assert ei.value.code == "INVALID_INPUT"


def test_check_support_wav_pcm_ok_without_ffmpeg() -> None:
    check_concat_support("wav", ffmpeg=False)
    check_concat_support("pcm", ffmpeg=False)


def test_check_support_any_with_ffmpeg() -> None:
    check_concat_support("mp3", ffmpeg=True)


def test_concat_pcm_raw(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("seedaudio_cli.core.concat.have_ffmpeg", lambda: False)
    a, b = tmp_path / "a.pcm", tmp_path / "b.pcm"
    a.write_bytes(b"AAAA")
    b.write_bytes(b"BBBB")
    out = tmp_path / "out.pcm"
    method = concat_audio([a, b], out, encoding="pcm")
    assert method == "pcm"
    assert out.read_bytes() == b"AAAABBBB"


def test_concat_wav_stdlib(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("seedaudio_cli.core.concat.have_ffmpeg", lambda: False)
    a, b = tmp_path / "a.wav", tmp_path / "b.wav"
    _write_wav(a, b"\x01\x00" * 100)  # 100 frames
    _write_wav(b, b"\x02\x00" * 50)  # 50 frames
    out = tmp_path / "out.wav"
    method = concat_audio([a, b], out, encoding="wav")
    assert method == "wav"
    with wave.open(str(out), "rb") as w:
        assert w.getnframes() == 150
        assert w.getframerate() == 24000


@pytest.mark.skipif(not have_ffmpeg(), reason="ffmpeg not installed")
def test_concat_ffmpeg_real_wav(tmp_path: Path) -> None:
    a, b = tmp_path / "a.wav", tmp_path / "b.wav"
    _write_wav(a, b"\x01\x00" * 100)
    _write_wav(b, b"\x02\x00" * 50)
    out = tmp_path / "out.wav"
    method = concat_audio([a, b], out, encoding="wav")
    assert method == "ffmpeg"
    with wave.open(str(out), "rb") as w:
        assert w.getnframes() == 150
