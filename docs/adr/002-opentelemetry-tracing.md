# ADR 002 — OpenTelemetry for agent tracing

- Status: accepted
- Date: 2026-04-20
- Milestone: M8

## Context

M8 requires traces for every agent run so the team can answer "why did it
refuse?", "which chunk was decisive?", "where did latency go?" without
re-running the agent in a notebook. The execution plan explicitly lists
OpenTelemetry console + optional Langfuse. Before committing, we weighed
the alternatives.

## Decision

Adopt the **OpenTelemetry Python SDK** with a `ConsoleSpanExporter` by
default. Tests substitute an `InMemorySpanExporter`. A hosted exporter
(Langfuse, Jaeger, Honeycomb) is a configuration change, not a code
change.

Span topology:

- `agent.run` (root) — carries the collection, category filter, refusal
  flag.
- `agent.node.llm` — plans the tool call.
- `agent.node.retrieve_tool` — records query, category, hit count, top
  score.
- `agent.node.synthesize` / `agent.node.refuse` — mutually exclusive.
- `llm.complete` (child of `synthesize`) — isolates the LLM round-trip so
  latency dashboards can split embedding vs. generation.

## Alternatives considered

1. **LangSmith (langchain-native).** Deep integration, trivial to adopt
   via env var. Rejected because (a) it couples the repo to a SaaS vendor
   for what is otherwise a self-contained portfolio demo, and (b) the
   on-call operator will want a generic format they can plug into an
   existing observability stack.
2. **`structlog` + JSON logs.** Cheap, but logs are not traces — you
   lose parent/child causation, duration, span attributes by convention.
   The extra complexity of OTEL pays for itself the first time someone
   asks "what took 14 seconds?".
3. **Langfuse only (no OTEL).** Langfuse is excellent for LLM-specific
   traces but runs as a stateful container. Too much ops for a demo
   default; kept as the "optional" escape hatch the spec already names.

## PII handling (NFR-10)

Span attributes that can carry user- or document-derived strings (query,
retrieved chunk text, answer) are routed through `observability.scrub`,
which masks CPF, email and phone with fixed placeholders. The scrubber is
a pure function with unit tests; applying it uniformly at the edge keeps
the callers dumb.

## Consequences

- **Positive.** Every call to `agent.answer` emits a self-contained
  trace. Tests pin span presence and shape via
  `InMemorySpanExporter` — regressions that drop a node from the graph
  fail immediately.
- **Negative.** `ConsoleSpanExporter` is noisy on real traffic; operators
  must swap it for an OTLP exporter. The default sampler is `ALWAYS_ON`;
  a real deployment will want a ratio sampler.
- **Follow-ups.** (a) Wire an OTLP exporter env var before M10. (b) Add
  HTTP server-side spans when M9 lands so the FastAPI request ties to
  the agent trace.
