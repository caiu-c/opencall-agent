"""Unified CLI for opencall-agent."""

from __future__ import annotations

from pathlib import Path

import typer

from .config import get_settings
from .ingestion.indexer import ingest_document
from .vector import make_client

app = typer.Typer(help="opencall-agent CLI", no_args_is_help=True)

DEFAULT_COLLECTION = "knowledge"


@app.command()
def smoke() -> None:
    """Run end-to-end stack smoke test (LLM + embedding + Qdrant)."""
    from .smoke import main as smoke_main

    raise typer.Exit(code=smoke_main())


@app.command()
def ingest(
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="File to ingest (.txt or .md).",
    ),
    category: str = typer.Option(
        ...,
        "--category",
        "-c",
        help="Taxonomy tag: politica | produto | faq | transcricao | regulatorio.",
    ),
    collection: str = typer.Option(
        DEFAULT_COLLECTION,
        "--collection",
        help="Qdrant collection name.",
    ),
) -> None:
    """Ingest a document into the knowledge base."""
    settings = get_settings()
    client = make_client(settings)
    n = ingest_document(settings, client, path, category=category, collection=collection)
    typer.echo(
        f"Ingested {n} chunk(s) from {path} (category={category}, collection={collection})"
    )


if __name__ == "__main__":
    app()
