"""FastAPI surface over the agent.

POST /ask     → question in, answer + sources + trace_id out
POST /ingest  → supervisor-only: ingest a single uploaded document
GET  /healthz → liveness

The API layer owns nothing beyond HTTP concerns: the agent and ingestion
pipelines are imported verbatim. Trace correlation piggybacks on OTEL's
current span context so downstream observability ties to the operator log.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from opentelemetry import trace
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

from .agent import answer as rag_answer
from .config import Settings, get_settings
from .ingestion.indexer import ingest_document
from .ingestion.loader import SUPPORTED_EXTENSIONS
from .observability import get_tracer
from .vector import make_client

DEFAULT_COLLECTION = "knowledge"


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    collection: str = DEFAULT_COLLECTION
    category_filter: str | None = Field(default=None, description="e.g. 'politica'")


class SourceOut(BaseModel):
    doc_id: str
    chunk_id: str
    source: str
    category: str
    score: float


class AskResponse(BaseModel):
    answer: str
    refused: bool
    sources: list[SourceOut]
    trace_id: str | None = None


class IngestResponse(BaseModel):
    chunks: int
    source: str
    category: str
    collection: str


class HealthResponse(BaseModel):
    status: str = "ok"


def _current_trace_id() -> str | None:
    span = trace.get_current_span()
    ctx = span.get_span_context() if span else None
    if not ctx or not ctx.is_valid:
        return None
    return f"{ctx.trace_id:032x}"


def get_app_settings() -> Settings:
    return get_settings()


def get_client(settings: Settings = Depends(get_app_settings)) -> QdrantClient:
    return make_client(settings)


def create_app() -> FastAPI:
    app = FastAPI(title="opencall-agent", version="0.1.0")

    @app.get("/healthz", response_model=HealthResponse)
    def healthz() -> HealthResponse:
        return HealthResponse()

    @app.post("/ask", response_model=AskResponse)
    def ask(
        req: AskRequest,
        settings: Settings = Depends(get_app_settings),
        client: QdrantClient = Depends(get_client),
    ) -> AskResponse:
        with get_tracer().start_as_current_span("api.ask"):
            resp = rag_answer(
                settings,
                client,
                req.question,
                req.collection,
                category_filter=req.category_filter,
            )
            return AskResponse(
                answer=resp.answer,
                refused=resp.refused,
                sources=[
                    SourceOut(
                        doc_id=s.doc_id,
                        chunk_id=s.chunk_id,
                        source=s.source,
                        category=s.category,
                        score=s.score,
                    )
                    for s in resp.sources
                ],
                trace_id=_current_trace_id(),
            )

    @app.post("/ingest", response_model=IngestResponse)
    def ingest(
        file: UploadFile,
        category: str,
        collection: str = DEFAULT_COLLECTION,
        settings: Settings = Depends(get_app_settings),
        client: QdrantClient = Depends(get_client),
    ) -> IngestResponse:
        filename = file.filename or ""
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
            )

        with get_tracer().start_as_current_span("api.ingest"):
            with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file.file.read())
                tmp_path = Path(tmp.name)
            try:
                n = ingest_document(
                    settings, client, tmp_path, category=category, collection=collection
                )
            finally:
                tmp_path.unlink(missing_ok=True)

        return IngestResponse(
            chunks=n, source=filename, category=category, collection=collection
        )

    return app


app = create_app()
