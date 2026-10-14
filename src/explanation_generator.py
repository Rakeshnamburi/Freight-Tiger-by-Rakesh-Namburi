"""Deterministic, evidence-grounded explanation templates."""

from __future__ import annotations

import pandas as pd

from .anomaly_detector import AnomalyConfig
from .evidence_validator import EvidenceMatch


def _evidence_fact(match: EvidenceMatch) -> str:
    text = match.note_text.lower()
    if "flood" in text and "detour" in text:
        return "route-specific flooding forced detours and explicitly raised trip costs"
    if "festival" in text and "surcharge" in text:
        return "a route-specific festival surcharge was active because truck supply was limited"
    if "diesel" in text:
        return "a nationwide diesel-price increase explicitly raised transportation costs"
    if "toll" in text:
        return "a toll change explicitly increased transportation costs"
    return "the note explicitly describes a transportation-cost increase"


def generate_explanation(
    observation: pd.Series,
    match: EvidenceMatch | None,
    config: AnomalyConfig,
) -> str:
    if not bool(observation["is_anomaly"]):
        if int(observation.get("history_observations", 0)) == 0:
            return "No anomaly decision: this is the first available week for the route."
        return (
            "No unusual positive cost increase detected under the configured "
            f"{config.history_threshold_pct:.0f}% history and "
            f"{config.peer_threshold_pct:.0f}% peer thresholds."
        )

    if match is None:
        return (
            "Unexplained: an unusual positive cost increase was detected, but no supplied "
            "context note passed the route, date, positive-impact, contradiction, and "
            "magnitude checks. Human review is required."
        )

    if match.effective_end is None:
        period = f"from {match.effective_start:%Y-%m-%d} onward"
    elif match.effective_start == match.effective_end:
        period = f"on {match.effective_start:%Y-%m-%d}"
    else:
        period = (
            f"from {match.effective_start:%Y-%m-%d} to "
            f"{match.effective_end:%Y-%m-%d}"
        )
    return (
        f"Justified by note {match.note_id} dated {match.note_date:%Y-%m-%d}: "
        f"{_evidence_fact(match)} {period}."
    )

