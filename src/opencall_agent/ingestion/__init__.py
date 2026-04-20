"""Document ingestion: load -> chunk -> embed -> index."""

from .chunker import chunk_text, split_sentences
from .indexer import ingest_document
from .loader import SUPPORTED_EXTENSIONS, load_document

__all__ = [
    "SUPPORTED_EXTENSIONS",
    "chunk_text",
    "ingest_document",
    "load_document",
    "split_sentences",
]
