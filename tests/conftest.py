from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def valid_shipments() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "shipment_id": "S1",
                "origin": "A",
                "destination": "B",
                "route_type": "Short",
                "material": "Steel",
                "quantity_tonnes": 10.0,
                "distance_km": 100.0,
                "freight_cost_inr": 2000.0,
                "shipment_date": "2025-01-06",
                "transporter": "T1",
            },
            {
                "shipment_id": "S2",
                "origin": "A",
                "destination": "B",
                "route_type": "Short",
                "material": "Steel",
                "quantity_tonnes": 20.0,
                "distance_km": 100.0,
                "freight_cost_inr": 6000.0,
                "shipment_date": "2025-01-12",
                "transporter": "T2",
            },
        ]
    )

