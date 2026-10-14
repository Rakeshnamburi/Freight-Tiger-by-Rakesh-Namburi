"""Same-week, same-route-type comparison against other routes only."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_peer_baseline(weekly: pd.DataFrame) -> pd.DataFrame:
    result = weekly.copy()
    groups = result.groupby(["route_type", "week_of"], sort=False)[
        "cost_per_tonne_km"
    ]
    peer_sum = groups.transform("sum") - result["cost_per_tonne_km"]
    peer_count = groups.transform("count") - 1
    result["peer_route_count"] = peer_count.astype(int)
    result["peer_baseline"] = np.where(peer_count > 0, peer_sum / peer_count, np.nan)
    result["vs_similar_routes_pct"] = np.where(
        result["peer_baseline"].notna() & result["peer_baseline"].ne(0),
        (result["cost_per_tonne_km"] / result["peer_baseline"] - 1.0) * 100.0,
        np.nan,
    )
    return result

