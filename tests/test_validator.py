from __future__ import annotations

import pytest

from src.validator import DataValidationError, validate_shipments


def test_valid_input_is_parsed(valid_shipments):
    result = validate_shipments(valid_shipments)
    assert str(result["shipment_date"].dtype).startswith("datetime64")
    assert len(result) == 2


def test_missing_required_column_is_rejected(valid_shipments):
    with pytest.raises(DataValidationError, match="missing required columns"):
        validate_shipments(valid_shipments.drop(columns=["distance_km"]))


@pytest.mark.parametrize("column", ["quantity_tonnes", "distance_km"])
def test_zero_quantity_or_distance_is_rejected(valid_shipments, column):
    invalid = valid_shipments.copy()
    invalid.loc[0, column] = 0
    with pytest.raises(DataValidationError, match="greater than zero"):
        validate_shipments(invalid)


def test_duplicate_shipment_id_is_rejected(valid_shipments):
    invalid = valid_shipments.copy()
    invalid.loc[1, "shipment_id"] = "S1"
    with pytest.raises(DataValidationError, match="must be unique"):
        validate_shipments(invalid)

