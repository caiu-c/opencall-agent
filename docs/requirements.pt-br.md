# opencall-agent — Requisitos

> Espelho em PT-BR. Versão canônica (EN): [requirements.md](./requirements.md).

## 1. Visão

Construir um assistente de RAG agêntico para operadores de call center, demonstrando uma arquitetura production-grade (ingestão, retrieval, orquestração agêntica, avaliação, observabilidade, deploy) em stack local-first.

## 2. Personas

- **Atendente** — operador de linha de frente em chamadas ao vivo. **Usuário primário.**
- **Supervisor** — gerencia base de conhecimento, audita respostas, revisa métricas de qualidade. **Usuário secundário.**
- **Cliente Final** — *fora de escopo no MVP*; registrado como roadmap futuro.

## 3. Requisitos Funcionais (User Stories)

### 3.1 Atendente — consumo de conhecimento

**US-A1** — Como Atendente, quero fazer perguntas em linguagem natural sobre políticas e procedimentos da empresa, para responder ao cliente sem colocá-lo em espera.
- **Dado** uma pergunta em PT-BR e uma base de conhecimento populada,
- **Quando** submeto a pergunta,
- **Então** o sistema retorna uma resposta fundamentada em documentos recuperados com p95 < 8s.

**US-A2** — Como Atendente, quero que cada resposta inclua citações (documento-fonte + seção/chunk), para verificar a afirmação e construir confiança.
- **Dado** que o sistema retornou uma resposta,
- **Quando** inspeciono a resposta,
- **Então** pelo menos uma referência de fonte (id do doc + localizador do chunk) está presente.

**US-A3** — Como Atendente, quero que o assistente diga explicitamente "não sei" quando a base de conhecimento não tem a resposta, para não repassar informação inventada ao cliente.
- **Dado** uma pergunta sem documentos relevantes (score de retrieval abaixo do threshold),
- **Quando** o sistema processa,
- **Então** a resposta declara a ausência e não contém fatos fabricados.

**US-A4** — Como Atendente, quero respostas em PT-BR no idioma da chamada, para repassá-las diretamente.
- **Dado** qualquer pergunta em PT-BR,
- **Quando** o assistente responde,
- **Então** a resposta é em PT-BR e idiomática.

### 3.2 Supervisor — curadoria e qualidade

**US-S1** — Como Supervisor, quero ingerir documentos (PDF, TXT, MD, transcrições de chamadas) na base via CLI/API, para que atendentes tenham info atualizada.
- **Dado** um arquivo-fonte,
- **Quando** rodo a ingestão,
- **Então** o arquivo é chunked, embedded, armazenado em Qdrant com metadados (fonte, data, categoria), e fica acessível ao retrieval.

**US-S2** — Como Supervisor, quero taggear documentos com metadados (categoria, produto, região), para que o retrieval possa filtrar.
- **Dado** documentos taggeados e uma consulta filtrada,
- **Quando** o agente recupera,
- **Então** apenas documentos que batem com o filtro são considerados.

**US-S3** — Como Supervisor, quero rodar avaliação automatizada de qualidade contra um gold set, para detectar regressões.
- **Dado** um dataset-ouro de (pergunta, resposta_esperada, fontes_esperadas),
- **Quando** rodo `eval`,
- **Então** o sistema reporta faithfulness, answer relevancy, context precision (ragas) e sinaliza resultados abaixo dos thresholds.

**US-S4** — Como Supervisor, quero traces de cada decisão do agente (chamadas de retrieval, uso de tools, turns do LLM), para auditar comportamento.
- **Dado** que um agente respondeu uma pergunta,
- **Quando** inspeciono o trace,
- **Então** cada passo (inputs, outputs, latência, modelo, tokens) é observável.

## 4. Requisitos Não-Funcionais

| ID | Requisito | Threshold |
|----|-----------|-----------|
| NFR-1 | Idioma user-facing | PT-BR |
| NFR-2 | Latência fim-a-fim (pergunta → resposta) | p95 < 8s no `qwen2.5:7b` local |
| NFR-3 | Custo em dev | $0/mês (tudo local) |
| NFR-4 | Retrieval Context Precision@5 | ≥ 0,80 no eval set |
| NFR-5 | Faithfulness da resposta (ragas) | ≥ 0,85 |
| NFR-6 | Observabilidade | Cada passo do agente tem trace |
| NFR-7 | Reprodutibilidade | Deps pinadas (`uv.lock`); determinístico (`temperature=0`) em eval |
| NFR-8 | Portabilidade de provider | Troca de LLM por config só (LiteLLM) |
| NFR-9 | Dev offline | Stack completa roda sem internet após setup |
| NFR-10 | Higiene de PII | Logs mascaram email, CPF, telefone |

## 5. Restrições

- Python 3.12 + `uv`
- Stack travada: LangGraph + LiteLLM + Qdrant + Ollama (dev)
- Ambiente dev: WSL2 + Docker Desktop
- Mono-usuário (sem multi-tenancy)
- Sem API key cloud de LLM na fase dev

## 6. Fora de Escopo (MVP)

- I/O de voz (ASR/TTS)
- Transcrição de chamada em tempo real
- Bot de auto-atendimento ao cliente final
- Autenticação / autorização
- Multi-tenancy
- Fine-tuning de modelo
- Web UI (apenas CLI + HTTP API)

## 7. Decisões Tomadas

- **Domínio âncora**: **call center de farmácia**. Rico em conteúdo regulado (ANVISA), informação estruturada de produto (bulas, posologia, interações) e consultas comuns de alto impacto (refill, genérico, convênio).
- **Fonte de dados**: **dados públicos**. Base de conhecimento construída a partir de fontes públicas brasileiras — bulas da ANVISA (domínio público), BulaPaciente, FAQs públicos. Transcrições de chamadas são **sintetizadas por LLM** usando corpora públicos de customer support (ex.: [dataset Bitext](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset)) como referência estilística. Motivo: não existe corpus "transcrições de call center de farmácia" verdadeiramente público; o híbrido mantém a base autêntica e contorna o gap.
- **Taxonomia de filtros para US-S2** (conjunto inicial — extensível):
  - `politica` — políticas (trocas, entrega, genérico, convênio)
  - `produto` — info de produto/medicamento (bulas, posologia, interações, indicações)
  - `faq` — perguntas frequentes de clientes
  - `transcricao` — transcrições sintetizadas para few-shot / referência de tom
  - `regulatorio` — ANVISA / lei de prescrição / controlados
- **Integração OpenCall**: **adiada para pós-MVP**. Se necessária depois, implementar como webhook FastAPI que recebe um evento de chamada (chamador, tópico, trecho de transcrição) e retorna resposta sugerida. Não há contrato de API OpenCall real disponível — mock é suficiente para portfolio.
