from __future__ import annotations

import pytest
from pydantic import ValidationError

from opencall_agent.config import Settings, get_settings


def test_defaults_applied(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    # isolate from any local .env
    monkeypatch.chdir(tmp_path)
    for key in list(Settings.model_fields):
        monkeypatch.delenv(f"OPENCALL_{key.upper()}", raising=False)

    s = get_settings()
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.qdrant_url == "http://localhost:6333"
    assert s.llm_model == "ollama/qwen2.5:7b"
    assert s.embed_model == "ollama/nomic-embed-text"
    assert s.llm_temperature == 0.0
    assert s.retrieval_top_k == 5
    assert s.retrieval_score_threshold == 0.5


def test_env_overrides_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENCALL_LLM_MODEL", "anthropic/claude-sonnet-4-6")
    monkeypatch.setenv("OPENCALL_LLM_TEMPERATURE", "0.4")
    monkeypatch.setenv("OPENCALL_RETRIEVAL_TOP_K", "10")

    s = get_settings()
    assert s.llm_model == "anthropic/claude-sonnet-4-6"
    assert s.llm_temperature == 0.4
    assert s.retrieval_top_k == 10


def test_invalid_temperature_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENCALL_LLM_TEMPERATURE", "3.5")  # > 2.0 max

    with pytest.raises(ValidationError):
        get_settings()


def test_invalid_top_k_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENCALL_RETRIEVAL_TOP_K", "0")  # < 1 min

    with pytest.raises(ValidationError):
        get_settings()


def test_env_file_loaded(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    for key in list(Settings.model_fields):
        monkeypatch.delenv(f"OPENCALL_{key.upper()}", raising=False)
    (tmp_path / ".env").write_text(
        "OPENCALL_QDRANT_URL=http://qdrant.local:7000\n"
        "OPENCALL_RETRIEVAL_TOP_K=7\n"
    )
    monkeypatch.chdir(tmp_path)

    s = get_settings()
    assert s.qdrant_url == "http://qdrant.local:7000"
    assert s.retrieval_top_k == 7
