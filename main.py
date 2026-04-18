"""Smoke test: validates Ollama (LLM + embeddings) and Qdrant are wired up."""

from __future__ import annotations

import sys

import litellm
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

LLM_MODEL = "ollama/qwen2.5:7b"
EMBED_MODEL = "ollama/nomic-embed-text"
OLLAMA_BASE = "http://localhost:11434"
QDRANT_URL = "http://localhost:6333"
COLLECTION = "smoke_test"


def check_llm() -> None:
    print("[1/3] LLM via LiteLLM...", flush=True)
    resp = litellm.completion(
        model=LLM_MODEL,
        api_base=OLLAMA_BASE,
        messages=[{"role": "user", "content": "Responda em uma frase: o que é RAG?"}],
    )
    print(f"      -> {resp.choices[0].message.content.strip()[:200]}")


def check_embed_and_qdrant() -> None:
    print("[2/3] Embedding via LiteLLM...", flush=True)
    emb = litellm.embedding(
        model=EMBED_MODEL,
        api_base=OLLAMA_BASE,
        input=["ligacao sobre cobranca indevida", "cliente quer cancelar plano"],
    )
    vectors = [item["embedding"] for item in emb.data]
    dim = len(vectors[0])
    print(f"      -> {len(vectors)} vetores, dim={dim}")

    print("[3/3] Qdrant round-trip...", flush=True)
    client = QdrantClient(url=QDRANT_URL)
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )
    client.upsert(
        collection_name=COLLECTION,
        points=[
            PointStruct(id=1, vector=vectors[0], payload={"text": "cobranca indevida"}),
            PointStruct(id=2, vector=vectors[1], payload={"text": "cancelamento de plano"}),
        ],
    )
    query = litellm.embedding(
        model=EMBED_MODEL,
        api_base=OLLAMA_BASE,
        input=["quero reclamar de uma cobranca"],
    ).data[0]["embedding"]
    hits = client.query_points(collection_name=COLLECTION, query=query, limit=1).points
    top = hits[0]
    print(f"      -> top hit: '{top.payload['text']}' (score={top.score:.3f})")


def main() -> int:
    try:
        check_llm()
        check_embed_and_qdrant()
    except Exception as exc:  # noqa: BLE001
        print(f"\nFAILED: {exc}", file=sys.stderr)
        return 1
    print("\nOK: Ollama + LiteLLM + Qdrant wired up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
