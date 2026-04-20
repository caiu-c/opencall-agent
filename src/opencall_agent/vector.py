"""Qdrant client factory, collection helpers, and semantic retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, Filter, VectorParams

from .config import Settings
from .llm import embed


@dataclass(frozen=True)
class Hit:
    """Single retrieval result."""

    score: float
    doc_id: str
    chunk_id: str
    source: str
    category: str
    chunk_idx: int
    text: str


def make_client(settings: Settings) -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection(
    client: QdrantClient,
    name: str,
    dim: int,
    distance: Distance = Distance.COSINE,
    *,
    recreate: bool = False,
) -> None:
    exists = client.collection_exists(name)
    if exists and recreate:
        client.delete_collection(name)
        exists = False
    if not exists:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=distance),
        )


def retrieve(
    settings: Settings,
    client: QdrantClient,
    query: str,
    collection: str,
    k: int | None = None,
    query_filter: Filter | None = None,
) -> list[Hit]:
    """Embed `query` and return the top-k chunks from `collection`."""
    limit = k if k is not None else settings.retrieval_top_k
    [vector] = embed(settings, [query])
    result = client.query_points(
        collection_name=collection,
        query=vector,
        limit=limit,
        query_filter=query_filter,
        with_payload=True,
    )
    hits: list[Hit] = []
    for point in result.points:
        payload = point.payload or {}
        hits.append(
            Hit(
                score=point.score,
                doc_id=payload.get("doc_id", ""),
                chunk_id=str(point.id),
                source=payload.get("source", ""),
                category=payload.get("category", ""),
                chunk_idx=payload.get("chunk_idx", -1),
                text=payload.get("text", ""),
            )
        )
    return hits
