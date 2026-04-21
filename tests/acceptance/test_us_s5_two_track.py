"""Two-track retrieval — transcripts feed tone, not citations.

Pins the architectural commitment from docs/requirements.md §7 and ADR 003:
`transcricao` chunks are synthesized dialog used to calibrate the agent's
register; they must never surface as citable evidence in a normal answer.
"""

from __future__ import annotations

import pytest

from opencall_agent.agent import answer
from opencall_agent.vector import make_client

pytestmark = pytest.mark.acceptance


def test_default_answer_never_cites_transcripts(settings, knowledge_collection) -> None:
    """Even for a question with matching transcript content, citations stay factual."""
    client = make_client(settings)
    # A transcripción sample covers this exact topic (transcricao_troca_medicamento.txt).
    resp = answer(
        settings,
        client,
        "Posso trocar um medicamento com embalagem danificada?",
        knowledge_collection,
    )

    assert not resp.refused
    assert resp.sources, "factual retrieval must still find citable matches"
    cited = {s.category for s in resp.sources}
    assert "transcricao" not in cited, (
        f"transcripts leaked into citable sources: {[s.source for s in resp.sources]}"
    )


def test_style_retrieval_does_not_gate_refusal(settings, knowledge_collection) -> None:
    """Off-topic question still refuses even if some transcript happens to embed near it."""
    from opencall_agent.agent import REFUSAL_PHRASE

    client = make_client(settings)
    resp = answer(
        settings,
        client,
        "Qual é o procedimento para lançar um foguete em órbita lunar?",
        knowledge_collection,
    )

    assert resp.refused
    assert resp.answer == REFUSAL_PHRASE
    assert resp.sources == []


def test_explicit_transcricao_filter_still_honored(settings, knowledge_collection) -> None:
    """Override escape hatch — explicit `category_filter='transcricao'` still works.

    Kept for CLI/API debugging so operators can inspect what a transcript
    retrieval would have returned; default path (no filter) excludes them.
    """
    client = make_client(settings)
    resp = answer(
        settings,
        client,
        "Troca de medicamento com embalagem amassada",
        knowledge_collection,
        category_filter="transcricao",
    )

    if not resp.refused:
        assert {s.category for s in resp.sources} == {"transcricao"}
