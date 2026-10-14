from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.historical_baseline import add_historical_baseline
from src.peer_comparison import add_peer_baseline
from src.validator import validate_shipments
from src.weekly_aggregator import aggregate_weekly_costs


def test_monday_grouping_and_weighted_cost(valid_shipments):
    shipments = validate_shipments(valid_shipments)
    weekly = aggregate_weekly_costs(shipments)
    assert len(weekly) == 1
    assert weekly.loc[0, "week_of"] == pd.Timestamp("2025-01-06")
    # (2000 + 6000) / (10*100 + 20*100), not the mean of row-level rates.
    assert weekly.loc[0, "cost_per_tonne_km"] == pytest.approx(8_000 / 3_000)


def _weekly_values(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "origin": "A",
            "destination": "B",
            "route_type": "Short",
            "route": "A-B",
            "week_of": pd.date_range("2025-01-06", periods=len(values), freq="7D"),
            "cost_per_tonne_km": values,
        }
    )


def test_history_uses_previous_eight_observations_only():
    result = add_historical_baseline(_weekly_values(list(range(1, 11))), window=8)
    assert np.isnan(result.loc[0, "historical_baseline"])
    assert result.loc[1, "historical_baseline"] == pytest.approx(1.0)
    # For current value 10, the prior eight available observations are 2..9.
    assert result.loc[9, "historical_baseline"] == pytest.approx(5.5)
    assert result.loc[9, "history_observations"] == 8


def test_history_has_no_lookahead_leakage():
    original = add_historical_baseline(_weekly_values([1.0, 2.0, 3.0, 4.0]))
    changed_future = add_historical_baseline(_weekly_values([1.0, 2.0, 3.0, 4000.0]))
    assert original.loc[2, "historical_baseline"] == changed_future.loc[
        2, "historical_baseline"
    ]
    assert original.loc[3, "historical_baseline"] == changed_future.loc[
        3, "historical_baseline"
    ]


def test_peer_average_excludes_self_and_other_route_types():
    week = pd.Timestamp("2025-01-06")
    frame = pd.DataFrame(
        {
            "origin": ["A", "C", "E", "G"],
            "destination": ["B", "D", "F", "H"],
            "route_type": ["Short", "Short", "Short", "Long"],
            "route": ["A-B", "C-D", "E-F", "G-H"],
            "week_of": [week] * 4,
            "cost_per_tonne_km": [1.0, 3.0, 5.0, 100.0],
        }
    )
    result = add_peer_baseline(frame).set_index("route")
    assert result.loc["A-B", "peer_baseline"] == pytest.approx(4.0)
    assert result.loc["C-D", "peer_baseline"] == pytest.approx(3.0)
    assert result.loc["E-F", "peer_baseline"] == pytest.approx(2.0)
    assert np.isnan(result.loc["G-H", "peer_baseline"])

