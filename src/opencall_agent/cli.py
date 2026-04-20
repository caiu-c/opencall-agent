"""Unified CLI for opencall-agent."""

from __future__ import annotations

from pathlib import Path

import typer

from .config import get_settings
from .ingestion.indexer import ingest_document
from .vector import make_client

app = typer.Typer(help="opencall-agent CLI", no_args_is_help=True)

DEFAULT_COLLECTION = "knowledge"

CATEGORY_BY_PREFIX = {
    "politica": "politica",
    "faq": "faq",
    "transcricao": "transcricao",
    "produto": "produto",
    "regulatorio": "regulatorio",
}


def _infer_category(filename: str) -> str | None:
    prefix = filename.split("_", 1)[0].lower()
    return CATEGORY_BY_PREFIX.get(prefix)


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


@app.command("ingest-dir")
def ingest_dir(
    directory: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Directory of .txt/.md files. Category is inferred from filename prefix.",
    ),
    collection: str = typer.Option(
        DEFAULT_COLLECTION,
        "--collection",
        help="Qdrant collection name.",
    ),
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Drop the collection before ingesting (reproducible from scratch).",
    ),
) -> None:
    """Ingest every supported file in a directory, inferring category from the filename prefix."""
    from .ingestion.loader import SUPPORTED_EXTENSIONS

    settings = get_settings()
    client = make_client(settings)

    if reset and client.collection_exists(collection):
        client.delete_collection(collection)
        typer.echo(f"Dropped collection '{collection}'.")

    files = sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not files:
        typer.echo(f"No ingestible files in {directory}", err=True)
        raise typer.Exit(code=1)

    total_docs = 0
    total_chunks = 0
    skipped: list[str] = []
    for path in files:
        category = _infer_category(path.name)
        if category is None:
            skipped.append(path.name)
            continue
        n = ingest_document(settings, client, path, category=category, collection=collection)
        typer.echo(f"  {path.name} -> {n} chunks (category={category})")
        total_docs += 1
        total_chunks += n

    typer.echo(
        f"Done. Ingested {total_docs} docs, {total_chunks} chunks into '{collection}'."
    )
    if skipped:
        typer.echo(f"Skipped {len(skipped)} file(s) with unknown prefix: {skipped}", err=True)


if __name__ == "__main__":
    app()
