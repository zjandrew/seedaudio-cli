# tests/unit/core/test_config.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from seedaudio_cli.core.config import (
    DEFAULT_ENDPOINT,
    Config,
    Profile,
    load,
    mask_api_key,
    resolve_profile,
    save,
)
from seedaudio_cli.framework.errors import CliError


def test_load_missing_returns_default(tmp_path: Path) -> None:
    cfg = load(tmp_path / "nope.json")
    assert cfg.active == "default"
    assert cfg.profiles["default"].endpoint == DEFAULT_ENDPOINT
    assert cfg.profiles["default"].resource_id is None  # auto: inferred per voice


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    cfg = Config(
        active="prod",
        profiles={
            "prod": Profile(api_key="sk-abc", default_voice="vv", resource_id="seed-icl-2.0")
        },
    )
    save(cfg, path)
    assert oct(path.stat().st_mode)[-3:] == "600"
    again = load(path)
    assert again.active == "prod"
    assert again.profiles["prod"].api_key == "sk-abc"
    assert again.profiles["prod"].default_voice == "vv"
    assert again.profiles["prod"].resource_id == "seed-icl-2.0"


def test_load_rejects_non_object(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(CliError) as ei:
        load(path)
    assert ei.value.code == "IO_ERROR"


def test_mask_api_key() -> None:
    assert mask_api_key(None) == ""
    assert mask_api_key("sk-1234567890") == "sk-***7890"
    assert mask_api_key("short") == "***rt"


def test_resolve_profile_priority(tmp_path: Path) -> None:
    cfg = Config(active="default", profiles={"default": Profile(), "prod": Profile()})
    assert resolve_profile(cli="prod", env={}, config=cfg) == "prod"
    assert resolve_profile(cli=None, env={"SEEDAUDIO_PROFILE": "prod"}, config=cfg) == "prod"
    assert resolve_profile(cli=None, env={}, config=cfg) == "default"


def test_resolve_profile_unknown_raises() -> None:
    cfg = Config(profiles={"default": Profile()})
    with pytest.raises(CliError) as ei:
        resolve_profile(cli="ghost", env={}, config=cfg)
    assert ei.value.code == "INVALID_INPUT"
