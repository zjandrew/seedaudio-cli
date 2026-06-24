# tests/integration/test_config.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from seedaudio_cli.__main__ import root


def _data(output: str) -> dict[str, Any]:
    payload = json.loads(output)
    assert payload["ok"] is True, payload
    return payload["data"]


def test_set_show_use_list(tmp_config: Path) -> None:
    runner = CliRunner()
    assert runner.invoke(root, ["config", "set", "api_key", "sk-abc123456"]).exit_code == 0
    assert runner.invoke(root, ["config", "set", "default_voice", "vv"]).exit_code == 0

    shown = _data(runner.invoke(root, ["config", "show"]).output)
    assert shown["default_voice"] == "vv"
    assert shown["api_key"] == "sk-***3456"  # masked
    assert shown["resource_id"] is None  # auto: inferred per voice unless pinned

    listed = _data(runner.invoke(root, ["config", "list"]).output)
    assert listed["active"] == "default"


def test_add_and_use_profile(tmp_config: Path) -> None:
    runner = CliRunner()
    add = runner.invoke(
        root, ["config", "add", "prod"], input="sk-prodkey\n\nseed-icl-2.0\nmyvoice\n"
    )
    assert add.exit_code == 0, add.output
    used = _data(runner.invoke(root, ["config", "use", "prod"]).output)
    assert used["active"] == "prod"
    shown = _data(runner.invoke(root, ["config", "show", "prod"]).output)
    assert shown["resource_id"] == "seed-icl-2.0"
    assert shown["default_voice"] == "myvoice"


def test_unset_resource_id_returns_to_auto(tmp_config: Path) -> None:
    runner = CliRunner()
    runner.invoke(root, ["config", "set", "resource_id", "seed-icl-2.0"])
    out = _data(runner.invoke(root, ["config", "unset", "resource_id"]).output)
    assert out["resource_id"] is None  # auto


def test_unset_endpoint_resets_to_default(tmp_config: Path) -> None:
    runner = CliRunner()
    runner.invoke(root, ["config", "set", "endpoint", "https://custom.example"])
    out = _data(runner.invoke(root, ["config", "unset", "endpoint"]).output)
    assert out["endpoint"] == "https://openspeech.bytedance.com"


def test_set_unknown_key_rejected(tmp_config: Path) -> None:
    runner = CliRunner()
    res = runner.invoke(root, ["config", "set", "bogus", "x"])
    assert res.exit_code == 2
    assert json.loads(res.output)["error"]["code"] == "INVALID_INPUT"


def test_init_wizard(tmp_config: Path) -> None:
    runner = CliRunner()
    res = runner.invoke(
        root, ["config", "init"], input="sk-init12345\n\nseed-tts-2.0\nzh_female_vv_uranus_bigtts\n"
    )
    assert res.exit_code == 0, res.output
    # Prompts go to stderr; verify the persisted profile via a clean `config show`.
    data = _data(runner.invoke(root, ["config", "show"]).output)
    assert data["api_key"] == "sk-***2345"
    assert data["default_voice"] == "zh_female_vv_uranus_bigtts"
