# src/seedaudio_cli/core/concat.py
from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

from seedaudio_cli.framework.errors import CliError

# Encodings we can concatenate with the stdlib alone (no ffmpeg).
_STDLIB_OK = {"wav", "pcm"}


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def check_concat_support(encoding: str, *, ffmpeg: bool) -> None:
    """Fail fast (before any API call) when this encoding can't be concatenated."""
    if ffmpeg or encoding in _STDLIB_OK:
        return
    raise CliError(
        "INVALID_INPUT",
        f"concatenating {encoding} segments needs ffmpeg, which was not found. "
        f"install ffmpeg, or use --encoding wav / pcm for dependency-free concat.",
    )


def concat_audio(seg_paths: list[Path], out_path: Path, *, encoding: str) -> str:
    """Concatenate segment files into out_path. Returns the method used."""
    if not seg_paths:
        raise CliError("INTERNAL", "no segments to concatenate")
    if have_ffmpeg():
        _concat_ffmpeg(seg_paths, out_path)
        return "ffmpeg"
    if encoding == "wav":
        _concat_wav(seg_paths, out_path)
        return "wav"
    if encoding == "pcm":
        _concat_raw(seg_paths, out_path)
        return "pcm"
    raise CliError(
        "INVALID_INPUT",
        f"cannot concatenate {encoding} without ffmpeg; use --encoding wav / pcm",
    )


def _concat_ffmpeg(seg_paths: list[Path], out_path: Path) -> None:
    listing = "".join(f"file '{p.resolve()}'\n" for p in seg_paths)
    list_file = out_path.with_suffix(out_path.suffix + ".concat.txt")
    list_file.write_text(listing)
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(out_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise CliError(
                "IO_ERROR",
                f"ffmpeg concat failed: {proc.stderr.strip()[-500:]}",
            )
    finally:
        list_file.unlink(missing_ok=True)


def _concat_wav(seg_paths: list[Path], out_path: Path) -> None:
    with wave.open(str(out_path), "wb") as out:
        params_set = False
        for p in seg_paths:
            with wave.open(str(p), "rb") as w:
                if not params_set:
                    out.setparams(w.getparams())
                    params_set = True
                out.writeframes(w.readframes(w.getnframes()))


def _concat_raw(seg_paths: list[Path], out_path: Path) -> None:
    with open(out_path, "wb") as out:
        for p in seg_paths:
            out.write(p.read_bytes())
