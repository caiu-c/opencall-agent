from __future__ import annotations

import pytest

from opencall_agent.ingestion.indexer import ingest_document
from opencall_agent.vector import make_client

pytestmark = pytest.mark.integration


def test_ingest_round_trip(settings, tmp_path) -> None:
    doc = tmp_path / "policy.txt"
    doc.write_text(
        "A farmácia aceita devolução em até sete dias corridos.",
        encoding="utf-8",
    )

    client = make_client(settings)
    collection = "test_integration_ingest"
    if client.collection_exists(collection):
        client.delete_collection(collection)

    try:
        n = ingest_document(settings, client, doc, category="politica", collection=collection)
        assert n == 1

        points = client.scroll(collection_name=collection, limit=10)[0]
        assert len(points) == 1
        payload = points[0].payload
        assert payload["category"] == "politica"
        assert payload["source"].endswith("policy.txt")
        assert payload["chunk_idx"] == 0
        assert "doc_id" in payload and payload["doc_id"]
        assert "ingested_at" in payload
        assert "farmácia" in payload["text"]
    finally:
        client.delete_collection(collection)
