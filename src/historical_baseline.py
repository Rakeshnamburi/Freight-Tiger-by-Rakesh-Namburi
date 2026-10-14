"""Trailing route-history baseline without look-ahead leakage."""

from __future__ import annotations

import numpy as np
import pandas as pd


ROUTE_GROUP = ["origin", "destination", "route_type"]


def add_historical_baseline(weekly: pd.DataFrame, window: int = 8) -> pd.DataFrame:
    if window <= 0:
        raise ValueError("historical window must be positive")

    result = weekly.sort_values(ROUTE_GROUP + ["week_of"], kind="mergesort").copy()
    grouped = result.groupby(ROUTE_GROUP, sort=False)["cost_per_tonne_km"]
    result["historical_baseline"] = grouped.transform(
        lambda values: values.shift(1).rolling(window=window, min_periods=1).mean()
    )
    result["history_observations"] = (
        result.groupby(ROUTE_GROUP, sort=False).cumcount().clip(upper=window).astype(int)
    )
    result["vs_own_history_pct"] = np.where(
        result["historical_baseline"].notna() & result["historical_baseline"].ne(0),
        (result["cost_per_tonne_km"] / result["historical_baseline"] - 1.0) * 100.0,
        np.nan,
    )
    return result

