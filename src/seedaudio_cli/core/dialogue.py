# src/seedaudio_cli/core/dialogue.py
from __future__ import annotations

from dataclasses import dataclass

from seedaudio_cli.framework.errors import CliError


@dataclass
class DialogueLine:
    role: str
    text: str


def parse_script(text: str) -> list[DialogueLine]:
    """Parse a dialogue script. Each non-blank line is `角色: 台词` (`:` or `：`).
    Blank lines and lines starting with `#` are ignored."""
    lines: list[DialogueLine] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        seps = [i for i in (s.find(":"), s.find("：")) if i != -1]
        if not seps:
            raise CliError("INVALID_INPUT", f"script line missing 'role:' prefix: {raw.strip()!r}")
        idx = min(seps)
        role, utter = s[:idx].strip(), s[idx + 1 :].strip()
        if not role or not utter:
            raise CliError("INVALID_INPUT", f"malformed script line: {raw.strip()!r}")
        lines.append(DialogueLine(role=role, text=utter))
    if not lines:
        raise CliError("INVALID_INPUT", "script has no dialogue lines")
    return lines


def parse_kv(items: tuple[str, ...], *, flag: str) -> dict[str, str]:
    """Parse repeated `KEY=VALUE` option values into a dict."""
    out: dict[str, str] = {}
    for it in items:
        if "=" not in it:
            raise CliError("INVALID_INPUT", f"{flag} expects ROLE=VALUE, got {it!r}")
        k, _, v = it.partition("=")
        if not k.strip() or not v.strip():
            raise CliError("INVALID_INPUT", f"{flag} expects ROLE=VALUE, got {it!r}")
        out[k.strip()] = v.strip()
    return out
