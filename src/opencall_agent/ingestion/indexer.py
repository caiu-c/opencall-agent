"""Orchestrates load -> chunk -> embed -> upsert."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from ..config import Settings
from ..llm import embed
from ..vector import ensure_collection
from .chunker import chunk_text
from .loader import load_document


def ingest_document(
    settings: Settings,
    client: QdrantClient,
    path: Path,
    category: str,
    collection: str,
) -> int:
    """Index a single document. Returns the number of chunks written."""
    text = load_document(path)
    chunks = chunk_text(text)
    if not chunks:
        return 0

    vectors = embed(settings, chunks)
    ensure_collection(client, collection, dim=len(vectors[0]))

    doc_id = str(uuid.uuid4())
    ingested_at = datetime.now(timezone.utc).isoformat()
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vectors[i],
            payload={
                "doc_id": doc_id,
                "source": str(path),
                "category": category,
                "ingested_at": ingested_at,
                "chunk_idx": i,
                "text": chunk,
            },
        )
        for i, chunk in enumerate(chunks)
    ]
    client.upsert(collection_name=collection, points=points)
    return len(points)
