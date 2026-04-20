"""US-A1 — Answer within p95 < 8s, non-empty answer.

Test plan calls for 20 runs; kept tunable via OPENCALL_LATENCY_RUNS because
the target LLM is an Ollama-hosted local model whose throughput varies by
hardware. Default 5 runs is enough to catch obvious regressions; bump to 20
before signing off a release.
"""

from __future__ import annotations

import os
import time

import pytest

from opencall_agent.agent import answer
from opencall_agent.vector import make_client

pytestmark = pytest.mark.acceptance

P95_LATENCY_LIMIT_S = 8.0


def _p95(samples: list[float]) -> float:
    """Nearest-rank p95. Honest for small samples; matches test-plan intent
    without relying on statistics.quantiles interpolation quirks at low n."""
    ordered = sorted(samples)
    idx = max(0, min(len(ordered) - 1, int(0.95 * len(ordered))))
    return ordered[idx]


def test_agent_answers_under_8s(settings, knowledge_collection) -> None:
    runs = int(os.environ.get("OPENCALL_LATENCY_RUNS", "5"))
    client = make_client(settings)
    question = "Qual a validade da receita de antibiótico?"

    # Warm-up: amortize Ollama/Qdrant cold-start costs that otherwise
    # dominate a p95 computed over only 5 samples. Two iterations stabilize
    # when the model sat idle during upstream test setup.
    for _ in range(2):
        answer(settings, client, question, knowledge_collection)

    latencies: list[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        resp = answer(settings, client, question, knowledge_collection)
        latencies.append(time.perf_counter() - t0)
        assert resp.answer.strip(), "answer must be non-empty"

    p95 = _p95(latencies)
    assert p95 < P95_LATENCY_LIMIT_S, (
        f"p95 latency {p95:.2f}s exceeds {P95_LATENCY_LIMIT_S}s over {runs} runs"
    )
