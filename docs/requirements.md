# opencall-agent — Requirements

> Canonical version (EN). Portuguese mirror: [requirements.pt-br.md](./requirements.pt-br.md).

## 1. Vision

Build an agentic RAG assistant for call center operators, demonstrating a production-grade architecture (ingestion, retrieval, agentic orchestration, evaluation, observability, deployment) on a local-first stack.

## 2. Personas

- **Agent (Atendente)** — frontline operator handling live calls. **Primary user.**
- **Supervisor** — manages the knowledge base, audits answers, reviews quality metrics. **Secondary user.**
- **End Customer** — *out of scope for MVP*; tracked as future roadmap.

## 3. Functional Requirements (User Stories)

### 3.1 Agent — knowledge consumption

**US-A1** — As an Agent, I want to ask natural-language questions about company policies and procedures, so that I can answer customer inquiries without putting them on hold.
- **Given** a question in PT-BR and a populated knowledge base,
- **When** I submit the question,
- **Then** the system returns an answer grounded in retrieved documents within p95 < 8s.

**US-A2** — As an Agent, I want each answer to include citations (source document + section/chunk), so that I can verify the claim and build trust.
- **Given** the system returns an answer,
- **When** I inspect the response,
- **Then** at least one source reference (document id + chunk locator) is present.

**US-A3** — As an Agent, I want the assistant to explicitly admit "I don't know" when the knowledge base lacks the answer, so that I don't relay fabricated info to a customer.
- **Given** a question with no relevant documents (retrieval score below threshold),
- **When** the system processes it,
- **Then** the response states the absence and contains no fabricated facts.

**US-A4** — As an Agent, I want responses in PT-BR matching the call language, so that I can relay them directly.
- **Given** any question in PT-BR,
- **When** the assistant responds,
- **Then** the response is in PT-BR and idiomatic.

### 3.2 Supervisor — knowledge curation & quality

**US-S1** — As a Supervisor, I want to ingest documents (PDF, TXT, MD, call transcripts) into the knowledge base via a CLI/API, so that agents get up-to-date info.
- **Given** a source file,
- **When** I run ingestion,
- **Then** the file is chunked, embedded, stored in Qdrant with metadata (source, date, category), and discoverable by retrieval.

**US-S2** — As a Supervisor, I want to tag documents with metadata (category, product, region), so that retrieval can be filtered.
- **Given** tagged documents and a filtered query,
- **When** the agent retrieves,
- **Then** only documents matching the filter are considered.

**US-S3** — As a Supervisor, I want to run automated quality evaluation against a gold set, so that I can detect regressions.
- **Given** a gold dataset of (question, expected_answer, expected_sources),
- **When** I run `eval`,
- **Then** the system reports faithfulness, answer relevancy, context precision (ragas) and flags results below thresholds.

**US-S4** — As a Supervisor, I want traces of each agent decision (retrieval calls, tool usage, LLM turns), so that I can audit behavior.
- **Given** an agent answers a question,
- **When** I inspect the trace,
- **Then** each step (inputs, outputs, timing, model, tokens) is observable.

## 4. Non-Functional Requirements

| ID | Requirement | Threshold |
|----|-------------|-----------|
| NFR-1 | User-facing language | PT-BR |
| NFR-2 | End-to-end latency (question → answer) | p95 < 8s on local `qwen2.5:7b` |
| NFR-3 | Cost in dev | $0/month (all local) |
| NFR-4 | Retrieval Context Precision@5 | ≥ 0.80 on eval set |
| NFR-5 | Answer faithfulness (ragas) | ≥ 0.85 |
| NFR-6 | Observability | Every agent step traced |
| NFR-7 | Reproducibility | Pinned deps (`uv.lock`); deterministic (`temperature=0`) in eval |
| NFR-8 | Provider portability | Switch LLM provider via config only (LiteLLM) |
| NFR-9 | Offline dev | Full stack runs without internet post-setup |
| NFR-10 | PII hygiene | Logs mask email, CPF, phone |

## 5. Constraints

- Python 3.12 + `uv`
- Stack locked: LangGraph + LiteLLM + Qdrant + Ollama (dev)
- Dev env: WSL2 + Docker Desktop
- Single-user (no multi-tenancy)
- No cloud LLM API key in dev phase

## 6. Out of Scope (MVP)

- Voice I/O (ASR/TTS)
- Real-time call transcription
- End-customer self-service bot
- Authentication / authorization
- Multi-tenancy
- Model fine-tuning
- Web UI (CLI + HTTP API only)

## 7. Resolved Decisions

- **Anchor domain**: **Pharmacy call center** (atendimento de farmácia). Rich in regulated content (ANVISA), structured product info (bulas, dosages, interactions), and common high-stakes queries (refills, substitutions, insurance coverage).
- **Data source**: **Public data**. Primary knowledge base built from public Brazilian pharmacy sources — ANVISA bulas (public domain), BulaPaciente, public pharmacy FAQs. Call transcripts are **synthesized by LLM** using public customer-support corpora (e.g., [Bitext customer-support dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset)) as stylistic reference. Rationale: no truly public "pharmacy call transcript" corpus exists; hybrid keeps knowledge base authentic while bypassing that gap.
- **Filter taxonomy for US-S2** (initial set — extensible):
  - `politica` — policies (returns, delivery, substitution, insurance)
  - `produto` — product/drug info (bulas, dosage, interactions, indications)
  - `faq` — frequent customer questions
  - `transcricao` — synthesized call transcripts for few-shot / tone reference
  - `regulatorio` — ANVISA / prescription law / controlled substances
- **OpenCall integration**: **deferred to post-MVP**. If later needed, implement as a FastAPI webhook that accepts a call event (caller, topic, transcript snippet) and returns a suggested answer. No real OpenCall API contract available — mock is sufficient for portfolio.
