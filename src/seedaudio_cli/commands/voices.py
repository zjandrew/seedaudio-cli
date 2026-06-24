# src/seedaudio_cli/commands/voices.py
from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

import click

from seedaudio_cli.__main__ import emit
from seedaudio_cli.framework.envelope import Success


@lru_cache(maxsize=1)
def _load_catalog() -> dict[str, Any]:
    raw = resources.files("seedaudio_cli.data").joinpath("voices.json").read_text(encoding="utf-8")
    return json.loads(raw)


@click.command("voices")
@click.option("--language", default=None, help="filter by language, e.g. zh / en")
@click.option("--search", default=None, help="substring match on id / name / tags")
@click.pass_context
def voices(ctx: click.Context, language: str | None, search: str | None) -> None:
    """List a curated subset of known voice ids (verify the full list in the console)."""
    catalog = _load_catalog()
    items: list[dict[str, Any]] = list(catalog.get("voices", []))

    if language:
        items = [v for v in items if v.get("language") == language]
    if search:
        needle = search.lower()
        items = [
            v
            for v in items
            if needle in v.get("id", "").lower()
            or needle in v.get("name", "").lower()
            or any(needle in t.lower() for t in v.get("tags", []))
        ]

    emit(ctx, Success(data={"voices": items, "count": len(items), "note": catalog.get("_note")}))
