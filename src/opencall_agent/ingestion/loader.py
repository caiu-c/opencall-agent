"""Read raw document content from disk."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTENSIONS = frozenset({".txt", ".md"})


def load_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported format '{suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    return path.read_text(encoding="utf-8")
