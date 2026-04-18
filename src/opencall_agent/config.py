"""Application configuration, loaded from env vars with sane defaults.

Env vars use the `OPENCALL_` prefix. A local `.env` file is auto-loaded if present.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENCALL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_base_url: str = "http://localhost:11434"
    qdrant_url: str = "http://localhost:6333"

    llm_model: str = "ollama/qwen2.5:7b"
    embed_model: str = "ollama/nomic-embed-text"

    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    retrieval_top_k: int = Field(default=5, ge=1, le=50)
    retrieval_score_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


def get_settings() -> Settings:
    """Return a freshly loaded Settings instance.

    Not cached on purpose — tests may monkeypatch env vars between calls.
    """
    return Settings()
