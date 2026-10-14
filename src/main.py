"""Command-line entry point for the Freight Tiger analysis pipeline."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from .anomaly_detector import AnomalyConfig, detect_anomalies
from .context_retriever import ContextRetriever
from .cost_tracker import write_token_cost_report
from .data_loader import load_context_notes, load_shipments
from .evidence_validator import select_valid_evidence
from .explanation_generator import generate_explanation
from .historical_baseline import add_historical_baseline
from .output_writer import write_output_csv
from .peer_comparison import add_peer_baseline
from .weekly_aggregator import aggregate_weekly_costs


LOGGER = logging.getLogger("freight_tiger")


def run_pipeline(
    data_dir: str | Path,
    output_path: str | Path,
    *,
    config: AnomalyConfig | None = None,
    reports_dir: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    config = config or AnomalyConfig()
    data_path = Path(data_dir)
    shipments = load_shipments(data_path / "shipment_records.csv")
    notes = load_context_notes(data_path / "context_notes.csv")

    analysis = aggregate_weekly_costs(shipments)
    analysis = add_historical_baseline(analysis, window=8)
    analysis = add_peer_baseline(analysis)
    analysis = detect_anomalies(analysis, config=config)

    retriever = ContextRetriever(notes)
    matched_note_ids: list[str] = []
    reasons: list[str] = []
    retrieval_queries = 0
    for _, observation in analysis.iterrows():
        match = None
        if bool(observation["is_anomaly"]):
            retrieval_queries += 1
            candidates = retriever.retrieve(observation, top_k=5)
            match = select_valid_evidence(observation, candidates)
        matched_note_ids.append(match.note_id if match else "")
        reasons.append(generate_explanation(observation, match, config))

    analysis["matched_note_id"] = matched_note_ids
    analysis["reason"] = reasons
    write_output_csv(analysis, output_path)

    summary = {
        "shipment_records": int(len(shipments)),
        "route_week_observations": int(len(analysis)),
        "anomalies": int(analysis["is_anomaly"].sum()),
        "justified": int(
            (analysis["is_anomaly"] & analysis["matched_note_id"].ne("")).sum()
        ),
        "unexplained": int(
            (analysis["is_anomaly"] & analysis["matched_note_id"].eq("")).sum()
        ),
        "retrieval_queries": retrieval_queries,
    }

    if reports_dir is not None:
        report_path = Path(reports_dir)
        report_path.mkdir(parents=True, exist_ok=True)
        write_token_cost_report(
            report_path / "token_cost_report.md",
            shipment_rows=len(shipments),
            route_week_rows=len(analysis),
            retrieval_queries=retrieval_queries,
        )
        (report_path / "run_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    return analysis, summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze weekly route costs and produce the Freight Tiger CSV."
    )
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output", default="output/freight_cost_analysis.csv")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--history-threshold", type=float, default=20.0)
    parser.add_argument("--peer-threshold", type=float, default=20.0)
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args()
    config = AnomalyConfig(
        history_threshold_pct=args.history_threshold,
        peer_threshold_pct=args.peer_threshold,
    )
    _, summary = run_pipeline(
        args.data_dir,
        args.output,
        config=config,
        reports_dir=args.reports_dir,
    )
    LOGGER.info("Pipeline complete: %s", json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

