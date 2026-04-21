from __future__ import annotations

from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from opencall_agent.config import Settings, get_settings
from opencall_agent.ingestion.indexer import ingest_document
from opencall_agent.vector import make_client

ACCEPTANCE_COLLECTION = "acceptance_knowledge"
SAMPLES_DIR = Path(__file__).resolve().parents[1] / "data" / "samples"

_CATEGORY_BY_PREFIX = {
    "politica": "politica",
    "faq": "faq",
    "transcricao": "transcricao",
    "produto": "produto",
    "regulatorio": "regulatorio",
}


def _reachable(url: str, timeout: float = 1.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except (URLError, OSError, ValueError):
        return False


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def knowledge_collection(settings: Settings) -> str:
    """Ingest the sample corpus once per session into an isolated collection.

    Also primes the LLM with a single throwaway call; without it, the first
    acceptance test to invoke the agent absorbs Ollama's cold-start and
    skews the US-A1 latency budget.
    """
    from opencall_agent.agent import answer as rag_answer

    client = make_client(settings)
    if client.collection_exists(ACCEPTANCE_COLLECTION):
        client.delete_collection(ACCEPTANCE_COLLECTION)
    for path in sorted(SAMPLES_DIR.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".txt", ".md"}:
            continue
        category = _CATEGORY_BY_PREFIX.get(path.name.split("_", 1)[0].lower())
        if category is None:
            continue
        ingest_document(settings, client, path, category=category, collection=ACCEPTANCE_COLLECTION)

    rag_answer(settings, client, "aquecimento", ACCEPTANCE_COLLECTION)
    return ACCEPTANCE_COLLECTION


def _services_up(settings: Settings) -> tuple[bool, bool]:
    qd = _reachable(f"{settings.qdrant_url}/")
    ol = _reachable(f"{settings.ollama_base_url}/api/tags")
    return qd, ol


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    settings = get_settings()
    qd, ol = _services_up(settings)
    missing: list[str] = []
    if not qd:
        missing.append("Qdrant")
    if not ol:
        missing.append("Ollama")
    if not missing:
        return

    reason = f"skipped: services not reachable ({', '.join(missing)})"
    skip_marker = pytest.mark.skip(reason=reason)
    for item in items:
        if "integration" in item.keywords or "acceptance" in item.keywords:
            item.add_marker(skip_marker)
