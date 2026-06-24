# src/seedaudio_cli/core/client.py
from __future__ import annotations

from dataclasses import dataclass

from seedaudio_cli.core.config import DEFAULT_ENDPOINT, DEFAULT_RESOURCE_ID
from seedaudio_cli.framework.errors import CliError

# HTTP Chunked unidirectional streaming TTS (Doubao speech synthesis large model 2.0).
TTS_PATH = "/api/v3/tts/unidirectional"

# X-Api-Resource-Id values: route the request to a model family.
RESOURCE_IDS = {
    "seed-tts-2.0",  # official 2.0 voices
    "seed-icl-2.0",  # cloned voices (speaker ids starting with S_)
}

# Optional req_params.model values (used mainly with cloned voices).
MODEL_CHOICES = {"seed-tts-2.0-standard", "seed-tts-2.0-expressive"}

# Cloned (ICL) voice ids carry these prefixes and must route through seed-icl-2.0.
CLONED_VOICE_PREFIXES = ("S_", "ICL_", "saturn_")


def resource_id_for_voice(voice_id: str) -> str:
    """Infer the X-Api-Resource-Id from a voice id (cloned vs official)."""
    if voice_id.startswith(CLONED_VOICE_PREFIXES):
        return "seed-icl-2.0"
    return "seed-tts-2.0"


@dataclass(frozen=True)
class Auth:
    api_key: str
    endpoint: str
    resource_id: str

    @property
    def tts_url(self) -> str:
        return self.endpoint.rstrip("/") + TTS_PATH


def resolve_auth(
    *,
    cli_api_key: str | None,
    cli_endpoint: str | None,
    cli_resource_id: str | None,
    env: dict[str, str],
    profile_api_key: str | None,
    profile_endpoint: str | None,
    profile_resource_id: str | None,
) -> Auth:
    api_key = cli_api_key or env.get("SEEDAUDIO_API_KEY") or profile_api_key
    if not api_key:
        raise CliError(
            "CONFIG_MISSING",
            "no API key found. set SEEDAUDIO_API_KEY env or run: seedaudio-cli config init",
        )
    endpoint = cli_endpoint or env.get("SEEDAUDIO_ENDPOINT") or profile_endpoint or DEFAULT_ENDPOINT
    resource_id = cli_resource_id or profile_resource_id or DEFAULT_RESOURCE_ID
    return Auth(api_key=api_key, endpoint=endpoint, resource_id=resource_id)
