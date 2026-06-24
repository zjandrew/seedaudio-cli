# tests/unit/core/test_client.py
from __future__ import annotations

import pytest

from seedaudio_cli.core.client import resolve_auth
from seedaudio_cli.framework.errors import CliError


def _resolve(**over: str | None):  # type: ignore[no-untyped-def]
    base: dict[str, str | None] = {
        "cli_api_key": None,
        "cli_endpoint": None,
        "cli_resource_id": None,
        "profile_api_key": "sk-profile",
        "profile_endpoint": "https://openspeech.bytedance.com",
        "profile_resource_id": "seed-tts-2.0",
    }
    base.update(over)
    return resolve_auth(env={}, **base)  # type: ignore[arg-type]


def test_cli_flag_wins() -> None:
    auth = _resolve(cli_api_key="sk-cli", cli_resource_id="seed-icl-2.0")
    assert auth.api_key == "sk-cli"
    assert auth.resource_id == "seed-icl-2.0"


def test_env_over_profile() -> None:
    auth = resolve_auth(
        cli_api_key=None,
        cli_endpoint=None,
        cli_resource_id=None,
        env={"SEEDAUDIO_API_KEY": "sk-env", "SEEDAUDIO_ENDPOINT": "https://env.example"},
        profile_api_key="sk-profile",
        profile_endpoint="https://profile.example",
        profile_resource_id="seed-tts-2.0",
    )
    assert auth.api_key == "sk-env"
    assert auth.endpoint == "https://env.example"


def test_missing_key_raises_config_missing() -> None:
    with pytest.raises(CliError) as ei:
        resolve_auth(
            cli_api_key=None,
            cli_endpoint=None,
            cli_resource_id=None,
            env={},
            profile_api_key=None,
            profile_endpoint=None,
            profile_resource_id=None,
        )
    assert ei.value.code == "CONFIG_MISSING"


def test_tts_url() -> None:
    auth = _resolve(cli_endpoint="https://host/")
    assert auth.tts_url == "https://host/api/v3/tts/unidirectional"
