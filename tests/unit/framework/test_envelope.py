# tests/unit/framework/test_envelope.py
from __future__ import annotations

import json

from seedaudio_cli.framework.envelope import Failure, Success, apply_jq, render


def test_success_render_json() -> None:
    out = json.loads(render(Success(data={"a": 1})))
    assert out == {"ok": True, "data": {"a": 1}}


def test_failure_render_json_with_details() -> None:
    out = json.loads(render(Failure(code="X", message="bad", details={"k": "v"})))
    assert out == {"ok": False, "error": {"code": "X", "message": "bad", "details": {"k": "v"}}}


def test_apply_jq_dotted_path() -> None:
    env = Success(data={"audio": {"path": "/tmp/a.mp3"}})
    assert apply_jq(env, ".audio.path").data == "/tmp/a.mp3"


def test_apply_jq_array_index() -> None:
    env = Success(data={"voices": [{"id": "a"}, {"id": "b"}]})
    assert apply_jq(env, ".voices[1].id").data == "b"


def test_apply_jq_missing_returns_none() -> None:
    assert apply_jq(Success(data={"a": 1}), ".nope.deep").data is None


def test_failure_always_json_even_in_table_mode() -> None:
    out = json.loads(render(Failure(code="X", message="bad"), fmt="table"))
    assert out["ok"] is False


def test_table_renders_dict() -> None:
    text = render(Success(data={"voice": "vv", "bytes": 10}), fmt="table")
    assert "voice" in text and "vv" in text
