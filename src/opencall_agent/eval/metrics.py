"""Pure-function metrics over a single (gold_row, rag_response, latency) triple."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean


@dataclass(frozen=True)
class RowScore:
    id: str
    category: str
    refused_expected: bool
    refused_actual: bool
    retrieval_recall: float  # must_cite ∩ retrieved / len(must_cite)
    must_contain_coverage: float
    latency_s: float
    answer: str


def _basenames(paths: list[str]) -> set[str]:
    return {Path(p).name for p in paths}


def score_row(gold_row: dict, sources: list, answer: str, latency_s: float) -> RowScore:
    """Score a single row. `sources` are RagResponse.sources; `answer` is the text."""
    must_cite = gold_row.get("must_cite", [])
    must_contain = gold_row.get("must_contain", [])

    retrieved_names = _basenames([s.source for s in sources])
    must_cite_names = _basenames(must_cite)
    recall = (
        len(must_cite_names & retrieved_names) / len(must_cite_names)
        if must_cite_names
        else 1.0
    )

    if must_contain:
        haystack = answer.lower()
        coverage = mean(1.0 if needle.lower() in haystack else 0.0 for needle in must_contain)
    else:
        coverage = 1.0

    refused_actual = not sources and not answer.strip().lower().startswith("a ") and (
        "não encontrei" in answer.lower()
        or "recomendo consultar" in answer.lower()
    )
    refused_expected = bool(gold_row.get("refusal_expected", False))

    return RowScore(
        id=gold_row["id"],
        category=gold_row.get("category", ""),
        refused_expected=refused_expected,
        refused_actual=refused_actual,
        retrieval_recall=recall,
        must_contain_coverage=coverage,
        latency_s=latency_s,
        answer=answer,
    )


def _p(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(pct * len(ordered))))
    return ordered[idx]


def aggregate(rows: list[RowScore]) -> dict:
    if not rows:
        return {
            "n": 0,
            "retrieval_recall_mean": 0.0,
            "must_contain_coverage_mean": 0.0,
            "latency_p50_s": 0.0,
            "latency_p95_s": 0.0,
            "refusal_false_negatives": 0,
            "by_category": {},
        }
    by_cat: dict[str, list[RowScore]] = {}
    for row in rows:
        by_cat.setdefault(row.category or "uncategorized", []).append(row)
    latencies = [r.latency_s for r in rows]
    return {
        "n": len(rows),
        "retrieval_recall_mean": mean(r.retrieval_recall for r in rows),
        "must_contain_coverage_mean": mean(r.must_contain_coverage for r in rows),
        "latency_p50_s": _p(latencies, 0.50),
        "latency_p95_s": _p(latencies, 0.95),
        "refusal_false_negatives": sum(
            1 for r in rows if r.refused_expected and not r.refused_actual
        ),
        "by_category": {
            cat: {
                "n": len(subset),
                "retrieval_recall_mean": mean(r.retrieval_recall for r in subset),
                "must_contain_coverage_mean": mean(r.must_contain_coverage for r in subset),
            }
            for cat, subset in sorted(by_cat.items())
        },
    }
