"""Honest LLM token and API-cost reporting."""

from __future__ import annotations

from pathlib import Path


def write_token_cost_report(
    path: str | Path,
    *,
    shipment_rows: int,
    route_week_rows: int,
    retrieval_queries: int,
) -> Path:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = f"""# Token and Cost Report

## Full-run scope

- Shipment records processed: {shipment_rows:,}
- Route-week observations produced: {route_week_rows:,}
- Retrieval queries for anomalous rows: {retrieval_queries:,}

## AI usage

- Retrieval system: local scikit-learn TF-IDF with cosine similarity
- Explanation system: deterministic rule-based templates
- Generative LLM model: none
- LLM call count: 0
- LLM input tokens: 0
- LLM output tokens: 0
- Published model price: not applicable
- Estimated API cost: INR 0 / USD 0.00

No tokenizer estimate is presented as actual usage. TF-IDF does not consume LLM tokens,
and no paid or remote model was called. Numerical calculations, anomaly decisions,
evidence applicability, note IDs, verdicts, and explanations are deterministic.
"""
    report_path.write_text(report, encoding="utf-8", newline="\n")
    return report_path

