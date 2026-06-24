# src/seedaudio_cli/core/naming.py
from __future__ import annotations

import os
from pathlib import Path

from seedaudio_cli.framework.errors import CliError


def make_stem(request_id: str, when: int) -> str:
    """Auto file stem: <unix_ts>-<short request id>."""
    short = request_id.replace("-", "")[:8] or "tts"
    return f"{when}-{short}"


def resolve_out_path(*, out: str | None, stem: str, ext: str) -> Path:
    if out is None:
        return Path.cwd() / f"{stem}.{ext}"
    # trailing slash → directory (auto-created)
    if out.endswith(("/", os.sep)):
        d = Path(out.rstrip("/" + os.sep)).expanduser()
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{stem}.{ext}"
    target = Path(out).expanduser()
    if not target.parent.exists():
        raise CliError(
            "IO_ERROR",
            f"parent directory does not exist: {target.parent} "
            f"(pass a path ending with '/' to auto-create, or mkdir it first)",
        )
    return target
