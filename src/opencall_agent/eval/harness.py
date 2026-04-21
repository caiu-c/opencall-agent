"""Run the agent over gold.jsonl and collect per-row results."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from qdrant_client import QdrantClient

from ..agent import answer
from ..config import Settings
from .metrics import RowScore, aggregate, score_row


@dataclass(frozen=True)
class RowResult:
    gold: dict
    answer: str
    sources: list
    refused: bool
    retrieval_scores: list[float]
    latency_s: float
    score: RowScore


@dataclass(frozen=True)
class EvalResult:
    rows: list[RowResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def load_gold(gold_path: Path, max_rows: int | None = None) -> list[dict]:
    rows: list[dict] = []
    with gold_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if max_rows is not None and len(rows) >= max_rows:
                break
    return rows


def run_eval(
    settings: Settings,
    client: QdrantClient,
    collection: str,
    gold_path: Path,
    max_rows: int | None = None,
) -> EvalResult:
    # Style retrieval is disabled during eval: the gold set scores retrieval
    # purely on factual `must_cite` hits, so letting transcript snippets leak
    # phrasing into the answer would inflate `must_contain` coverage without
    # proving the citable retrieval worked.
    settings = settings.model_copy(update={"style_top_k": 0})
    rows: list[RowResult] = []
    for gold in load_gold(gold_path, max_rows=max_rows):
        t0 = time.perf_counter()
        resp = answer(settings, client, gold["question"], collection)
        latency = time.perf_counter() - t0
        score = score_row(gold, resp.sources, resp.answer, latency)
        rows.append(
            RowResult(
                gold=gold,
                answer=resp.answer,
                sources=resp.sources,
                refused=resp.refused,
                retrieval_scores=resp.retrieval_scores,
                latency_s=latency,
                score=score,
            )
        )
    return EvalResult(rows=rows, summary=aggregate([r.score for r in rows]))
