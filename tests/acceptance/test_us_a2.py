"""US-A2 — Every answer carries at least one source reference."""

from __future__ import annotations

import pytest

from opencall_agent.agent import answer
from opencall_agent.vector import make_client

pytestmark = pytest.mark.acceptance


def test_answer_includes_citations(settings, knowledge_collection) -> None:
    client = make_client(settings)
    resp = answer(
        settings, client, "Onde descartar medicamento vencido?", knowledge_collection
    )

    assert not resp.refused, "this question should be answerable from the corpus"
    assert resp.sources, "response must carry at least one source"
    top = resp.sources[0]
    assert top.doc_id, "source must carry a doc_id"
    assert top.chunk_id, "source must carry a chunk_id"
    assert top.source, "source must carry a source path"
