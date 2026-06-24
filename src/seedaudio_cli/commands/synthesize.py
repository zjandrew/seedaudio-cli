# src/seedaudio_cli/commands/synthesize.py
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import click

import seedaudio_cli.core.synth as _synth_mod
from seedaudio_cli.__main__ import emit
from seedaudio_cli.core.client import Auth, resolve_auth, resource_id_for_voice
from seedaudio_cli.core.config import DEFAULT_ENDPOINT, load, resolve_profile
from seedaudio_cli.core.naming import make_stem, resolve_out_path
from seedaudio_cli.core.request import RequestParams, build_req_params, ext_for
from seedaudio_cli.framework.envelope import Success


def _config_path() -> Path:
    # Lazy import so tmp_config fixture's monkeypatch on DEFAULT_CONFIG_PATH wins.
    from seedaudio_cli.core.config import DEFAULT_CONFIG_PATH

    return DEFAULT_CONFIG_PATH


def _read_text(prompt_text: str | None, text_file: str | None) -> str:
    if text_file:
        return Path(text_file).expanduser().read_text(encoding="utf-8")
    return prompt_text or ""


@click.command("synthesize")
@click.option("-p", "--text", "prompt_text", default=None, help="text to synthesize")
@click.option("--text-file", "text_file", type=click.Path(exists=True), default=None)
@click.option("--voice", "--speaker", "voice", default=None, help="voice id (speaker)")
@click.option("-m", "--model", default=None, help="seed-tts-2.0-standard | seed-tts-2.0-expressive")
@click.option("--ssml", is_flag=True, default=False, help="treat text as SSML markup")
@click.option(
    "--encoding",
    type=click.Choice(["mp3", "wav", "pcm", "ogg_opus"]),
    default="mp3",
    help="audio format (audio_params.format)",
)
@click.option("--sample-rate", "sample_rate", type=int, default=24000)
@click.option("--bit-rate", "bit_rate", type=int, default=None, help="mp3 only, bps")
@click.option("--speech-rate", "speech_rate", type=int, default=None, help="[-50,100]")
@click.option("--loudness-rate", "loudness_rate", type=int, default=None, help="[-50,100]")
@click.option("--pitch", type=int, default=None, help="[-12,12]")
@click.option("--instruct", "instruct", multiple=True, help="voice instruction, repeatable")
@click.option("--silence-ms", "silence_ms", type=int, default=None, help="trailing silence, ms")
@click.option("--subtitle", "subtitle", is_flag=True, default=False, help="request word timestamps")
@click.option("--out", default=None, help="output audio path (trailing / treats as dir)")
@click.option("--out-subtitle", "out_subtitle", default=None, help="word-timestamps json path")
@click.option(
    "--from-json",
    "from_json",
    type=click.Path(exists=True),
    default=None,
    help="load base req_params from JSON; other flags still override",
)
@click.option("--timeout", type=float, default=60.0)
@click.pass_context
def synthesize(
    ctx: click.Context,
    prompt_text: str | None,
    text_file: str | None,
    voice: str | None,
    model: str | None,
    ssml: bool,
    encoding: str,
    sample_rate: int,
    bit_rate: int | None,
    speech_rate: int | None,
    loudness_rate: int | None,
    pitch: int | None,
    instruct: tuple[str, ...],
    silence_ms: int | None,
    subtitle: bool,
    out: str | None,
    out_subtitle: str | None,
    from_json: str | None,
    timeout: float,
) -> None:
    """Synthesize speech from text (Doubao TTS)."""
    g = ctx.obj

    cfg = load(_config_path())
    profile_name = resolve_profile(cli=g.get("profile"), env=dict(os.environ), config=cfg)
    profile = cfg.profiles[profile_name]

    text = _read_text(prompt_text, text_file)
    chosen_voice = voice or profile.default_voice
    chosen_model = model or profile.default_model

    params = RequestParams(
        speaker=chosen_voice,
        model=chosen_model,
        ssml=ssml,
        encoding=encoding,
        sample_rate=sample_rate,
        bit_rate=bit_rate,
        speech_rate=speech_rate,
        loudness_rate=loudness_rate,
        pitch=pitch,
        enable_subtitle=subtitle,
        instruct=list(instruct),
        silence_ms=silence_ms,
    )

    base_params: dict[str, Any] = {}
    if from_json:
        base_params = json.loads(Path(from_json).read_text())
    req_params: dict[str, Any] = {**base_params, **build_req_params(text=text, params=params)}

    # resource_id: explicit flag > profile pin > inferred from the voice (official vs cloned).
    resource_id = (
        g.get("resource_id") or profile.resource_id or resource_id_for_voice(chosen_voice or "")
    )
    endpoint = (g.get("endpoint") or profile.endpoint or DEFAULT_ENDPOINT).rstrip("/")

    if g.get("dry_run"):
        emit(
            ctx,
            Success(
                data={
                    "would_call": f"POST {endpoint}/api/v3/tts/unidirectional",
                    "resource_id": resource_id,
                    "request": {"req_params": req_params},
                }
            ),
        )
        return

    auth = resolve_auth(
        cli_api_key=g.get("api_key"),
        cli_endpoint=g.get("endpoint"),
        cli_resource_id=g.get("resource_id"),
        env=dict(os.environ),
        profile_api_key=profile.api_key,
        profile_endpoint=profile.endpoint,
        profile_resource_id=profile.resource_id,
    )
    # Apply the inferred/pinned resource_id resolved above (resolve_auth would
    # otherwise fall back to the built-in default for unpinned profiles).
    auth = Auth(api_key=auth.api_key, endpoint=auth.endpoint, resource_id=resource_id)

    request_id = str(uuid.uuid4())
    ext = ext_for(encoding)
    out_path = resolve_out_path(out=out, stem=make_stem(request_id, int(time.time())), ext=ext)

    result = _synth_mod.synthesize(
        auth=auth,
        request_id=request_id,
        req_params=req_params,
        out_path=out_path,
        timeout=timeout,
    )

    data: dict[str, Any] = {
        "audio_path": str(result.audio_path),
        "bytes": result.audio_bytes,
        "voice": chosen_voice,
        "encoding": encoding,
        "sample_rate": sample_rate,
        "resource_id": auth.resource_id,
        "request_id": request_id,
    }
    if chosen_model:
        data["model"] = chosen_model
    if result.usage is not None:
        data["usage"] = result.usage
    if subtitle and result.words:
        sub_path = (
            resolve_out_path(
                out=out_subtitle,
                stem=make_stem(request_id, int(time.time())),
                ext="words.json",
            )
            if out_subtitle
            else out_path.with_suffix(out_path.suffix + ".words.json")
        )
        sub_path.write_text(json.dumps(result.words, ensure_ascii=False, indent=2))
        data["subtitle_path"] = str(sub_path)

    emit(ctx, Success(data=data))
