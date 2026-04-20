from __future__ import annotations

from opencall_agent.ingestion.chunker import chunk_text, split_sentences


def test_empty_text_returns_empty() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_fits_one_chunk() -> None:
    text = "Isto é uma frase. Esta é outra."
    assert chunk_text(text, max_chars=1000) == [text]


def test_long_text_splits_into_multiple_chunks() -> None:
    sentence = "Esta é uma frase de teste usada para exercitar o chunker."
    text = " ".join([sentence] * 30)
    chunks = chunk_text(text, max_chars=200, overlap_sentences=0)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 200


def test_overlap_carries_last_sentence() -> None:
    sentences = [f"Frase numero {i}." for i in range(10)]
    text = " ".join(sentences)
    chunks = chunk_text(text, max_chars=40, overlap_sentences=1)
    assert len(chunks) >= 2
    for i in range(len(chunks) - 1):
        last_sentence_of_prev = chunks[i].split(". ")[-1].rstrip(".")
        assert last_sentence_of_prev in chunks[i + 1]


def test_single_sentence_longer_than_max_is_hard_split() -> None:
    long_sentence = "a" * 1000 + "."
    chunks = chunk_text(long_sentence, max_chars=300)
    assert len(chunks) >= 4
    for c in chunks:
        assert len(c) <= 300


def test_split_sentences_basic() -> None:
    assert split_sentences("Oi. Tchau. Até!") == ["Oi.", "Tchau.", "Até!"]
    assert split_sentences("") == []
    assert split_sentences("   ") == []


def test_unicode_preserved() -> None:
    text = "Posso tomar com leite? Sim, é seguro. Mas evite com álcool."
    chunks = chunk_text(text, max_chars=1000)
    assert len(chunks) == 1
    assert "álcool" in chunks[0]
