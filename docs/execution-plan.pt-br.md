# opencall-agent — Plano de Execução

> Espelho em PT-BR. Versão canônica (EN): [execution-plan.md](./execution-plan.md). Derivado de [requirements.pt-br.md](./requirements.pt-br.md) e [test-plan.pt-br.md](./test-plan.pt-br.md).

## Princípios

- Cada milestone é um PR mergeável.
- Cada milestone tem **Definition of Done** citando user stories e testes.
- Ordem é sugestiva, não rígida — bloqueios podem reorganizar.
- Decisões arquiteturais em `docs/adr/` (introduzido em M5).

## Milestones

### M0 — Scaffold e validação de stack ✅ concluído
- Repo, deps, Qdrant em Docker, modelos Ollama, smoke test.
- **DoD:** `uv run main.py` passa fim-a-fim.

### M1 — Estrutura do projeto e configuração
**Objetivo:** sair do `main.py` flat para pacote `src/opencall_agent/` + camada de config.
- Reestruturar: `src/opencall_agent/{config, llm, vector, ingestion, agent}`
- `pydantic-settings` para config via env
- `.env.example` commitado
- Testes unitários para carregamento de config
- **DoD:** `uv run pytest` verde; smoke test ainda passa via entrypoint do pacote.

### M2 — Ingestão de documentos (US-S1)
**Objetivo:** ingerir PDF/TXT/MD em Qdrant com metadados.
- `ingestion.load` por formato (começar com TXT + MD; PDF via `pypdf`)
- `ingestion.chunk` (consciente de frase + overlap)
- `ingestion.embed` (LiteLLM → Ollama)
- `ingestion.index` (Qdrant upsert com payload: source, date, category)
- CLI: `uv run opencall ingest <path> --category <cat>`
- Unit: chunker; Integração: round-trip
- **DoD:** teste de aceitação US-S1 passa; corpus TXT de amostra ingerido.

### M3 — Dados do domínio e gold set
**Objetivo:** popular base de conhecimento realista (destrava qualidade de retrieval).
- Resolver perguntas em aberto: domínio âncora, fonte de dados, taxonomia de filtros
- Gerar/curar ~20 políticas, ~10 FAQs, ~10 transcrições mock em `data/samples/`
- Ingerir via pipeline do M2
- Gold set: 30 pares Q&A em `tests/eval/gold.jsonl`
- **DoD:** dados e gold set no repo; ingestão reprodutível do zero.

### M4 — RAG básico (US-A1..A4)
**Objetivo:** Q&A via CLI: pergunta → retrieve top-k → resposta com citações.
- `vector.retrieve(query, k=5, filter=None)`
- `agent.rag_chain`: retrieve simples → stuff-prompt → LLM
- Pós-processamento de citação (chunks → refs de fonte)
- Caminho de recusa quando top score < threshold
- CLI: `uv run opencall ask "<q>"`
- **DoD:** testes de aceitação US-A1..A4 passam.

### M5 — Agente LangGraph
**Objetivo:** substituir chain direta por agente LangGraph com `retrieve` como tool.
- `AgentState` (messages, tool calls, sources)
- Nós: `llm`, `retrieve_tool`, `synthesize`
- Edges condicionais no loop de tool
- Agente substitui `rag_chain` na CLI (mesma interface)
- Primeiro ADR: `docs/adr/001-langgraph-over-chain.md`
- **DoD:** testes de aceitação do M4 continuam passando via agente; trace mostra invocação de tool.

### M6 — Filtros de metadados (US-S2)
**Objetivo:** expor filtros ao agente.
- Argumento `filter` na tool de retrieve
- Prompt do agente ensina quando aplicar filtros
- CLI: `uv run opencall ask "<q>" --filter category=politica`
- **DoD:** teste de aceitação US-S2 passa.

### M7 — Harness de avaliação (US-S3)
**Objetivo:** medição de qualidade reprodutível.
- Módulo `eval`: roda gold set pelo agente → coleta (q, a, contextos, esperado)
- Integração ragas: context_precision, faithfulness, answer_relevancy, answer_correctness
- Relatório JSON + Markdown → `eval_reports/`
- CLI: `uv run opencall eval`
- Thresholds de NFR-4, NFR-5 enforçados
- **DoD:** teste de aceitação US-S3 passa; baseline commitado.

### M8 — Observabilidade (US-S4)
**Objetivo:** traces para cada run do agente.
- ADR decide: OpenTelemetry console + container Langfuse opcional
- Span por nó, propagação de contexto
- PII scrubber na camada de logging (NFR-10)
- **DoD:** teste de aceitação US-S4 passa; trace de exemplo com screenshot nos docs.

### M9 — API HTTP
**Objetivo:** expor o agente via FastAPI.
- `POST /ask` → `{ answer, sources, trace_id }`
- `POST /ingest` para supervisores
- OpenAPI auto-gerada
- CLI: `uv run opencall serve`
- **DoD:** teste de integração bate na API fim-a-fim.

### M10 — Deploy
**Objetivo:** subida com um comando.
- `docker-compose.yml`: `api` + `qdrant` (+ `ollama` opcional)
- `Dockerfile` multi-stage (baseado em uv)
- README atualizado com passos de deploy
- **DoD:** `docker compose up` + query smoke funciona.

### M11 — Retrieval de duas pistas
**Objetivo:** cumprir o compromisso original de `transcricao = referência de
tom` (`requirements.md` §7) — transcrições influenciam *como* o agente fala,
nunca *o que* ele cita.
- Retrieval factual exclui `category=transcricao`; retrieval estilístico
  (top-K controlado por `OPENCALL_STYLE_TOP_K`) injeta trechos de transcrição
  somente no system prompt.
- Harness de avaliação força `style_top_k=0` para o gold medir apenas
  retrieval factual.
- Gold set limpo: linhas que exigiam `transcricao_*.txt` em `must_cite`
  re-rotuladas contra as fontes de política/faq correspondentes.
- **DoD:** aceite `test_us_s5_two_track` passa; recall do eval ≥ baseline.

## Futuro (pós-MVP)

- Bot de auto-atendimento ao cliente final
- I/O de voz
- Multi-tenancy
- Fine-tuning de modelo pequeno em transcrições
- CI via GitHub Actions
- Integração externa OpenCall (webhook/mock REST)
