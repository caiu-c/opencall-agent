"""Sentence-aware chunking with configurable size and overlap."""

from __future__ import annotations

import re

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def chunk_text(
    text: str,
    max_chars: int = 800,
    overlap_sentences: int = 1,
) -> list[str]:
    """Pack sentences into chunks of up to max_chars; carry the last N sentences forward as overlap.

    A sentence longer than max_chars is hard-split on character boundaries.
    """
    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> list[str]:
        nonlocal current, current_len
        if not current:
            return []
        chunks.append(" ".join(current))
        tail = current[-overlap_sentences:] if overlap_sentences > 0 else []
        current = list(tail)
        current_len = sum(len(x) + 1 for x in current)
        return tail

    for sentence in sentences:
        sep_len = 1 if current else 0
        if len(sentence) > max_chars:
            flush()
            for i in range(0, len(sentence), max_chars):
                chunks.append(sentence[i : i + max_chars])
            current = []
            current_len = 0
            continue

        if current_len + sep_len + len(sentence) > max_chars and current:
            flush()
            sep_len = 1 if current else 0

        current.append(sentence)
        current_len += sep_len + len(sentence)

    if current:
        chunks.append(" ".join(current))

    return chunks
