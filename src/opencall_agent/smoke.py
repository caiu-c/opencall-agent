"""End-to-end smoke test: validates Ollama (LLM + embeddings) and Qdrant."""

from __future__ import annotations

import sys

from qdrant_client.models import PointStruct

from . import llm, vector
from .config import get_settings

COLLECTION = "smoke_test"


def main() -> int:
    settings = get_settings()
    try:
        print("[1/3] LLM via LiteLLM...", flush=True)
        answer = llm.complete(
            settings,
            [{"role": "user", "content": "Responda em uma frase: o que e RAG?"}],
        )
        print(f"      -> {answer[:200]}")

        print("[2/3] Embedding via LiteLLM...", flush=True)
        vectors = llm.embed(
            settings,
            ["ligacao sobre cobranca indevida", "cliente quer cancelar plano"],
        )
        dim = len(vectors[0])
        print(f"      -> {len(vectors)} vetores, dim={dim}")

        print("[3/3] Qdrant round-trip...", flush=True)
        client = vector.make_client(settings)
        vector.ensure_collection(client, COLLECTION, dim, recreate=True)
        client.upsert(
            collection_name=COLLECTION,
            points=[
                PointStruct(id=1, vector=vectors[0], payload={"text": "cobranca indevida"}),
                PointStruct(id=2, vector=vectors[1], payload={"text": "cancelamento de plano"}),
            ],
        )
        query_vec = llm.embed(settings, ["quero reclamar de uma cobranca"])[0]
        hits = client.query_points(collection_name=COLLECTION, query=query_vec, limit=1).points
        top = hits[0]
        print(f"      -> top hit: '{top.payload['text']}' (score={top.score:.3f})")
    except Exception as exc:  # noqa: BLE001
        print(f"\nFAILED: {exc}", file=sys.stderr)
        return 1
    print("\nOK: Ollama + LiteLLM + Qdrant wired up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
