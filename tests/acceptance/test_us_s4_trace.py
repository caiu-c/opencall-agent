"""US-S4 — every agent run emits an OTEL trace with retrieval + llm spans."""

from __future__ import annotations

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from opencall_agent.agent import RETRIEVE_TOOL_NAME, answer, build_graph
from opencall_agent.observability import configure_tracing
from opencall_agent.vector import make_client

pytestmark = pytest.mark.acceptance


@pytest.fixture
def span_exporter():
    exporter = InMemorySpanExporter()
    configure_tracing(exporter=exporter)
    yield exporter
    exporter.clear()


def test_agent_run_emits_trace(settings, knowledge_collection, span_exporter) -> None:
    client = make_client(settings)
    resp = answer(
        settings, client, "Onde descartar medicamento vencido?", knowledge_collection
    )
    assert not resp.refused

    spans = span_exporter.get_finished_spans()
    names = {s.name for s in spans}
    assert "agent.run" in names
    assert "agent.node.llm" in names
    assert "agent.node.retrieve_tool" in names
    assert "agent.node.synthesize" in names
    assert "llm.complete" in names

    for span in spans:
        assert (span.end_time or 0) > (span.start_time or 0), (
            f"span {span.name} has no duration"
        )

    retrieve_span = next(s for s in spans if s.name == "agent.node.retrieve_tool")
    assert retrieve_span.attributes.get("retrieval.hits", 0) > 0


def test_agent_run_invokes_retrieve_tool(settings, knowledge_collection) -> None:
    """Structural check retained from M5: the graph visits the tool node."""
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    client = make_client(settings)
    app = build_graph(settings, client)
    initial = {
        "question": "Onde descartar medicamento vencido?",
        "collection": knowledge_collection,
        "category_filter": None,
        "messages": [HumanMessage(content="Onde descartar medicamento vencido?")],
        "hits": [],
        "sources": [],
        "retrieval_scores": [],
        "refused": False,
        "answer": "",
    }
    final = app.invoke(initial)

    tool_calls = [
        call
        for msg in final["messages"]
        if isinstance(msg, AIMessage)
        for call in (msg.tool_calls or [])
    ]
    assert any(c["name"] == RETRIEVE_TOOL_NAME for c in tool_calls)
    assert any(
        isinstance(m, ToolMessage) and m.name == RETRIEVE_TOOL_NAME
        for m in final["messages"]
    )
