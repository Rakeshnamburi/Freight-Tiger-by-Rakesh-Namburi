"""Load validated project inputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .validator import validate_context_notes, validate_shipments


def load_shipments(path: str | Path) -> pd.DataFrame:
    return validate_shipments(pd.read_csv(path))


def load_context_notes(path: str | Path) -> pd.DataFrame:
    return validate_context_notes(pd.read_csv(path))

