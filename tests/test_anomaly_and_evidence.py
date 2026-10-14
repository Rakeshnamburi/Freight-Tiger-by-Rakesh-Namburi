from __future__ import annotations

import pandas as pd

from src.anomaly_detector import detect_anomalies
from src.evidence_validator import (
    select_valid_evidence,
    validate_note_for_observation,
)


def _observation(
    *,
    route="Chennai-Bangalore",
    week="2025-02-24",
    own=31.0,
    peer=38.0,
    history_trigger=True,
):
    return pd.Series(
        {
            "route": route,
            "route_type": "Medium",
            "week_of": pd.Timestamp(week),
            "vs_own_history_pct": own,
            "vs_similar_routes_pct": peer,
            "history_trigger": history_trigger,
            "peer_trigger": peer >= 20,
            "is_anomaly": True,
        }
    )


def _note(note_id, date, applies_to, text, score=1.0):
    return pd.Series(
        {
            "note_id": note_id,
            "date": pd.Timestamp(date),
            "applies_to": applies_to,
            "note": text,
            "retrieval_score": score,
        }
    )


def test_decrease_is_not_flagged_even_when_peer_level_is_high():
    frame = pd.DataFrame(
        {
            "vs_own_history_pct": [-0.1],
            "vs_similar_routes_pct": [25.0],
        }
    )
    result = detect_anomalies(frame)
    assert not bool(result.loc[0, "is_anomaly"])


def test_route_specific_note_is_valid_inside_explicit_window():
    note = _note(
        "N001",
        "2025-02-24",
        "Chennai-Bangalore",
        "Flooding disrupted trucks from Feb 24 to Mar 8, forcing detours and higher trip costs.",
    )
    valid, _, _ = validate_note_for_observation(_observation(), note)
    assert valid
    valid_second_week, _, _ = validate_note_for_observation(
        _observation(week="2025-03-03"), note
    )
    assert valid_second_week


def test_note_is_invalid_after_its_date_window():
    note = _note(
        "N001",
        "2025-02-24",
        "Chennai-Bangalore",
        "Flooding disrupted trucks from Feb 24 to Mar 8, forcing detours and higher trip costs.",
    )
    valid, reason, _ = validate_note_for_observation(
        _observation(week="2025-03-10"), note
    )
    assert not valid
    assert reason == "outside effective period"


def test_wrong_route_and_no_cost_impact_notes_are_rejected():
    wrong_route = _note(
        "N100",
        "2025-02-24",
        "Mumbai-Delhi",
        "A surcharge was applied and increased transportation costs this week.",
    )
    no_impact = _note(
        "N101",
        "2025-02-24",
        "Chennai-Bangalore",
        "Maintenance caused delays for about a week; costs were not significantly affected.",
    )
    assert not validate_note_for_observation(_observation(), wrong_route)[0]
    assert not validate_note_for_observation(_observation(), no_impact)[0]


def test_nationwide_note_cannot_justify_peer_only_divergence():
    note = _note(
        "N003",
        "2025-05-05",
        "All Routes",
        "Diesel prices rose nationwide starting this week, pushing up transportation costs by 5-7%.",
    )
    observation = _observation(
        route="Mumbai-Pune",
        week="2025-06-23",
        own=6.2,
        peer=20.6,
        history_trigger=False,
    )
    valid, reason, _ = validate_note_for_observation(observation, note)
    assert not valid
    assert "peer-only" in reason


def test_selects_exact_valid_note_id_and_leaves_missing_evidence_blank():
    valid_note = _note(
        "N001",
        "2025-02-24",
        "Chennai-Bangalore",
        "Flooding disrupted trucks from Feb 24 to Mar 8, forcing detours and higher trip costs.",
        score=0.8,
    )
    invalid_note = _note(
        "N999",
        "2025-02-24",
        "Chennai-Bangalore",
        "Road conditions were stable and costs were not significantly affected.",
        score=0.9,
    )
    candidates = pd.DataFrame([invalid_note, valid_note])
    match = select_valid_evidence(_observation(), candidates)
    assert match is not None
    assert match.note_id == "N001"

    missing = select_valid_evidence(_observation(), pd.DataFrame([invalid_note]))
    assert missing is None

