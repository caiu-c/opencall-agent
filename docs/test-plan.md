# opencall-agent — Test Plan

> Canonical version (EN). Portuguese mirror: [test-plan.pt-br.md](./test-plan.pt-br.md). Derived from [requirements.md](./requirements.md).

## 1. Philosophy

Three execution layers plus a separate quality track:

- **Unit** — fast, isolated, no external services. Run on every commit.
- **Integration** — real Qdrant + real Ollama. Run on PR.
- **Acceptance** — user-story level, end-to-end. Run on PR.
- **RAG Eval** — quality metrics, tracked over time; regressions beyond budget block merge.

## 2. Tooling

- Test runner: `pytest` (+ `pytest-asyncio` for LangGraph)
- Ephemeral services (future CI): `testcontainers`
- RAG quality: `ragas`
- LLM-as-judge fallback: `qwen2.5:7b` via LiteLLM with a scoring prompt

## 3. Unit Tests

| Component | What to test |
|-----------|--------------|
| Chunker | fixed-size + overlap; edges (empty input, input < chunk size, unicode) |
| Embedding wrapper | correct dim, batching, error on empty input |
| Qdrant wrapper | collection create/delete idempotent, upsert, filter queries |
| LiteLLM wrapper | provider switch via env; retry on transient errors |
| PII scrubber | masks email / CPF / phone; preserves non-PII tokens |
| Config loader | required env vars raise early; defaults applied |

## 4. Integration Tests

| Scenario | Fixtures |
|----------|----------|
| Ingest → retrieve round-trip | Docker Qdrant + Ollama embed |
| Filter-based retrieval | Seeded collection with tagged docs |
| Agent tool call loop | Real Ollama LLM + in-memory retriever |
| PII not leaked to logs | Captured log stream + fixture with PII-laden docs |

## 5. Acceptance Tests (mapped to User Stories)

| Story | Test | Assertion |
|-------|------|-----------|
| US-A1 | `test_agent_answers_under_8s` | 20 runs; p95 latency < 8s; non-empty answer |
| US-A2 | `test_answer_includes_citations` | `response.sources` has ≥1 entry with `{doc_id, chunk_id}` |
| US-A3 | `test_refuses_when_no_relevant_docs` | off-topic query → refusal phrase; no fabricated claims |
| US-A4 | `test_response_language_is_ptbr` | `langdetect` returns `pt` on response |
| US-S1 | `test_ingest_makes_doc_retrievable` | ingest file → query distinct phrase from it → retrieved |
| US-S2 | `test_filter_narrows_retrieval` | filtered query only returns matching tags |
| US-S3 | `test_eval_produces_ragas_metrics` | run eval on mini gold set → metrics object has expected keys |
| US-S4 | `test_agent_run_emits_trace` | trace has retrieval span + llm span with timing |

## 6. RAG Evaluation

### 6.1 Gold set

- Location: `tests/eval/gold.jsonl`
- Row schema: `{question, expected_answer, expected_sources: [doc_id, ...], category}`
- Size target: 30–50 rows across all categories
- Curated manually (or via LLM with human review)

### 6.2 Metrics & thresholds

| Metric | Source | Threshold | Enforced |
|--------|--------|-----------|----------|
| Context Precision@5 | ragas | ≥ 0.80 (NFR-4) | Gate on PR |
| Faithfulness | ragas | ≥ 0.85 (NFR-5) | Gate on PR |
| Answer Relevancy | ragas | ≥ 0.75 | Tracked |
| Answer Correctness | ragas (LLM judge) | ≥ 0.70 | Tracked |

### 6.3 Running & reporting

- Command: `uv run opencall eval`
- Output: JSON + Markdown report → `eval_reports/<YYYY-MM-DD-HHMM>.md`
- Historical comparison: latest report diffed against last committed baseline

## 7. Non-Functional Validation

| NFR | How validated |
|-----|---------------|
| NFR-2 latency | Acceptance test `test_agent_answers_under_8s` (p95 over 20 runs) |
| NFR-6 observability | Acceptance test asserts trace has retrieval + llm spans |
| NFR-7 reproducibility | CI runs `uv sync --frozen` |
| NFR-8 portability | Integration test parameterized over `LLM_PROVIDER={ollama, openai}` (openai skipped if no key) |
| NFR-9 offline | CI job with network disabled post-setup |
| NFR-10 PII hygiene | Unit test for scrubber + integration test asserting log capture contains no raw PII |

## 8. CI Strategy (future)

GitHub Actions:
- `test` job: unit + integration (service containers: Qdrant, Ollama-small)
- `eval` job: RAG metrics, triggered by PR label `run-eval`
- Status badge in README
