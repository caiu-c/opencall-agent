"""End-to-end HTTP tests — real Qdrant + Ollama behind a TestClient."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from opencall_agent.api import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def client(settings, knowledge_collection):
    # knowledge_collection is session-scoped; its presence ensures services are up.
    del settings, knowledge_collection
    return TestClient(create_app())


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ask_returns_answer_with_sources(client: TestClient, knowledge_collection) -> None:
    r = client.post(
        "/ask",
        json={
            "question": "Onde descartar medicamento vencido?",
            "collection": knowledge_collection,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["refused"] is False
    assert body["sources"], "expected at least one source"
    assert body["sources"][0]["score"] > 0
    assert isinstance(body["answer"], str) and body["answer"].strip()
    # Two-track retrieval: transcripts are tone reference, never citable.
    cited = {s["category"] for s in body["sources"]}
    assert "transcricao" not in cited, (
        f"transcripts must not appear as citable sources, got {cited}"
    )


def test_ask_refusal_path(client: TestClient, knowledge_collection) -> None:
    r = client.post(
        "/ask",
        json={
            "question": "How do I launch a rocket to the moon?",
            "collection": knowledge_collection,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["refused"] is True
    assert body["sources"] == []


def test_ask_category_filter(client: TestClient, knowledge_collection) -> None:
    r = client.post(
        "/ask",
        json={
            "question": "Como descartar medicamento vencido?",
            "collection": knowledge_collection,
            "category_filter": "politica",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["sources"], "filtered query should still have sources"
    assert {s["category"] for s in body["sources"]} == {"politica"}


def test_ingest_endpoint(client: TestClient, settings) -> None:
    from opencall_agent.vector import make_client

    qd = make_client(settings)
    collection = "test_api_ingest"
    if qd.collection_exists(collection):
        qd.delete_collection(collection)
    try:
        r = client.post(
            "/ingest",
            params={"category": "politica", "collection": collection},
            files={
                "file": (
                    "note.txt",
                    "A política X é válida por trinta dias corridos.",
                    "text/plain",
                )
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["chunks"] >= 1
        assert body["collection"] == collection
    finally:
        if qd.collection_exists(collection):
            qd.delete_collection(collection)


def test_ingest_rejects_unsupported_format(client: TestClient) -> None:
    r = client.post(
        "/ingest",
        params={"category": "politica"},
        files={"file": ("doc.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert r.status_code == 400
    assert "Unsupported format" in r.json()["detail"]
