"""Emit JSON + Markdown reports from an EvalResult."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .harness import EvalResult


def _fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _fmt_s(v: float) -> str:
    return f"{v:.2f}s"


def to_markdown(result: EvalResult, *, title: str = "RAG evaluation report") -> str:
    s = result.summary
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    lines.append(f"- Rows evaluated: {s.get('n', 0)}")
    lines.append(
        f"- Retrieval recall (must_cite ∩ retrieved): {_fmt_pct(s.get('retrieval_recall_mean', 0.0))}"
    )
    lines.append(
        f"- Anchor coverage (must_contain): {_fmt_pct(s.get('must_contain_coverage_mean', 0.0))}"
    )
    lines.append(f"- Latency p50 / p95: {_fmt_s(s.get('latency_p50_s', 0.0))} / {_fmt_s(s.get('latency_p95_s', 0.0))}")
    lines.append(f"- Refusal false-negatives: {s.get('refusal_false_negatives', 0)}")
    lines.append("")
    lines.append("## By category")
    lines.append("")
    lines.append("| Category | N | Recall | Anchors |")
    lines.append("|----------|---|--------|---------|")
    for cat, stats in s.get("by_category", {}).items():
        lines.append(
            f"| {cat} | {stats['n']} | {_fmt_pct(stats['retrieval_recall_mean'])} "
            f"| {_fmt_pct(stats['must_contain_coverage_mean'])} |"
        )
    lines.append("")
    lines.append("## Per-row")
    lines.append("")
    lines.append("| id | cat | recall | anchors | latency |")
    lines.append("|----|-----|--------|---------|---------|")
    for row in result.rows:
        score = row.score
        lines.append(
            f"| {score.id} | {score.category} | {_fmt_pct(score.retrieval_recall)} "
            f"| {_fmt_pct(score.must_contain_coverage)} | {_fmt_s(score.latency_s)} |"
        )
    return "\n".join(lines) + "\n"


def _serialize(result: EvalResult) -> dict:
    return {
        "summary": result.summary,
        "rows": [
            {
                "id": r.score.id,
                "category": r.score.category,
                "question": r.gold.get("question"),
                "answer": r.answer,
                "sources": [{"source": s.source, "score": s.score} for s in r.sources],
                "refused": r.refused,
                "retrieval_scores": r.retrieval_scores,
                "latency_s": r.latency_s,
                "metrics": asdict(r.score),
            }
            for r in result.rows
        ],
    }


def write_reports(result: EvalResult, out_dir: Path, *, stem: str | None = None) -> dict[str, Path]:
    """Write JSON and Markdown reports; return their paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    stem = stem or ts
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(
        json.dumps(_serialize(result), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path.write_text(to_markdown(result), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}
