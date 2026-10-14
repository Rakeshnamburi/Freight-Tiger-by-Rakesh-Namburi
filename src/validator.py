"""Input and output validation rules for the freight-cost pipeline."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd


SHIPMENT_REQUIRED_COLUMNS = [
    "shipment_id",
    "origin",
    "destination",
    "route_type",
    "material",
    "quantity_tonnes",
    "distance_km",
    "freight_cost_inr",
    "shipment_date",
    "transporter",
]

CONTEXT_REQUIRED_COLUMNS = ["note_id", "date", "applies_to", "note"]

OUTPUT_COLUMNS = [
    "route",
    "week_of",
    "cost_per_tonne_km",
    "vs_own_history",
    "vs_similar_routes",
    "flagged",
    "matched_note_id",
    "reason",
]

VALID_ROUTE_TYPES = {"Short", "Medium", "Long"}


class DataValidationError(ValueError):
    """Raised when an input violates a pipeline data contract."""


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise DataValidationError(f"{label} is missing required columns: {missing}")


def _require_nonblank(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    for column in columns:
        values = frame[column]
        if values.isna().any() or values.astype(str).str.strip().eq("").any():
            raise DataValidationError(f"{label}.{column} contains blank values")


def validate_shipments(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize shipment input without mutating the caller's frame."""

    _require_columns(frame, SHIPMENT_REQUIRED_COLUMNS, "shipment_records")
    result = frame.copy()
    _require_nonblank(
        result,
        [
            "shipment_id",
            "origin",
            "destination",
            "route_type",
            "material",
            "shipment_date",
            "transporter",
        ],
        "shipment_records",
    )

    if result["shipment_id"].duplicated().any():
        duplicates = result.loc[result["shipment_id"].duplicated(), "shipment_id"].tolist()
        raise DataValidationError(f"shipment_id must be unique; duplicates: {duplicates[:5]}")

    invalid_route_types = sorted(set(result["route_type"]) - VALID_ROUTE_TYPES)
    if invalid_route_types:
        raise DataValidationError(f"unsupported route_type values: {invalid_route_types}")

    try:
        result["shipment_date"] = pd.to_datetime(result["shipment_date"], errors="raise")
    except (ValueError, TypeError) as exc:
        raise DataValidationError("shipment_date contains invalid dates") from exc

    numeric_columns = ["quantity_tonnes", "distance_km", "freight_cost_inr"]
    for column in numeric_columns:
        try:
            result[column] = pd.to_numeric(result[column], errors="raise")
        except (ValueError, TypeError) as exc:
            raise DataValidationError(f"{column} must be numeric") from exc
        if not np.isfinite(result[column].to_numpy(dtype=float)).all():
            raise DataValidationError(f"{column} contains non-finite values")

    if (result["quantity_tonnes"] <= 0).any():
        raise DataValidationError("quantity_tonnes must be greater than zero")
    if (result["distance_km"] <= 0).any():
        raise DataValidationError("distance_km must be greater than zero")
    if (result["freight_cost_inr"] < 0).any():
        raise DataValidationError("freight_cost_inr cannot be negative")

    return result


def validate_context_notes(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize context-note input."""

    _require_columns(frame, CONTEXT_REQUIRED_COLUMNS, "context_notes")
    result = frame.copy()
    _require_nonblank(result, CONTEXT_REQUIRED_COLUMNS, "context_notes")

    if result["note_id"].duplicated().any():
        duplicates = result.loc[result["note_id"].duplicated(), "note_id"].tolist()
        raise DataValidationError(f"note_id must be unique; duplicates: {duplicates[:5]}")
    try:
        result["date"] = pd.to_datetime(result["date"], errors="raise")
    except (ValueError, TypeError) as exc:
        raise DataValidationError("context note date contains invalid dates") from exc

    return result


def validate_output_csv(path: str | Path, expected_rows: int | None = None) -> None:
    """Parse the output strictly and enforce the exact eight-column contract."""

    output_path = Path(path)
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        if reader.fieldnames != OUTPUT_COLUMNS:
            raise DataValidationError(
                f"output header must be exactly {OUTPUT_COLUMNS}; got {reader.fieldnames}"
            )
        rows = list(reader)

    if expected_rows is not None and len(rows) != expected_rows:
        raise DataValidationError(
            f"output row count mismatch: expected {expected_rows}, got {len(rows)}"
        )
    for index, row in enumerate(rows, start=2):
        if None in row:
            raise DataValidationError(f"malformed CSV row {index}")

