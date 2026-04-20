"""US-S3 — Eval harness produces a metrics object with the expected keys."""

from __future__ import annotations

from pathlib import Path

import pytest

from opencall_agent.eval import run_eval, write_reports
from opencall_agent.vector import make_client

pytestmark = pytest.mark.acceptance

GOLD = Path(__file__).resolve().parents[2] / "tests" / "eval" / "gold.jsonl"
REQUIRED_KEYS = {
    "n",
    "retrieval_recall_mean",
    "must_contain_coverage_mean",
    "latency_p50_s",
    "latency_p95_s",
    "refusal_false_negatives",
    "by_category",
}


def test_eval_produces_metrics(settings, knowledge_collection, tmp_path) -> None:
    result = run_eval(
        settings, make_client(settings), knowledge_collection, GOLD, max_rows=3
    )
    assert set(result.summary.keys()) >= REQUIRED_KEYS, (
        f"missing: {REQUIRED_KEYS - set(result.summary.keys())}"
    )
    assert result.summary["n"] == 3
    assert 0.0 <= result.summary["retrieval_recall_mean"] <= 1.0

    paths = write_reports(result, tmp_path, stem="smoke")
    assert paths["json"].exists() and paths["markdown"].exists()
    md = paths["markdown"].read_text(encoding="utf-8")
    assert "RAG evaluation report" in md
