# opencall-agent

Agentic RAG para domínio de call center (OpenCall). Projeto portfolio demonstrando arquitetura ponta-a-ponta: LLMs, RAG com vector DB, orquestração com grafos de estado, e deployment local.

## Stack

| Camada | Escolha | Por quê |
|---|---|---|
| Orquestração | [LangGraph](https://github.com/langchain-ai/langgraph) | State machines explícitas; mais "engenharia" que chain clássico |
| LLM abstraction | [LiteLLM](https://github.com/BerriAI/litellm) | Troca de provider (Ollama/OpenAI/Anthropic) sem refactor |
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

# Smoke test (LLM + embedding + Qdrant round-trip)
uv run main.py
```

## Status

- [x] Stack validada via smoke test
- [ ] Ingestão de documentos (transcrições de chamadas)
- [ ] Pipeline RAG (chunk → embed → index → retrieve)
- [ ] Grafo LangGraph com agente + tool de retrieval
- [ ] Avaliação (ragas ou similar)
- [ ] Observabilidade (traces)
- [ ] Deployment
