# src/seedaudio_cli/commands/dialogue.py
from __future__ import annotations

import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import click

import seedaudio_cli.core.concat as _concat
import seedaudio_cli.core.synth as _synth_mod
from seedaudio_cli.__main__ import emit
from seedaudio_cli.core.client import Auth, resolve_auth, resource_id_for_voice
from seedaudio_cli.core.config import load, resolve_profile
from seedaudio_cli.core.dialogue import parse_kv, parse_script
from seedaudio_cli.core.naming import make_stem, resolve_out_path
from seedaudio_cli.core.request import RequestParams, build_req_params, ext_for
from seedaudio_cli.framework.envelope import Success
from seedaudio_cli.framework.errors import CliError


def _config_path() -> Path:
    from seedaudio_cli.core.config import DEFAULT_CONFIG_PATH

    return DEFAULT_CONFIG_PATH


@click.command("dialogue")
@click.option(
    "--script",
    "script_path",
    type=click.Path(exists=True),
    default=None,
    help="script file: each line `角色: 台词`",
)
@click.option("-p", "--text", "inline_script", default=None, help="inline script (same format)")
@click.option("--voice", "voice_map", multiple=True, help="ROLE=VOICE_ID, repeatable")
@click.option("--instruct", "instruct_map", multiple=True, help="ROLE=指令, repeatable")
@click.option("-m", "--model", default=None, help="seed-tts-2.0-standard | seed-tts-2.0-expressive")
@click.option(
    "--encoding",
    type=click.Choice(["mp3", "wav", "pcm", "ogg_opus"]),
    default="mp3",
    help="audio format; wav/pcm concat needs no ffmpeg",
)
@click.option("--sample-rate", "sample_rate", type=int, default=24000)
@click.option("--speech-rate", "speech_rate", type=int, default=None, help="[-50,100]")
@click.option("--loudness-rate", "loudness_rate", type=int, default=None, help="[-50,100]")
@click.option("--pitch", type=int, default=None, help="[-12,12]")
@click.option(
    "--silence-ms", "silence_ms", type=int, default=None, help="per-line trailing silence"
)
@click.option("--keep-segments", "keep_segments", is_flag=True, default=False)
@click.option("--out", default=None, help="final concatenated audio path")
@click.option("--timeout", type=float, default=60.0)
@click.pass_context
def dialogue(
    ctx: click.Context,
    script_path: str | None,
    inline_script: str | None,
    voice_map: tuple[str, ...],
    instruct_map: tuple[str, ...],
    model: str | None,
    encoding: str,
    sample_rate: int,
    speech_rate: int | None,
    loudness_rate: int | None,
    pitch: int | None,
    silence_ms: int | None,
    keep_segments: bool,
    out: str | None,
    timeout: float,
) -> None:
    """Multi-role dialogue: synthesize each line with its role's voice, concatenate."""
    g = ctx.obj

    if script_path:
        raw = Path(script_path).expanduser().read_text(encoding="utf-8")
    elif inline_script:
        raw = inline_script
    else:
        raise CliError("INVALID_INPUT", "no script: pass --script PATH or -p TEXT")
    lines = parse_script(raw)
    roles = list(dict.fromkeys(line.role for line in lines))

    voices = parse_kv(voice_map, flag="--voice")
    instructs = parse_kv(instruct_map, flag="--instruct")
    missing = [r for r in roles if r not in voices]
    if missing:
        raise CliError(
            "INVALID_INPUT",
            f"no voice mapped for role(s): {missing}. pass --voice ROLE=VOICE_ID for each.",
            details={"roles": roles, "mapped": list(voices.keys())},
        )

    cfg = load(_config_path())
    profile_name = resolve_profile(cli=g.get("profile"), env=dict(os.environ), config=cfg)
    profile = cfg.profiles[profile_name]
    chosen_model = model or profile.default_model

    def _params_for(role: str) -> RequestParams:
        ins = [instructs[role]] if role in instructs else []
        return RequestParams(
            speaker=voices[role],
            model=chosen_model,
            encoding=encoding,
            sample_rate=sample_rate,
            speech_rate=speech_rate,
            loudness_rate=loudness_rate,
            pitch=pitch,
            instruct=ins,
            silence_ms=silence_ms,
        )

    # Validate every role's params once (raises INVALID_INPUT before any call).
    for r in roles:
        build_req_params(text="占位", params=_params_for(r))

    ffmpeg = _concat.have_ffmpeg()
    _concat.check_concat_support(encoding, ffmpeg=ffmpeg)

    if g.get("dry_run"):
        emit(
            ctx,
            Success(
                data={
                    "would_call": "POST .../api/v3/tts/unidirectional (per line)",
                    "lines": len(lines),
                    "roles": {r: voices[r] for r in roles},
                    "concat": "ffmpeg" if ffmpeg else encoding,
                    "preview": [{"role": ln.role, "text": ln.text[:30]} for ln in lines],
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
    cli_resource_id = g.get("resource_id")

    ext = ext_for(encoding)
    batch = make_stem(str(uuid.uuid4()), int(time.time()))
    final_path = resolve_out_path(out=out, stem=batch, ext=ext)

    if keep_segments:
        seg_dir = final_path.parent / f"{final_path.stem}.segments"
        seg_dir.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        seg_dir = Path(tempfile.mkdtemp(prefix="seedaudio-"))
        cleanup = True

    try:
        seg_paths: list[Path] = []
        total_words = 0
        for i, ln in enumerate(lines, start=1):
            voice = voices[ln.role]
            # Explicit --resource-id wins; otherwise infer per voice (cloned vs official).
            resource_id = cli_resource_id or resource_id_for_voice(voice)
            line_auth = Auth(api_key=auth.api_key, endpoint=auth.endpoint, resource_id=resource_id)
            click.echo(f"[{i}/{len(lines)}] {ln.role} ({voice})...", err=True)
            req_params = build_req_params(text=ln.text, params=_params_for(ln.role))
            seg_path = seg_dir / f"line-{i:03d}.{ext}"
            result = _synth_mod.synthesize(
                auth=line_auth,
                request_id=str(uuid.uuid4()),
                req_params=req_params,
                out_path=seg_path,
                timeout=timeout,
            )
            seg_paths.append(seg_path)
            if result.usage and isinstance(result.usage.get("text_words"), int):
                total_words += result.usage["text_words"]

        method = _concat.concat_audio(seg_paths, final_path, encoding=encoding)
        data: dict[str, Any] = {
            "audio_path": str(final_path),
            "lines": len(lines),
            "roles": {r: voices[r] for r in roles},
            "bytes": final_path.stat().st_size,
            "encoding": encoding,
            "sample_rate": sample_rate,
            "concat": method,
            "usage": {"text_words": total_words},
        }
        if keep_segments:
            data["segment_paths"] = [str(p) for p in seg_paths]
        emit(ctx, Success(data=data))
    finally:
        if cleanup:
            shutil.rmtree(seg_dir, ignore_errors=True)
