# Status — opencall-agent

_Updated 2026-04-20._

## Where we are

**MVP fechado.** Todos os 11 milestones do `docs/execution-plan.md` estão em `main`:

| M | Entrega | Commit |
|---|---|---|
| M0–M2 | Stack + package + ingestão | — |
| M3 | Corpus (20 polícias, 10 FAQs, 10 transcrições) + gold set (30 linhas) | — |
| M4–M5 | RAG chain → agente LangGraph | — |
| M6 | Filtros de metadado por categoria | — |
| M7 | Harness de avaliação + baseline | — |
| M8 | OpenTelemetry + PII scrubber | — |
| M9 | FastAPI (`/ask` · `/ingest` · `/healthz`) | `feeab06` |
| M10 | Docker compose (api + qdrant, ollama opt-in) + UI de chat em `GET /` | `9c29f66` |
| M11 | Retrieval de duas pistas (factual vs. tom) | `b722453` |

**Branches órfãs**: `origin/feat/m11-two-track-retrieval` ficou pendurada no remote (PR #12 foi auto-fechado quando a base stacked sumiu no merge de #11; recriei como #13). Pode deletar no GH — o conteúdo está em main via #13.

## Compromissos arquiteturais que NÃO podem regredir

1. **Transcrições = tom, nunca fonte.** `ADR 003` e `test_us_s5_two_track.py` pinam isso. Código crítico: `src/opencall_agent/agent/graph.py` → `_factual_filter` (`must_not category=transcricao`) e `_style_filter` (`must category=transcricao`). O prompt do sistema recebe os snippets como `(A), (B)` com instrução explícita "não cite". Se alguém mexer no retrieval, checar se essa invariante continua valendo.
2. **Eval mede retrieval factual puro.** `eval/harness.py` força `style_top_k=0` via `settings.model_copy` — não remover sem pensar: senão transcrições vazam phrasing e inflam `must_contain`.
3. **Refusal depende só do pass factual.** Se o score top factual < `retrieval_score_threshold` (default 0.72), recusa — independente do que o style pass retornou.

## Como subir e testar rápido

```bash
# Pré-req: Ollama no host em :11434 com qwen2.5:7b + nomic-embed-text
docker compose up --build -d
docker compose exec api python -m opencall_agent.cli ingest-dir data/samples --reset
```

- Chat UI: http://localhost:8000/
- Swagger: http://localhost:8000/docs
- Testes: `uv run pytest` (38 testes; unit + integration + acceptance)
- Eval: `uv run opencall eval --stem <rótulo>` → `eval_reports/<rótulo>.md`

**Baseline pra comparar mudanças de retrieval** (pós-M11, n=30 contra `acceptance_knowledge`):
- recall 28.3%, anchors 47.8%, p95 14.97s, refusal FN=0.

## Decisões em aberto

- **Fine-tuning em transcrições** (post-MVP). `ADR 003` já prevê: quando for a hora, migrar transcrições pra coleção Qdrant dedicada e aposentar o filtro compartilhado. Vira M12.
- **Integração OpenCall externa**. `requirements.md:104`: webhook FastAPI mockado. Baixo risco, bom pra fechar a "história" do portfolio. Vira M13.
- **CI (GitHub Actions)**. Precisa de Ollama no runner (caro) ou mock de LLM/embed pra unit+integration rodarem em pipeline. Fácil só pros unit; integration/acceptance precisam dependência viva. Provavelmente M14.
- **Voz (ASR/TTS) e self-service bot**. Salto grande de escopo; só depois dos anteriores.
- **`OPENCALL_STYLE_TOP_K` no README/env docs**. Checkbox ainda não marcada no PR #13. Pequeno débito.

## Próximos passos sugeridos (em ordem)

1. **M12 — Fine-tuning prep** _(baixo risco, alto valor para portfolio)_: migrar transcrições pra coleção `transcripts` dedicada; exportar o corpus em JSONL de pares `(pergunta_inferida, resposta_atendente)`. Gera material pro fine-tuning mesmo sem treinar agora.
2. **M13 — Webhook OpenCall mockado**: `POST /hooks/call-event` recebendo `{caller, topic, transcript_snippet}` → roda o agente → devolve resposta sugerida. Encerra a narrativa do requirements.md §7.
3. **M14 — CI mínimo**: GitHub Actions rodando só unit tests + lint (ruff/mypy se adotarem). Integration roda manual localmente. Pouco esforço, destrava PRs no portfolio.
4. **Documentar `OPENCALL_STYLE_TOP_K`** no README e em `docker-compose.yml` (env var exposta + comentário).

## Débitos menores

- `data/samples/faq_farmacia_popular.txt` — usuário abriu esse arquivo na última sessão; pode estar revisando conteúdo. Vale perguntar antes de assumir que tá final.
- `eval_reports/.gitignore` só libera `baseline.*`. Se quiser snapshotar pós-M11, adicionar exceção ou sobrescrever baseline (optativo).
- `rag_chain.py` é dead code desde M5 (ADR 001 previu isso). Ainda exporta `REFUSAL_PHRASE`, `RagResponse`, `SourceRef` usados por `graph.py`. Mover esses 3 símbolos pra `agent/__init__.py` e deletar `rag_chain.py` é trivial; não fiz pra manter M11 focado.
