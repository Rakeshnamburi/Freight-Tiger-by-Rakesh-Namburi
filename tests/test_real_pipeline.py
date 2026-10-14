from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.main import run_pipeline
from src.validator import validate_output_csv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_real_pipeline_counts_schema_and_spot_checks(tmp_path: Path):
    output = tmp_path / "freight_cost_analysis.csv"
    analysis, summary = run_pipeline(PROJECT_ROOT / "data", output)
    validate_output_csv(output, expected_rows=728)

    assert summary == {
        "shipment_records": 2940,
        "route_week_observations": 728,
        "anomalies": 19,
        "justified": 3,
        "unexplained": 16,
        "retrieval_queries": 19,
    }

    keyed = analysis.set_index(["route", "week_of"])
    delhi = keyed.loc[("Delhi-Jaipur", pd.Timestamp("2024-11-11"))]
    assert delhi["cost_per_tonne_km"] == pytest.approx(4.172957, abs=1e-6)
    assert delhi["vs_own_history_pct"] == pytest.approx(35.520091, abs=1e-6)
    assert delhi["vs_similar_routes_pct"] == pytest.approx(21.034360, abs=1e-6)
    assert delhi["matched_note_id"] == ""

    festival = keyed.loc[("Ahmedabad-Mumbai", pd.Timestamp("2025-01-20"))]
    assert festival["cost_per_tonne_km"] == pytest.approx(3.290367, abs=1e-6)
    assert festival["matched_note_id"] == "N002"

    sample_peer = keyed.loc[("Mumbai-Pune", pd.Timestamp("2025-09-15"))]
    assert sample_peer["cost_per_tonne_km"] == pytest.approx(3.980810, abs=1e-6)
    assert sample_peer["vs_own_history_pct"] == pytest.approx(9.249687, abs=1e-6)
    assert sample_peer["vs_similar_routes_pct"] == pytest.approx(23.625216, abs=1e-6)


def test_independent_weighted_cost_spot_check(tmp_path: Path):
    analysis, _ = run_pipeline(PROJECT_ROOT / "data", tmp_path / "out.csv")
    source = pd.read_csv(PROJECT_ROOT / "data" / "shipment_records.csv")
    source["shipment_date"] = pd.to_datetime(source["shipment_date"])
    mask = (
        source["origin"].eq("Mumbai")
        & source["destination"].eq("Pune")
        & source["shipment_date"].between("2024-01-01", "2024-01-07")
    )
    selected = source.loc[mask]
    expected = selected["freight_cost_inr"].sum() / (
        selected["quantity_tonnes"] * selected["distance_km"]
    ).sum()
    actual = analysis.set_index(["route", "week_of"]).loc[
        ("Mumbai-Pune", pd.Timestamp("2024-01-01")), "cost_per_tonne_km"
    ]
    assert actual == pytest.approx(expected, rel=0, abs=1e-12)

