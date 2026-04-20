"""US-S1 — Supervisor ingests documents so agents get up-to-date info.

Given a source file,
When I run ingestion,
Then the file is chunked, embedded, stored with metadata, and discoverable by retrieval.
"""

from __future__ import annotations

import pytest

from opencall_agent.ingestion.indexer import ingest_document
from opencall_agent.llm import embed
from opencall_agent.vector import make_client

pytestmark = pytest.mark.acceptance


def test_ingested_document_is_retrievable(settings, tmp_path) -> None:
    doc = tmp_path / "politica_generico.txt"
    doc.write_text(
        "A farmácia aceita trocas de medicamentos genéricos no prazo de 7 dias "
        "corridos após a compra, mediante apresentação da nota fiscal.",
        encoding="utf-8",
    )

    client = make_client(settings)
    collection = "test_us_s1"
    if client.collection_exists(collection):
        client.delete_collection(collection)

    try:
        n_chunks = ingest_document(
            settings, client, doc, category="politica", collection=collection
        )
        assert n_chunks >= 1, "ingestion produced at least one chunk"

        query_vec = embed(settings, ["qual o prazo para trocar um genérico?"])[0]
        hits = client.query_points(
            collection_name=collection, query=query_vec, limit=3
        ).points

        assert hits, "retrieval returned at least one hit"
        top = hits[0]
        assert top.payload["source"].endswith("politica_generico.txt")
        assert top.payload["category"] == "politica"
        text_lower = top.payload["text"].lower()
        assert "7 dias" in text_lower or "prazo" in text_lower or "genéric" in text_lower
    finally:
        client.delete_collection(collection)
