# opencall-agent — Plano de Testes

> Espelho em PT-BR. Versão canônica (EN): [test-plan.md](./test-plan.md). Derivado de [requirements.pt-br.md](./requirements.pt-br.md).

## 1. Filosofia

Três camadas de execução + uma trilha de qualidade separada:

- **Unit** — rápidos, isolados, sem serviços externos. Em cada commit.
- **Integration** — Qdrant e Ollama reais. Em cada PR.
- **Acceptance** — nível de user story, fim-a-fim. Em cada PR.
- **RAG Eval** — métricas de qualidade, trackeadas ao longo do tempo; regressões acima do budget bloqueiam merge.

## 2. Ferramentas

- Test runner: `pytest` (+ `pytest-asyncio` para LangGraph)
- Serviços efêmeros (CI futura): `testcontainers`
- Qualidade RAG: `ragas`
- LLM-as-judge fallback: `qwen2.5:7b` via LiteLLM com prompt de scoring

## 3. Testes Unitários

| Componente | O que testar |
|------------|--------------|
| Chunker | tamanho fixo + overlap; bordas (entrada vazia, menor que chunk, unicode) |
| Wrapper de embedding | dim correta, batching, erro com input vazio |
| Wrapper do Qdrant | criação/deleção de collection idempotente, upsert, filtros |
| Wrapper LiteLLM | troca de provider via env; retry em erro transitório |
| PII scrubber | mascara email / CPF / telefone; preserva tokens não-PII |
| Loader de config | env vars obrigatórias falham cedo; defaults aplicados |

## 4. Testes de Integração

| Cenário | Fixtures |
|---------|----------|
| Round-trip ingestão → retrieval | Docker Qdrant + Ollama embed |
| Retrieval com filtro | Collection populada com docs taggeados |
| Loop de tool call do agente | LLM Ollama real + retriever em memória |
| PII não vaza em logs | Stream de log capturado + fixture com docs PII-ladeados |

## 5. Testes de Aceitação (mapeados às User Stories)

| Story | Teste | Assertiva |
|-------|-------|-----------|
| US-A1 | `test_agent_answers_under_8s` | 20 execuções; p95 de latência < 8s; resposta não-vazia |
| US-A2 | `test_answer_includes_citations` | `response.sources` tem ≥1 entrada `{doc_id, chunk_id}` |
| US-A3 | `test_refuses_when_no_relevant_docs` | pergunta off-topic → frase de recusa; zero fatos fabricados |
| US-A4 | `test_response_language_is_ptbr` | `langdetect` retorna `pt` para a resposta |
| US-S1 | `test_ingest_makes_doc_retrievable` | ingere arquivo → consulta com frase única dele → recupera |
| US-S2 | `test_filter_narrows_retrieval` | consulta filtrada só retorna tags compatíveis |
| US-S3 | `test_eval_produces_ragas_metrics` | roda eval com gold set pequeno → objeto de métricas com chaves esperadas |
| US-S4 | `test_agent_run_emits_trace` | trace tem span de retrieval + span de llm com timing |

## 6. Avaliação RAG

### 6.1 Gold set

- Local: `tests/eval/gold.jsonl`
- Schema por linha: `{question, expected_answer, expected_sources: [doc_id, ...], category}`
- Meta de tamanho: 30–50 linhas cobrindo todas as categorias
- Curadoria manual (ou LLM + revisão humana)

### 6.2 Métricas e thresholds

| Métrica | Fonte | Threshold | Gate |
|---------|-------|-----------|------|
| Context Precision@5 | ragas | ≥ 0,80 (NFR-4) | Bloqueia PR |
| Faithfulness | ragas | ≥ 0,85 (NFR-5) | Bloqueia PR |
| Answer Relevancy | ragas | ≥ 0,75 | Trackeada |
| Answer Correctness | ragas (LLM judge) | ≥ 0,70 | Trackeada |

### 6.3 Execução e relatório

- Comando: `uv run opencall eval`
- Saída: JSON + relatório Markdown → `eval_reports/<YYYY-MM-DD-HHMM>.md`
- Comparação histórica: relatório atual diffado contra último baseline commitado

## 7. Validação Não-Funcional

| NFR | Como validar |
|-----|--------------|
| NFR-2 latência | Acceptance `test_agent_answers_under_8s` (p95 em 20 runs) |
| NFR-6 observabilidade | Acceptance verifica trace com spans de retrieval + llm |
| NFR-7 reprodutibilidade | CI roda `uv sync --frozen` |
| NFR-8 portabilidade | Integração parametrizada em `LLM_PROVIDER={ollama, openai}` (openai skipado se sem key) |
| NFR-9 offline | Job de CI com rede desabilitada pós-setup |
| NFR-10 PII | Unit do scrubber + integração que captura log e verifica ausência de PII |

## 8. Estratégia de CI (futura)

GitHub Actions:
- Job `test`: unit + integração (service containers: Qdrant, Ollama pequeno)
- Job `eval`: métricas RAG, disparado por label de PR `run-eval`
- Badge de status no README
