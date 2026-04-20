"""US-A3 — Refuses when no relevant documents, no fabricated claims."""

from __future__ import annotations

import pytest

from opencall_agent.agent import REFUSAL_PHRASE, answer
from opencall_agent.vector import make_client

pytestmark = pytest.mark.acceptance


def test_refuses_when_no_relevant_docs(settings, knowledge_collection) -> None:
    client = make_client(settings)
    resp = answer(
        settings,
        client,
        "Qual é o procedimento para lançar um foguete em órbita lunar?",
        knowledge_collection,
    )

    assert resp.refused, "off-topic question must trigger refusal"
    assert resp.answer == REFUSAL_PHRASE
    assert resp.sources == []
