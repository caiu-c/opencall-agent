"""LangGraph agent: llm → retrieve_tool → (refuse | synthesize)."""

from __future__ import annotations

import json
from typing import Annotated, TypedDict
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from qdrant_client import QdrantClient

from ..config import Settings
from ..llm import complete
from ..vector import Hit, retrieve
from .prompts import SYSTEM_PROMPT, USER_TEMPLATE, format_contexts
from .rag_chain import REFUSAL_PHRASE, RagResponse, SourceRef

RETRIEVE_TOOL_NAME = "retrieve"


class AgentState(TypedDict):
    """Graph state carried between nodes.

    `messages` is append-only (via `add_messages`) to keep a chronological
    trace that M8 observability can read without re-executing the graph.
    """

    question: str
    collection: str
    messages: Annotated[list, add_messages]
    hits: list[Hit]
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
    call_id = f"call_{uuid4().hex[:8]}"
    ai = AIMessage(
        content="",
        tool_calls=[
            {
                "id": call_id,
                "name": RETRIEVE_TOOL_NAME,
                "args": {"query": state["question"]},
            }
        ],
    )
    return {"messages": [ai]}


def _retrieve_node(
    state: AgentState, *, settings: Settings, client: QdrantClient
) -> dict:
    last_ai = next(
        msg for msg in reversed(state["messages"]) if isinstance(msg, AIMessage)
    )
    call = last_ai.tool_calls[0]
    query = call["args"]["query"]

    hits = retrieve(settings, client, query, state["collection"])
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
    contexts = format_contexts([h.text for h in state["hits"]])
    prompt_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_TEMPLATE.format(question=state["question"], contexts=contexts),
        },
    ]
    text = complete(settings, prompt_messages)
    return {
        "answer": text,
        "refused": False,
        "messages": [AIMessage(content=text)],
    }


def _refuse_node(state: AgentState) -> dict:
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
) -> RagResponse:
    """Run the agent graph to produce a RagResponse."""
    app = _get_compiled(settings, client)
    initial: AgentState = {
        "question": question,
        "collection": collection,
        "messages": [HumanMessage(content=question)],
        "hits": [],
        "sources": [],
        "retrieval_scores": [],
        "refused": False,
        "answer": "",
    }
    final = app.invoke(initial)
    return RagResponse(
        answer=final["answer"],
        sources=final["sources"],
        refused=final["refused"],
        retrieval_scores=final["retrieval_scores"],
    )
