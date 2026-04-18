"""Thin wrappers over LiteLLM for completion and embedding calls."""

from __future__ import annotations

import litellm

from .config import Settings


def complete(settings: Settings, messages: list[dict[str, str]]) -> str:
    resp = litellm.completion(
        model=settings.llm_model,
        api_base=settings.ollama_base_url,
        temperature=settings.llm_temperature,
        messages=messages,
    )
    return resp.choices[0].message.content.strip()


def embed(settings: Settings, texts: list[str]) -> list[list[float]]:
    resp = litellm.embedding(
        model=settings.embed_model,
        api_base=settings.ollama_base_url,
        input=texts,
    )
    return [item["embedding"] for item in resp.data]
