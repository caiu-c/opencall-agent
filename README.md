# opencall-agent

Agentic RAG para domínio de call center (OpenCall). Projeto portfolio demonstrando arquitetura ponta-a-ponta: LLMs, RAG com vector DB, orquestração com grafos de estado, e deployment local.

## Stack

| Camada | Escolha | Por quê |
|---|---|---|
| Orquestração | [LangGraph](https://github.com/langchain-ai/langgraph) | State machines explícitas; mais "engenharia" que chain clássico |
| LLM abstraction | [LiteLLM](https://github.com/BerriAI/litellm) | Troca de provider (Ollama/OpenAI/Azure) sem refactor |
| LLM (dev) | Ollama `qwen2.5:7b` | Local, zero custo, bom em tool-calling |
| Embeddings | Ollama `nomic-embed-text` (768-dim) | Rápido, roda em CPU |
| Vector DB | [Qdrant](https://qdrant.tech) via Docker | Produção-ready, filtering rico |
| Runtime | Python 3.12 + [uv](https://github.com/astral-sh/uv) | Gerenciador moderno, lockfile determinístico |

## Pré-requisitos

- Docker (com integração WSL se Windows)
- [Ollama](https://ollama.com) (`curl -fsSL https://ollama.com/install.sh | sh`)
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Setup

```bash
# Modelos Ollama
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

# Qdrant
docker run -d --name opencall-qdrant -p 6333:6333 -p 6334:6334 \
  -v "$(pwd)/qdrant_data:/qdrant/storage" qdrant/qdrant

# Dependências Python
uv sync

# (opcional) configuração por env — defaults funcionam sem .env
cp .env.example .env

# Smoke test (LLM + embedding + Qdrant round-trip)
uv run opencall smoke

# Ingerir um documento na base de conhecimento
uv run opencall ingest data/samples/politica_trocas.txt --category politica

# Ingerir o corpus completo (categoria inferida pelo prefixo do nome)
uv run opencall ingest-dir data/samples --reset

# Perguntar à base de conhecimento
uv run opencall ask "Qual a validade da receita de antibiótico?"

# Subir API HTTP (FastAPI em 127.0.0.1:8000, com OpenAPI em /docs)
uv run opencall serve

# Testes (unit só por padrão; integration/acceptance rodam se serviços estiverem up)
uv run pytest
```

Especificação do projeto em [`docs/`](./docs/): requisitos, plano de testes e plano de execução (EN + PT-BR).

## Status

- [x] M0 — Stack validada via smoke test
- [x] M1 — Package scaffold + camada de config
- [x] M2 — Ingestão de documentos (TXT/MD → chunk → embed → Qdrant)
- [x] M3 — Corpus de amostra + gold set
- [x] M4 — Pipeline RAG básico (CLI ask)
- [x] M5 — Agente LangGraph
- [x] M6 — Filtros de metadados
- [x] M7 — Harness de avaliação
- [x] M8 — Observabilidade
- [x] M9 — API HTTP
- [ ] M10 — Deploy
