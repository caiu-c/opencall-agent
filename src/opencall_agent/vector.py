"""Qdrant client factory + collection helpers."""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from .config import Settings


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
