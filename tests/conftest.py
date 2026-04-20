from __future__ import annotations

from urllib.error import URLError
from urllib.request import urlopen

import pytest

from opencall_agent.config import Settings, get_settings


def _reachable(url: str, timeout: float = 1.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except (URLError, OSError, ValueError):
        return False


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


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
