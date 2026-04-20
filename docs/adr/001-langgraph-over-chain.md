# ADR 001 — LangGraph agent over direct RAG chain

- Status: accepted
- Date: 2026-04-20
- Milestone: M5

## Context

M4 shipped `agent.rag_chain.answer`: a straight function call chaining
`retrieve → stuff-prompt → complete`. It meets US-A1..A4 today, but the
project spec (M5) commits to an agent architecture for three reasons:

1. **Extensibility.** M6 introduces metadata filters; M8 adds observability;
   M7 adds an evaluation harness. Each of these wants to hook into decision
   points (when to retrieve, with which filter, what context survived
   re-ranking) without rewriting the happy path.
2. **Traceability.** A graph execution emits a sequence of node updates that
   downstream tooling (LangSmith, custom OTEL spans) can consume without
   instrumenting call sites. A function chain would need bespoke spans per
   step.
3. **Portfolio intent.** The README markets the project as "engineering over
   chains" — the public stack explicitly calls out LangGraph as the
   orchestration layer. Leaving the direct chain would contradict the pitch.

## Decision

Replace the call-site exposure of `rag_chain.answer` with a LangGraph
`StateGraph` compiled in `agent.graph.build_graph`. The graph has four
nodes:

- `llm` — deterministically emits an `AIMessage` carrying a `retrieve` tool
  call. For a portfolio demo running `qwen2.5:7b` on local CPU, *real*
  tool-calling is flaky enough that a demo regression would be worse than
  the architectural deviation; the shape of the trace (AIMessage with
  tool_calls → ToolMessage → AIMessage) is preserved.
- `retrieve_tool` — executes `vector.retrieve` and appends a `ToolMessage`
  with the serialized hits.
- A conditional edge routes to `refuse` or `synthesize` based on whether
  the top hit clears `retrieval_score_threshold`.
- `synthesize` — stuff-prompt + LLM call producing the final answer.
- `refuse` — short-circuits with a canned PT-BR refusal.

The public entry point `agent.answer(settings, client, question, collection)`
preserves the M4 signature and `RagResponse` contract — callers (CLI, tests)
do not need to change.

## Alternatives considered

1. **Keep the chain, add instrumentation points manually.** Cheapest in
   code but contradicts the project's stated architecture and doesn't buy
   anything when M6..M8 arrive; we'd refactor anyway.
2. **LangGraph prebuilt `create_react_agent`.** Minimal code but hides the
   graph structure and the loop control we want to exercise (refusal edge,
   metadata filter routing in M6). Rejected for not teaching what the repo
   is meant to teach.
3. **Real LLM-driven tool calling.** Correct for a production agent. On
   qwen2.5:7b on local CPU, tool calls emerge unreliably (missing args,
   wrong names, occasional hallucinated tools). Deferred until the stack
   either moves to a hosted model or ships an eval harness (M7) that can
   catch regressions. The current implementation is shaped so that
   swapping the `llm` node to real tool calling is a single-file change.

## Consequences

- **Positive.** Explicit state (`AgentState`) makes M6 (filters), M7 (eval
  passes the same state), and M8 (OTEL spans per node) low-friction.
  `rag_chain.answer` stays in the repo as a reference implementation and a
  shortcut for developers who want to test retrieval without the graph
  overhead.
- **Negative.** The `llm` node is not genuinely "LLM-driven" yet; a reader
  expecting ReAct will need to read the comment. Mitigated by the node
  name, the canonical tool-call/tool-message shape, and this ADR.
- **Follow-ups.** (a) Revisit real tool calling after M7's eval harness
  exists. (b) Consider splitting `rag_chain.py` out of `agent/` once the
  graph path is the only production surface.
