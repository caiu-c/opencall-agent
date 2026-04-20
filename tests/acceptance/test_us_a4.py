"""US-A4 — Response language is PT-BR."""

from __future__ import annotations

import pytest

from opencall_agent.agent import answer
from opencall_agent.vector import make_client

pytestmark = pytest.mark.acceptance


def test_response_language_is_ptbr(settings, knowledge_collection) -> None:
    pytest.importorskip("langdetect")
    from langdetect import DetectorFactory, detect

    DetectorFactory.seed = 0

    client = make_client(settings)
    resp = answer(
        settings,
        client,
        "O que é intercambialidade de medicamentos?",
        knowledge_collection,
    )

    assert not resp.refused
    detected = detect(resp.answer)
    assert detected == "pt", f"expected pt, got {detected}: {resp.answer!r}"
