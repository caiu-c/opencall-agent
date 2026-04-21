FROM ghcr.io/astral-sh/uv:0.5-python3.12-bookworm-slim AS build
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src ./src
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENCALL_QDRANT_URL=http://qdrant:6333 \
    OPENCALL_OLLAMA_BASE_URL=http://ollama:11434

COPY --from=build /opt/venv /opt/venv
COPY --from=build /app/src /app/src
COPY data ./data

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)" || exit 1

CMD ["python", "-m", "uvicorn", "opencall_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]
