# src/seedaudio_cli/core/segment.py
from __future__ import annotations

# Primary break points (sentence enders) and secondary (clause separators).
_SENTENCE_END = set("。！？；!?;\n")
_CLAUSE_END = set("，,、：:")

# The V3 streaming endpoint handles multi-thousand-char text in one request, so
# this is just a "how big a chunk do you want" default, not an API cap.
DEFAULT_MAX_BYTES = 1500


def _blen(s: str) -> int:
    return len(s.encode("utf-8"))


def _split_keep(text: str, delims: set[str]) -> list[str]:
    """Split on any delimiter char, keeping the delimiter attached to its piece."""
    pieces: list[str] = []
    buf = ""
    for ch in text:
        buf += ch
        if ch in delims:
            pieces.append(buf)
            buf = ""
    if buf:
        pieces.append(buf)
    return pieces


def _hard_cut(s: str, max_bytes: int) -> list[str]:
    """Last resort: cut by character so each piece is within max_bytes."""
    out: list[str] = []
    cur = ""
    for ch in s:
        if cur and _blen(cur) + _blen(ch) > max_bytes:
            out.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def _pack(pieces: list[str], max_bytes: int) -> list[str]:
    """Greedily pack pieces into chunks within max_bytes (pieces assumed to fit)."""
    out: list[str] = []
    cur = ""
    for p in pieces:
        if cur and _blen(cur) + _blen(p) > max_bytes:
            out.append(cur)
            cur = p
        else:
            cur += p
    if cur:
        out.append(cur)
    return out


def split_text(text: str, max_bytes: int = DEFAULT_MAX_BYTES) -> list[str]:
    """Split long text into chunks each within max_bytes (UTF-8), preferring
    sentence then clause boundaries, hard-cutting only as a last resort."""
    text = text.strip()
    if not text:
        return []
    if _blen(text) <= max_bytes:
        return [text]

    chunks: list[str] = []
    for sent in _split_keep(text, _SENTENCE_END):
        if _blen(sent) <= max_bytes:
            chunks.append(sent)
            continue
        # Sentence itself too long → break on clauses, then hard-cut.
        for clause in _pack(_split_keep(sent, _CLAUSE_END), max_bytes):
            if _blen(clause) <= max_bytes:
                chunks.append(clause)
            else:
                chunks.extend(_hard_cut(clause, max_bytes))

    packed = _pack(chunks, max_bytes)
    return [c.strip() for c in packed if c.strip()]
