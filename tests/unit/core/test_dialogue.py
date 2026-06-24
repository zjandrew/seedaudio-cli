# tests/unit/core/test_dialogue.py
from __future__ import annotations

import pytest

from seedaudio_cli.core.client import resource_id_for_voice
from seedaudio_cli.core.dialogue import parse_kv, parse_script
from seedaudio_cli.framework.errors import CliError


def test_parse_script_basic() -> None:
    text = "旁白: 夜深了。\n小美：你回来啦？\n# 注释\n\n阿强: 嗯。"
    lines = parse_script(text)
    assert [(line.role, line.text) for line in lines] == [
        ("旁白", "夜深了。"),
        ("小美", "你回来啦？"),
        ("阿强", "嗯。"),
    ]


def test_parse_script_missing_colon() -> None:
    with pytest.raises(CliError) as ei:
        parse_script("这一行没有角色前缀")
    assert ei.value.code == "INVALID_INPUT"


def test_parse_script_empty() -> None:
    with pytest.raises(CliError):
        parse_script("# only comments\n\n")


def test_parse_kv() -> None:
    assert parse_kv(("旁白=v1", "小美=v2"), flag="--voice") == {"旁白": "v1", "小美": "v2"}


def test_parse_kv_bad() -> None:
    with pytest.raises(CliError):
        parse_kv(("noequalsign",), flag="--voice")


def test_resource_id_for_voice() -> None:
    assert resource_id_for_voice("zh_female_vv_uranus_bigtts") == "seed-tts-2.0"
    assert resource_id_for_voice("S_14TMJlS62") == "seed-icl-2.0"
    assert resource_id_for_voice("ICL_uranus_zh_male_ruyajunzi_tob") == "seed-icl-2.0"
    assert resource_id_for_voice("saturn_zh_female_keainvsheng_tob") == "seed-icl-2.0"
