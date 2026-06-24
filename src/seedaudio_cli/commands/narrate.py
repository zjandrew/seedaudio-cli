# src/seedaudio_cli/commands/narrate.py
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
from seedaudio_cli.core.client import resolve_auth
from seedaudio_cli.core.config import load, resolve_profile
from seedaudio_cli.core.naming import make_stem, resolve_out_path
from seedaudio_cli.core.request import RequestParams, build_req_params, ext_for
from seedaudio_cli.core.segment import DEFAULT_MAX_BYTES, split_text
from seedaudio_cli.framework.envelope import Success
from seedaudio_cli.framework.errors import CliError


def _config_path() -> Path:
    from seedaudio_cli.core.config import DEFAULT_CONFIG_PATH

    return DEFAULT_CONFIG_PATH


@click.command("narrate")
@click.option("-p", "--text", "prompt_text", default=None, help="long text to synthesize")
@click.option("--text-file", "text_file", type=click.Path(exists=True), default=None)
@click.option("--voice", "--speaker", "voice", default=None, help="voice id (speaker)")
@click.option("-m", "--model", default=None, help="seed-tts-2.0-standard | seed-tts-2.0-expressive")
@click.option(
    "--encoding",
    type=click.Choice(["mp3", "wav", "pcm", "ogg_opus"]),
    default="mp3",
    help="audio format; wav/pcm concat needs no ffmpeg",
)
@click.option("--sample-rate", "sample_rate", type=int, default=24000)
@click.option("--bit-rate", "bit_rate", type=int, default=None, help="mp3 only, bps")
@click.option("--speech-rate", "speech_rate", type=int, default=None, help="[-50,100]")
@click.option("--loudness-rate", "loudness_rate", type=int, default=None, help="[-50,100]")
@click.option("--pitch", type=int, default=None, help="[-12,12]")
@click.option("--instruct", "instruct", multiple=True, help="voice instruction, repeatable")
@click.option(
    "--silence-ms", "silence_ms", type=int, default=None, help="per-segment trailing silence"
)
@click.option(
    "--max-bytes",
    "max_bytes",
    type=int,
    default=DEFAULT_MAX_BYTES,
    help=f"max UTF-8 bytes per segment (default {DEFAULT_MAX_BYTES}; API cap ~1024)",
)
@click.option("--keep-segments", "keep_segments", is_flag=True, default=False)
@click.option("--out", default=None, help="final concatenated audio path")
@click.option("--timeout", type=float, default=60.0)
@click.pass_context
def narrate(
    ctx: click.Context,
    prompt_text: str | None,
    text_file: str | None,
    voice: str | None,
    model: str | None,
    encoding: str,
    sample_rate: int,
    bit_rate: int | None,
    speech_rate: int | None,
    loudness_rate: int | None,
    pitch: int | None,
    instruct: tuple[str, ...],
    silence_ms: int | None,
    max_bytes: int,
    keep_segments: bool,
    out: str | None,
    timeout: float,
) -> None:
    """Synthesize long text: auto-split into segments, synthesize each, concatenate."""
    g = ctx.obj

    cfg = load(_config_path())
    profile_name = resolve_profile(cli=g.get("profile"), env=dict(os.environ), config=cfg)
    profile = cfg.profiles[profile_name]

    text = (
        Path(text_file).expanduser().read_text(encoding="utf-8")
        if text_file
        else (prompt_text or "")
    )
    segments = split_text(text, max_bytes)
    if not segments:
        raise CliError("INVALID_INPUT", "no text: pass -p/--text TEXT or --text-file PATH")

    chosen_voice = voice or profile.default_voice
    chosen_model = model or profile.default_model
    params = RequestParams(
        speaker=chosen_voice,
        model=chosen_model,
        encoding=encoding,
        sample_rate=sample_rate,
        bit_rate=bit_rate,
        speech_rate=speech_rate,
        loudness_rate=loudness_rate,
        pitch=pitch,
        instruct=list(instruct),
        silence_ms=silence_ms,
    )
    # Validate params once (raises INVALID_INPUT before any network call).
    build_req_params(text=segments[0], params=params)

    ffmpeg = _concat.have_ffmpeg()
    _concat.check_concat_support(encoding, ffmpeg=ffmpeg)

    if g.get("dry_run"):
        emit(
            ctx,
            Success(
                data={
                    "would_call": "POST .../api/v3/tts/unidirectional (per segment)",
                    "segments": len(segments),
                    "concat": "ffmpeg" if ffmpeg else encoding,
                    "preview": [s[:40] for s in segments],
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
        for i, seg in enumerate(segments, start=1):
            click.echo(f"[{i}/{len(segments)}] synthesizing {len(seg.encode())}B...", err=True)
            req_params = build_req_params(text=seg, params=params)
            seg_path = seg_dir / f"seg-{i:03d}.{ext}"
            result = _synth_mod.synthesize(
                auth=auth,
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
            "segments": len(segments),
            "bytes": final_path.stat().st_size,
            "voice": chosen_voice,
            "encoding": encoding,
            "sample_rate": sample_rate,
            "resource_id": auth.resource_id,
            "concat": method,
            "usage": {"text_words": total_words},
        }
        if keep_segments:
            data["segment_paths"] = [str(p) for p in seg_paths]
        emit(ctx, Success(data=data))
    finally:
        if cleanup:
            shutil.rmtree(seg_dir, ignore_errors=True)
