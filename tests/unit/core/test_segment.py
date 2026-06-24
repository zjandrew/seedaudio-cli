# tests/unit/core/test_segment.py
from __future__ import annotations

from seedaudio_cli.core.segment import split_text


def _blen(s: str) -> int:
    return len(s.encode("utf-8"))


def test_empty() -> None:
    assert split_text("") == []
    assert split_text("   \n  ") == []


def test_short_stays_single() -> None:
    assert split_text("你好世界。", max_bytes=900) == ["你好世界。"]


def test_splits_on_sentence_boundary() -> None:
    text = "第一句。第二句。第三句。"
    # each "第一句。" is 4 chars * 3 bytes = 12 bytes; cap at 12 → one sentence per chunk
    chunks = split_text(text, max_bytes=12)
    assert chunks == ["第一句。", "第二句。", "第三句。"]


def test_packs_multiple_sentences_under_limit() -> None:
    text = "甲。乙。丙。丁。"
    chunks = split_text(text, max_bytes=12)  # "甲。乙。" = 12 bytes
    assert all(_blen(c) <= 12 for c in chunks)
    assert "".join(chunks) == "甲。乙。丙。丁。"


def test_long_clause_falls_back_to_comma() -> None:
    text = "这是一个很长的句子，里面有很多逗号分隔的部分，需要进一步切分才行。"
    chunks = split_text(text, max_bytes=24)
    assert all(_blen(c) <= 24 for c in chunks)
    assert len(chunks) >= 2


def test_hard_cut_no_punctuation() -> None:
    text = "啊" * 100  # 300 bytes, no punctuation
    chunks = split_text(text, max_bytes=30)
    assert all(_blen(c) <= 30 for c in chunks)
    assert "".join(chunks) == text


def test_all_chunks_within_limit() -> None:
    text = ("豆包语音合成大模型支持多种音色和情感。" * 20).strip()
    chunks = split_text(text, max_bytes=120)
    assert len(chunks) > 1
    assert all(_blen(c) <= 120 for c in chunks)
