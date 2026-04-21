# opencall-agent — Execution Plan

> Canonical version (EN). Portuguese mirror: [execution-plan.pt-br.md](./execution-plan.pt-br.md). Derived from [requirements.md](./requirements.md) and [test-plan.md](./test-plan.md).

## Principles

- Each milestone is a mergeable PR.
- Each milestone has a **Definition of Done** citing user stories and tests.
- Order is suggested, not rigid — blockers can reshuffle.
- Architectural decisions logged in `docs/adr/` (introduced at M5).

## Milestones

### M0 — Scaffold & stack validation ✅ done
- Repo, deps, Qdrant in Docker, Ollama models, smoke test.
- **DoD:** `uv run main.py` passes end-to-end.

### M1 — Project structure & configuration
**Goal:** move from flat `main.py` to `src/opencall_agent/` package + config layer.
- Restructure: `src/opencall_agent/{config, llm, vector, ingestion, agent}`
- `pydantic-settings` for env-driven config
- `.env.example` committed
- Unit tests for config loading
- **DoD:** `uv run pytest` green; smoke test still passes from the package entrypoint.

### M2 — Document ingestion (US-S1)
**Goal:** ingest PDF/TXT/MD into Qdrant with metadata.
- `ingestion.load` per format (start with TXT + MD; PDF via `pypdf`)
- `ingestion.chunk` (sentence-aware + overlap)
- `ingestion.embed` (LiteLLM → Ollama)
- `ingestion.index` (Qdrant upsert with payload: source, date, category)
- CLI: `uv run opencall ingest <path> --category <cat>`
- Unit: chunker; Integration: round-trip
- **DoD:** US-S1 acceptance test passes; sample TXT corpus ingested.

### M3 — Domain data & gold set
**Goal:** seed realistic call-center knowledge base (unblocks retrieval quality work).
- Resolve open questions: anchor domain, data source, filter taxonomy
- Generate/curate ~20 policies, ~10 FAQs, ~10 mock transcripts in `data/samples/`
- Ingest via M2 pipeline
- Gold set: 30 Q&A rows in `tests/eval/gold.jsonl`
- **DoD:** sample data + gold set checked in; ingestion reproducible from scratch.

### M4 — Basic RAG (US-A1..A4)
**Goal:** CLI Q&A: question → retrieve top-k → answer with citations.
- `vector.retrieve(query, k=5, filter=None)`
- `agent.rag_chain`: simple retrieve → stuff-prompt → LLM
- Citation post-processing (map chunks → source refs)
- Refusal path when top score < threshold
- CLI: `uv run opencall ask "<q>"`
- **DoD:** US-A1, US-A2, US-A3, US-A4 acceptance tests pass.

### M5 — LangGraph agent
**Goal:** replace direct chain with a LangGraph agent exposing `retrieve` as a tool.
- `AgentState` (messages, tool calls, sources)
- Nodes: `llm`, `retrieve_tool`, `synthesize`
- Conditional edges for tool loop
- Agent replaces `rag_chain` in CLI (same interface)
- First ADR: `docs/adr/001-langgraph-over-chain.md`
- **DoD:** M4 acceptance tests still pass through the agent; trace shows tool invocation.

### M6 — Metadata filtering (US-S2)
**Goal:** expose filter parameters to the agent.
- Add `filter` arg to retrieve tool
- Agent prompt teaches when to apply filters
- CLI: `uv run opencall ask "<q>" --filter category=policy`
- **DoD:** US-S2 acceptance test passes.

### M7 — Evaluation harness (US-S3)
**Goal:** reproducible quality measurement.
- `eval` module: runs gold set through agent → collects (q, a, contexts, expected)
- ragas integration: context_precision, faithfulness, answer_relevancy, answer_correctness
- JSON + Markdown report → `eval_reports/`
- CLI: `uv run opencall eval`
- Thresholds from NFR-4, NFR-5 enforced
- **DoD:** US-S3 acceptance test passes; baseline report committed.

### M8 — Observability (US-S4)
**Goal:** traces for every agent run.
- ADR decides: OpenTelemetry console + optional Langfuse container
- Span per node, context propagation
- PII scrubber in logging layer (NFR-10)
- **DoD:** US-S4 acceptance test passes; sample trace screenshotted in docs.

### M9 — HTTP API
**Goal:** expose the agent over FastAPI.
- `POST /ask` → `{ answer, sources, trace_id }`
- `POST /ingest` for supervisors
- OpenAPI auto-generated
- CLI: `uv run opencall serve`
- **DoD:** integration test hits API end-to-end.

### M10 — Deployment
**Goal:** one-command stand-up.
- `docker-compose.yml`: `api` + `qdrant` (+ optional `ollama`)
- Multi-stage `Dockerfile` (uv-based)
- README updated with deploy steps
- **DoD:** `docker compose up` + smoke query succeeds.

### M11 — Two-track retrieval
**Goal:** honor the original `transcricao = tone reference` commitment
(`requirements.md` §7) — transcripts influence how the agent speaks, never
what it cites.
- Factual retrieval excludes `category=transcricao`; style retrieval (top-K
  controlled by `OPENCALL_STYLE_TOP_K`) pulls transcript snippets into the
  system prompt only.
- Eval harness pins `style_top_k=0` so gold-set scores measure factual
  retrieval alone.
- Gold set cleaned: rows previously requiring `transcricao_*.txt` in
  `must_cite` re-tagged against the backing policy/faq sources.
- **DoD:** acceptance `test_us_s5_two_track` passes; eval recall ≥ baseline.

## Future (post-MVP)

- End-customer self-service bot
- Voice I/O
- Multi-tenancy
- Fine-tuning a small model on transcripts
- GitHub Actions CI
- OpenCall external integration (webhook/REST mock)
