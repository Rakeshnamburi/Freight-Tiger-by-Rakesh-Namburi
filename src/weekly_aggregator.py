"""Monday-based route-week aggregation."""

from __future__ import annotations

import pandas as pd


ROUTE_KEYS = ["origin", "destination", "route_type"]


def add_monday_week(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["week_of"] = result["shipment_date"].dt.normalize() - pd.to_timedelta(
        result["shipment_date"].dt.weekday, unit="D"
    )
    return result


def aggregate_weekly_costs(shipments: pd.DataFrame) -> pd.DataFrame:
    """Calculate weighted cost per tonne-km for every route-week."""

    enriched = add_monday_week(shipments)
    enriched["tonne_km"] = enriched["quantity_tonnes"] * enriched["distance_km"]

    weekly = (
        enriched.groupby(ROUTE_KEYS + ["week_of"], as_index=False, sort=True)
        .agg(
            total_freight_cost_inr=("freight_cost_inr", "sum"),
            total_tonne_km=("tonne_km", "sum"),
            shipment_count=("shipment_id", "size"),
        )
        .sort_values(ROUTE_KEYS + ["week_of"], kind="mergesort")
        .reset_index(drop=True)
    )
    weekly["cost_per_tonne_km"] = (
        weekly["total_freight_cost_inr"] / weekly["total_tonne_km"]
    )
    weekly["route"] = weekly["origin"] + "-" + weekly["destination"]
    return weekly

