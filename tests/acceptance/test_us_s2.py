"""US-S2 — Filtered retrieval narrows results to the requested category."""

from __future__ import annotations

import pytest

from opencall_agent.agent import answer
from opencall_agent.vector import make_client

pytestmark = pytest.mark.acceptance


def test_filter_narrows_retrieval(settings, knowledge_collection) -> None:
    client = make_client(settings)

    unfiltered = answer(
        settings, client, "Como descartar medicamento vencido?", knowledge_collection
    )
    filtered = answer(
        settings,
        client,
        "Como descartar medicamento vencido?",
        knowledge_collection,
        category_filter="politica",
    )

    assert not filtered.refused, "filtered query should still be answerable"
    assert filtered.sources, "filter must not wipe out sources on a matching query"

    assert {s.category for s in filtered.sources} == {"politica"}, (
        "filter must restrict sources to the requested category"
    )

    unfiltered_categories = {s.category for s in unfiltered.sources}
    assert len(unfiltered_categories) > 1 or "faq" in unfiltered_categories, (
        "baseline must span multiple categories to prove the filter mattered"
    )
