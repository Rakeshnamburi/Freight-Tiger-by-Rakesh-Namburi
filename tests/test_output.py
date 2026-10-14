from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd

from src.output_writer import write_output_csv
from src.validator import OUTPUT_COLUMNS, validate_output_csv


def _analysis() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "route": "B-C",
                "week_of": pd.Timestamp("2025-01-13"),
                "cost_per_tonne_km": 3.291,
                "vs_own_history_pct": 29.473,
                "vs_similar_routes_pct": 22.494,
                "is_anomaly": True,
                "matched_note_id": "N002",
                "reason": "Justified by note N002.",
            },
            {
                "route": "A-B",
                "week_of": pd.Timestamp("2025-01-06"),
                "cost_per_tonne_km": 2.0,
                "vs_own_history_pct": np.nan,
                "vs_similar_routes_pct": -2.0,
                "is_anomaly": False,
                "matched_note_id": "",
                "reason": "No anomaly decision.",
            },
        ]
    )


def test_exact_output_schema_format_and_sort(tmp_path: Path):
    path = write_output_csv(_analysis(), tmp_path / "output.csv")
    validate_output_csv(path, expected_rows=2)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, strict=True))
    assert list(rows[0]) == OUTPUT_COLUMNS
    assert rows[0]["route"] == "A-B"
    assert rows[0]["vs_own_history"] == ""
    assert rows[1]["cost_per_tonne_km"] == "3.29"
    assert rows[1]["vs_own_history"].startswith("+29.5%")
    assert rows[1]["flagged"] == "No (justified)"
    assert rows[1]["matched_note_id"] == "N002"


def test_output_bytes_are_deterministic(tmp_path: Path):
    first = write_output_csv(_analysis(), tmp_path / "first.csv")
    second = write_output_csv(_analysis(), tmp_path / "second.csv")
    assert first.read_bytes() == second.read_bytes()

