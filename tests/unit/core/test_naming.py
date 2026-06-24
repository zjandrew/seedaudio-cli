# tests/unit/core/test_naming.py
from __future__ import annotations

from pathlib import Path

import pytest

from seedaudio_cli.core.naming import make_stem, resolve_out_path
from seedaudio_cli.framework.errors import CliError


def test_make_stem() -> None:
    assert make_stem("abcd1234-ef56-7890-aaaa-bbbb", 1700000000) == "1700000000-abcd1234"


def test_out_none_uses_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    p = resolve_out_path(out=None, stem="s", ext="mp3")
    assert p == tmp_path / "s.mp3"


def test_out_trailing_slash_is_dir(tmp_path: Path) -> None:
    d = tmp_path / "audio"
    p = resolve_out_path(out=str(d) + "/", stem="s", ext="wav")
    assert p == d / "s.wav"
    assert d.is_dir()


def test_out_explicit_file(tmp_path: Path) -> None:
    target = tmp_path / "out.mp3"
    assert resolve_out_path(out=str(target), stem="s", ext="mp3") == target


def test_out_missing_parent_raises(tmp_path: Path) -> None:
    with pytest.raises(CliError) as ei:
        resolve_out_path(out=str(tmp_path / "nope" / "x.mp3"), stem="s", ext="mp3")
    assert ei.value.code == "IO_ERROR"
