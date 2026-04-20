"""M5 DoD — trace of an agent run shows the retrieve tool invocation.

Companion to US-A1..A4: these keep passing via the graph, while this test
asserts the graph actually invokes the retrieve tool node and emits a
ToolMessage with the canonical tool name. Without this, the agent could
regress into a direct LLM call and nobody would notice.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from opencall_agent.agent import RETRIEVE_TOOL_NAME, build_graph
from opencall_agent.agent.graph import AgentState
from opencall_agent.vector import make_client

pytestmark = pytest.mark.acceptance


def test_agent_run_invokes_retrieve_tool(settings, knowledge_collection) -> None:
    client = make_client(settings)
    app = build_graph(settings, client)
    initial: AgentState = {
        "question": "Onde descartar medicamento vencido?",
        "collection": knowledge_collection,
        "messages": [HumanMessage(content="Onde descartar medicamento vencido?")],
        "hits": [],
        "sources": [],
        "retrieval_scores": [],
        "refused": False,
        "answer": "",
    }

    nodes_visited: list[str] = []
    for step in app.stream(initial, stream_mode="updates"):
        nodes_visited.extend(step.keys())

    assert "llm" in nodes_visited, "llm node must plan the tool call"
    assert "retrieve_tool" in nodes_visited, "retrieve_tool node must execute"
    assert "synthesize" in nodes_visited, "successful query must synthesize an answer"

    final = app.invoke(initial)
    tool_calls = [
        call
        for msg in final["messages"]
        if isinstance(msg, AIMessage)
        for call in (msg.tool_calls or [])
    ]
    assert any(c["name"] == RETRIEVE_TOOL_NAME for c in tool_calls), (
        "trace must include an AIMessage carrying a retrieve tool_call"
    )
    assert any(
        isinstance(m, ToolMessage) and m.name == RETRIEVE_TOOL_NAME
        for m in final["messages"]
    ), "trace must include a ToolMessage produced by retrieve_tool"
