"""Evaluation harness for the RAG agent against tests/eval/gold.jsonl."""

from .harness import EvalResult, RowResult, run_eval
from .metrics import aggregate, score_row
from .report import write_reports

__all__ = [
    "EvalResult",
    "RowResult",
    "aggregate",
    "run_eval",
    "score_row",
    "write_reports",
]
