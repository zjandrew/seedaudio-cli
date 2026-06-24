# tests/integration/test_voices.py
from __future__ import annotations

import json
from typing import Any

from click.testing import CliRunner

from seedaudio_cli.__main__ import root


def _data(output: str) -> dict[str, Any]:
    payload = json.loads(output)
    assert payload["ok"] is True, payload
    return payload["data"]


def test_voices_lists_all() -> None:
    data = _data(CliRunner().invoke(root, ["voices"]).output)
    assert data["count"] >= 1
    assert all("id" in v for v in data["voices"])


def test_voices_filter_language() -> None:
    data = _data(CliRunner().invoke(root, ["voices", "--language", "en"]).output)
    assert data["count"] >= 1
    assert all(v["language"] == "en" for v in data["voices"])


def test_voices_search() -> None:
    data = _data(CliRunner().invoke(root, ["voices", "--search", "vv"]).output)
    assert any("vv" in v["id"] for v in data["voices"])
