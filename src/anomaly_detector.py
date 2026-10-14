"""Deterministic positive cost-increase detection."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class AnomalyConfig:
    history_threshold_pct: float = 20.0
    peer_threshold_pct: float = 20.0
    require_positive_history: bool = True


def detect_anomalies(
    comparisons: pd.DataFrame, config: AnomalyConfig | None = None
) -> pd.DataFrame:
    """Flag unusual levels while requiring evidence of a temporal increase.

    A row is anomalous when its cost is above its own trailing baseline and either
    the own-history or peer comparison reaches the configured threshold. Requiring
    a positive own-history comparison prevents a high-but-decreasing route from
    being mislabeled as a cost-increase anomaly.
    """

    config = config or AnomalyConfig()
    result = comparisons.copy()

    has_history = result["vs_own_history_pct"].notna()
    positive_history = result["vs_own_history_pct"] > 0
    history_trigger = result["vs_own_history_pct"] >= config.history_threshold_pct
    peer_trigger = result["vs_similar_routes_pct"] >= config.peer_threshold_pct

    if config.require_positive_history:
        result["is_anomaly"] = has_history & positive_history & (
            history_trigger | peer_trigger
        )
    else:
        result["is_anomaly"] = history_trigger | peer_trigger

    result["history_trigger"] = history_trigger.fillna(False)
    result["peer_trigger"] = peer_trigger.fillna(False)
    result["anomaly_trigger"] = ""
    result.loc[result["history_trigger"], "anomaly_trigger"] = "history"
    result.loc[result["peer_trigger"], "anomaly_trigger"] = "peer"
    result.loc[
        result["history_trigger"] & result["peer_trigger"], "anomaly_trigger"
    ] = "history_and_peer"
    result.loc[~result["is_anomaly"], "anomaly_trigger"] = ""
    return result

