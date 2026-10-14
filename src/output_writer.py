"""Standards-compliant writer for the exact submission CSV contract."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from .validator import OUTPUT_COLUMNS, validate_output_csv


def _format_comparison(value: float, description: str) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):+.1f}% {description}"


def build_output_rows(analysis: pd.DataFrame) -> list[dict[str, str]]:
    ordered = analysis.sort_values(["route", "week_of"], kind="mergesort")
    rows: list[dict[str, str]] = []
    for _, row in ordered.iterrows():
        is_anomaly = bool(row["is_anomaly"])
        note_id = str(row.get("matched_note_id", "") or "") if is_anomaly else ""
        if is_anomaly and note_id:
            flag = "No (justified)"
        elif is_anomaly:
            flag = "Yes"
        else:
            flag = "No"

        rows.append(
            {
                "route": str(row["route"]),
                "week_of": pd.Timestamp(row["week_of"]).strftime("%Y-%m-%d"),
                "cost_per_tonne_km": f"{float(row['cost_per_tonne_km']):.2f}",
                "vs_own_history": _format_comparison(
                    row["vs_own_history_pct"], "vs this route's past average"
                ),
                "vs_similar_routes": _format_comparison(
                    row["vs_similar_routes_pct"],
                    "vs similar-length routes this week",
                ),
                "flagged": flag,
                "matched_note_id": note_id,
                "reason": str(row["reason"]),
            }
        )
    return rows


def write_output_csv(analysis: pd.DataFrame, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_output_rows(analysis)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=OUTPUT_COLUMNS,
            extrasaction="raise",
            lineterminator="\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)
    validate_output_csv(output_path, expected_rows=len(rows))
    return output_path

