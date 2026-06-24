# tests/integration/test_dialogue.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from seedaudio_cli.__main__ import root
from tests.conftest import DEFAULT_AUDIO, FakeStream

SCRIPT = "旁白: 夜深了。\n小美: 你回来啦？\n阿强: 嗯，堵车了。"


def _envelope(output: str) -> dict[str, Any]:
    return json.loads(output[output.index("{") :])


def _data(output: str) -> dict[str, Any]:
    payload = _envelope(output)
    assert payload["ok"] is True, payload
    return payload["data"]


def _run(args: list[str], **kw: Any):  # type: ignore[no-untyped-def]
    return CliRunner().invoke(root, args, **kw)


def test_dry_run_lists_lines_and_roles(tmp_config: Path) -> None:
    res = _run(
        [
            "--dry-run",
            "dialogue",
            "-p",
            SCRIPT,
            "--voice",
            "旁白=zh_male_x_uranus_bigtts",
            "--voice",
            "小美=zh_female_y_uranus_bigtts",
            "--voice",
            "阿强=zh_male_z_uranus_bigtts",
        ]
    )
    assert res.exit_code == 0, res.output
    data = _data(res.output)
    assert data["lines"] == 3
    assert set(data["roles"]) == {"旁白", "小美", "阿强"}


def test_missing_voice_for_role(tmp_config: Path) -> None:
    res = _run(["--dry-run", "dialogue", "-p", SCRIPT, "--voice", "旁白=v1"])
    assert res.exit_code == 2
    assert _envelope(res.output)["error"]["code"] == "INVALID_INPUT"


def test_dialogue_concats_in_order(
    tmp_config: Path, tmp_path: Path, fake_tts: FakeStream, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("seedaudio_cli.core.concat.have_ffmpeg", lambda: False)
    out = tmp_path / "dlg.pcm"
    res = _run(
        [
            "dialogue",
            "-p",
            SCRIPT,
            "--encoding",
            "pcm",
            "--out",
            str(out),
            "--voice",
            "旁白=zh_male_x_uranus_bigtts",
            "--voice",
            "小美=S_14TMJlS62",
            "--voice",
            "阿强=zh_male_z_uranus_bigtts",
        ]
    )
    assert res.exit_code == 0, res.output
    data = _data(res.output)
    assert data["lines"] == 3
    assert out.read_bytes() == DEFAULT_AUDIO * 3
    # Per-line resource id inferred: line 2 uses a cloned voice → seed-icl-2.0.
    assert fake_tts.calls[1]["headers"]["X-Api-Resource-Id"] == "seed-icl-2.0"
    assert fake_tts.calls[0]["headers"]["X-Api-Resource-Id"] == "seed-tts-2.0"


def test_dialogue_per_role_instruct(
    tmp_config: Path, tmp_path: Path, fake_tts: FakeStream, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("seedaudio_cli.core.concat.have_ffmpeg", lambda: False)
    res = _run(
        [
            "dialogue",
            "-p",
            "小美: 你好。",
            "--encoding",
            "pcm",
            "--out",
            str(tmp_path / "a.pcm"),
            "--voice",
            "小美=zh_female_y_uranus_bigtts",
            "--instruct",
            "小美=用温柔的语气说",
        ]
    )
    assert res.exit_code == 0, res.output
    body = fake_tts.calls[0]["body"]["req_params"]
    assert body["context_texts"] == ["用温柔的语气说"]
