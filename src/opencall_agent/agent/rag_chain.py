"""Basic retrieve → stuff-prompt → answer chain with citation + refusal."""

from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient

from ..config import Settings
from ..llm import complete
from ..vector import Hit, retrieve
from .prompts import SYSTEM_PROMPT, USER_TEMPLATE, format_contexts

REFUSAL_PHRASE = (
    "Não encontrei essa informação na base de conhecimento. "
    "Recomendo consultar o farmacêutico responsável."
)


@dataclass(frozen=True)
class SourceRef:
    doc_id: str
    chunk_id: str
    source: str
    category: str
    score: float


@dataclass(frozen=True)
class RagResponse:
    answer: str
    sources: list[SourceRef]
    refused: bool
    retrieval_scores: list[float]


def _to_source_ref(hit: Hit) -> SourceRef:
    return SourceRef(
        doc_id=hit.doc_id,
        chunk_id=hit.chunk_id,
        source=hit.source,
        category=hit.category,
        score=hit.score,
    )


def answer(
    settings: Settings,
    client: QdrantClient,
    question: str,
    collection: str,
) -> RagResponse:
    """Answer `question` using documents from `collection`.

    Refuses (without calling the LLM) when no chunk clears the configured score
    threshold, ensuring US-A3 cannot regress into hallucination.
    """
    hits = retrieve(settings, client, question, collection)
    scores = [h.score for h in hits]

    if not hits or hits[0].score < settings.retrieval_score_threshold:
        return RagResponse(
            answer=REFUSAL_PHRASE,
            sources=[],
            refused=True,
            retrieval_scores=scores,
        )

    contexts = format_contexts([h.text for h in hits])
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(question=question, contexts=contexts)},
    ]
    text = complete(settings, messages)

    return RagResponse(
        answer=text,
        sources=[_to_source_ref(h) for h in hits],
        refused=False,
        retrieval_scores=scores,
    )
