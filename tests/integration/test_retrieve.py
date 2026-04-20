"""Retrieval round-trip: ingest → retrieve with threshold + filter semantics."""

from __future__ import annotations

import pytest
from qdrant_client.models import FieldCondition, Filter, MatchValue

from opencall_agent.ingestion.indexer import ingest_document
from opencall_agent.vector import make_client, retrieve

pytestmark = pytest.mark.integration


def test_retrieve_returns_hits_sorted_by_score(settings, tmp_path) -> None:
    doc = tmp_path / "policy.txt"
    doc.write_text(
        "A farmácia aceita devolução em até sete dias corridos apenas em compra "
        "não-presencial, conforme o artigo 49 do Código de Defesa do Consumidor.",
        encoding="utf-8",
    )
    client = make_client(settings)
    collection = "test_retrieve"
    if client.collection_exists(collection):
        client.delete_collection(collection)
    try:
        ingest_document(settings, client, doc, category="politica", collection=collection)
        hits = retrieve(
            settings, client, "qual o prazo para arrependimento em compra online?", collection
        )
        assert hits, "retrieve must return at least one hit"
        scores = [h.score for h in hits]
        assert scores == sorted(scores, reverse=True), "hits must be sorted by score desc"
        assert hits[0].category == "politica"
        assert hits[0].source.endswith("policy.txt")
    finally:
        client.delete_collection(collection)


def test_retrieve_respects_filter(settings, tmp_path) -> None:
    politica = tmp_path / "politica.txt"
    politica.write_text("Política: prazo de arrependimento é de sete dias.", encoding="utf-8")
    faq = tmp_path / "faq.txt"
    faq.write_text("FAQ: prazo de arrependimento é de sete dias.", encoding="utf-8")

    client = make_client(settings)
    collection = "test_retrieve_filter"
    if client.collection_exists(collection):
        client.delete_collection(collection)
    try:
        ingest_document(settings, client, politica, category="politica", collection=collection)
        ingest_document(settings, client, faq, category="faq", collection=collection)

        politica_only = Filter(
            must=[FieldCondition(key="category", match=MatchValue(value="politica"))]
        )
        hits = retrieve(
            settings,
            client,
            "arrependimento sete dias",
            collection,
            query_filter=politica_only,
        )
        assert hits, "filtered retrieve must return hits"
        assert {h.category for h in hits} == {"politica"}
    finally:
        client.delete_collection(collection)
