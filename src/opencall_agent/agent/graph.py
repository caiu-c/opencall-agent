"""LangGraph agent: llm → retrieve_tool → (refuse | synthesize)."""

from __future__ import annotations

import json
from typing import Annotated, TypedDict
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from ..config import Settings
from ..llm import complete
from ..observability import get_tracer, set_attr
from ..vector import Hit, retrieve
from .prompts import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    filter_note,
    format_contexts,
    format_style_block,
)
from .rag_chain import REFUSAL_PHRASE, RagResponse, SourceRef

RETRIEVE_TOOL_NAME = "retrieve"
# Transcripts are synthesized dialog — used only as tone reference, never cited
# as factual source. See docs/requirements.md §7 and ADR 003.
STYLE_CATEGORY = "transcricao"


def _factual_filter(category: str | None) -> Filter | None:
    """Filter for the citable retrieval pass.

    Explicit user-supplied category passes through as-is (including the
    degenerate `transcricao` case — preserved for debugging/browsing via the
    CLI). Default path excludes `transcricao` so synthesized dialog can never
    be cited in a normal answer.
    """
    if category:
        return Filter(must=[FieldCondition(key="category", match=MatchValue(value=category))])
    return Filter(
        must_not=[FieldCondition(key="category", match=MatchValue(value=STYLE_CATEGORY))]
    )


def _style_filter() -> Filter:
    return Filter(
        must=[FieldCondition(key="category", match=MatchValue(value=STYLE_CATEGORY))]
    )


class AgentState(TypedDict):
    """Graph state carried between nodes.

    `messages` is append-only (via `add_messages`) to keep a chronological
    trace that M8 observability can read without re-executing the graph.
    """

    question: str
    collection: str
    category_filter: str | None
    messages: Annotated[list, add_messages]
    hits: list[Hit]
    style_hits: list[Hit]
    sources: list[SourceRef]
    retrieval_scores: list[float]
    refused: bool
    answer: str


def _to_source_ref(hit: Hit) -> SourceRef:
    return SourceRef(
        doc_id=hit.doc_id,
        chunk_id=hit.chunk_id,
        source=hit.source,
        category=hit.category,
        score=hit.score,
    )


def _plan_node(state: AgentState) -> dict:
    """`llm` node: emits a tool_call intent for retrieve.

    Deterministic on purpose — qwen2.5:7b on Ollama handles tool-calling but
    unreliably enough for a CPU-local portfolio demo. We keep the structural
    ReAct shape (AIMessage with tool_calls → ToolMessage → final LLM turn)
    so downstream nodes and trace consumers see a recognizable agent loop.
    """
    with get_tracer().start_as_current_span("agent.node.llm") as span:
        call_id = f"call_{uuid4().hex[:8]}"
        args: dict = {"query": state["question"]}
        if state.get("category_filter"):
            args["category"] = state["category_filter"]
        set_attr(span, "agent.tool_call_id", call_id)
        set_attr(span, "agent.tool_name", RETRIEVE_TOOL_NAME)
        set_attr(span, "agent.question", state["question"])
        ai = AIMessage(
            content="",
            tool_calls=[
                {
                    "id": call_id,
                    "name": RETRIEVE_TOOL_NAME,
                    "args": args,
                }
            ],
        )
        return {"messages": [ai]}


def _retrieve_node(
    state: AgentState, *, settings: Settings, client: QdrantClient
) -> dict:
    """Two-track retrieval: factual (citable) + stylistic (tone-only).

    Only the factual pass round-trips through the tool-message protocol —
    the ReAct shape tracked in US-S4 traces is about the model's citable
    reasoning, so the stylistic pass is an internal side-retrieval.
    """
    with get_tracer().start_as_current_span("agent.node.retrieve_tool") as span:
        last_ai = next(
            msg for msg in reversed(state["messages"]) if isinstance(msg, AIMessage)
        )
        call = last_ai.tool_calls[0]
        query = call["args"]["query"]
        category = call["args"].get("category")
        set_attr(span, "retrieval.query", query)
        set_attr(span, "retrieval.category", category or "")

        with get_tracer().start_as_current_span("retrieval.factual") as fspan:
            hits = retrieve(
                settings,
                client,
                query,
                state["collection"],
                query_filter=_factual_filter(category),
            )
            set_attr(fspan, "retrieval.hits", len(hits))
            if hits:
                set_attr(fspan, "retrieval.top_score", hits[0].score)

        style_hits: list[Hit] = []
        if settings.style_top_k > 0 and not category:
            # Skip style when the caller pins a specific category — they're
            # either debugging or deliberately narrowing scope, and in either
            # case injecting off-topic tone examples would add noise.
            with get_tracer().start_as_current_span("retrieval.style") as sspan:
                style_hits = retrieve(
                    settings,
                    client,
                    query,
                    state["collection"],
                    k=settings.style_top_k,
                    query_filter=_style_filter(),
                )
                set_attr(sspan, "retrieval.hits", len(style_hits))

        set_attr(span, "retrieval.hits", len(hits))
        set_attr(span, "retrieval.style_hits", len(style_hits))
        if hits:
            set_attr(span, "retrieval.top_score", hits[0].score)

        sources = [_to_source_ref(h) for h in hits]
        payload = [
            {"idx": i + 1, "score": round(h.score, 4), "source": h.source, "text": h.text}
            for i, h in enumerate(hits)
        ]
        tool_msg = ToolMessage(
            content=json.dumps(payload, ensure_ascii=False),
            tool_call_id=call["id"],
            name=RETRIEVE_TOOL_NAME,
        )
        return {
            "hits": hits,
            "style_hits": style_hits,
            "sources": sources,
            "retrieval_scores": [h.score for h in hits],
            "messages": [tool_msg],
        }


def _route_after_retrieve(state: AgentState, *, settings: Settings) -> str:
    hits = state["hits"]
    if not hits or hits[0].score < settings.retrieval_score_threshold:
        return "refuse"
    return "synthesize"


def _synthesize_node(state: AgentState, *, settings: Settings) -> dict:
    with get_tracer().start_as_current_span("agent.node.synthesize") as span:
        contexts = format_contexts([h.text for h in state["hits"]])
        style_block = format_style_block([h.text for h in state.get("style_hits", [])])
        user = USER_TEMPLATE.format(
            question=state["question"],
            filter_note=filter_note(state.get("category_filter")),
            contexts=contexts,
        )
        prompt_messages = [
            {"role": "system", "content": SYSTEM_PROMPT + style_block},
            {"role": "user", "content": user},
        ]
        set_attr(span, "llm.model", settings.llm_model)
        set_attr(span, "llm.context_chunks", len(state["hits"]))
        set_attr(span, "llm.style_examples", len(state.get("style_hits", [])))
        with get_tracer().start_as_current_span("llm.complete") as llm_span:
            text = complete(settings, prompt_messages)
            set_attr(llm_span, "llm.response_chars", len(text))
        return {
            "answer": text,
            "refused": False,
            "messages": [AIMessage(content=text)],
        }


def _refuse_node(state: AgentState) -> dict:
    with get_tracer().start_as_current_span("agent.node.refuse") as span:
        top = state["retrieval_scores"][0] if state["retrieval_scores"] else 0.0
        set_attr(span, "agent.top_score", top)
        return {
            "answer": REFUSAL_PHRASE,
            "refused": True,
            "sources": [],
            "messages": [AIMessage(content=REFUSAL_PHRASE)],
        }


def build_graph(settings: Settings, client: QdrantClient):
    """Compile the agent graph bound to a (settings, client) pair."""

    def retrieve_node(state: AgentState) -> dict:
        return _retrieve_node(state, settings=settings, client=client)

    def route(state: AgentState) -> str:
        return _route_after_retrieve(state, settings=settings)

    def synthesize_node(state: AgentState) -> dict:
        return _synthesize_node(state, settings=settings)

    graph = StateGraph(AgentState)
    graph.add_node("llm", _plan_node)
    graph.add_node("retrieve_tool", retrieve_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("refuse", _refuse_node)

    graph.add_edge(START, "llm")
    graph.add_edge("llm", "retrieve_tool")
    graph.add_conditional_edges(
        "retrieve_tool",
        route,
        {"synthesize": "synthesize", "refuse": "refuse"},
    )
    graph.add_edge("synthesize", END)
    graph.add_edge("refuse", END)
    return graph.compile()


_GRAPH_CACHE: dict[tuple[int, int], object] = {}


def _get_compiled(settings: Settings, client: QdrantClient):
    key = (id(settings), id(client))
    app = _GRAPH_CACHE.get(key)
    if app is None:
        app = build_graph(settings, client)
        _GRAPH_CACHE[key] = app
    return app


def answer(
    settings: Settings,
    client: QdrantClient,
    question: str,
    collection: str,
    category_filter: str | None = None,
) -> RagResponse:
    """Run the agent graph to produce a RagResponse."""
    app = _get_compiled(settings, client)
    initial: AgentState = {
        "question": question,
        "collection": collection,
        "category_filter": category_filter,
        "messages": [HumanMessage(content=question)],
        "hits": [],
        "style_hits": [],
        "sources": [],
        "retrieval_scores": [],
        "refused": False,
        "answer": "",
    }
    with get_tracer().start_as_current_span("agent.run") as span:
        set_attr(span, "agent.collection", collection)
        set_attr(span, "agent.category_filter", category_filter or "")
        final = app.invoke(initial)
        set_attr(span, "agent.refused", final["refused"])
    return RagResponse(
        answer=final["answer"],
        sources=final["sources"],
        refused=final["refused"],
        retrieval_scores=final["retrieval_scores"],
    )
