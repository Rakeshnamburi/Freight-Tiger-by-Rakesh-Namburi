"""Conservative route, time, impact, contradiction, and magnitude validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

import pandas as pd


MONTHS = {
    name.lower(): number
    for number, name in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        start=1,
    )
}
MONTHS.update({name[:3]: number for name, number in list(MONTHS.items())})

POSITIVE_COST_PATTERNS = (
    r"higher\s+(?:trip\s+)?costs?",
    r"push(?:ing|ed)?\s+up\s+(?:transportation|freight|trip)\s+costs?",
    r"(?:temporary\s+)?surcharge\s+(?:was\s+)?applied",
    r"(?:freight|transportation)\s+(?:rates?|costs?)\s+(?:rose|increased)",
    r"increased\s+(?:freight|transportation|trip)\s+costs?",
)

CONTRADICTION_PATTERNS = (
    r"costs?\s+were\s+not\s+significantly\s+affected",
    r"without\s+a\s+rate\s+change",
    r"no\s+significant\s+disruptions?",
    r"remained\s+stable",
    r"returned\s+to\s+normal",
    r"normal\s+conditions",
    r"freight\s+movement\s+remained\s+normal",
    r"no\s+major\s+disruptions?",
    r"absorbed\s+by\s+transporters",
    r"not\s+part\s+of\s+this\s+dataset",
    r"improved\s+road\s+conditions",
)


@dataclass(frozen=True)
class EvidenceMatch:
    note_id: str
    note_date: pd.Timestamp
    note_text: str
    applies_to: str
    effective_start: pd.Timestamp
    effective_end: pd.Timestamp | None
    retrieval_score: float


def _normalize(text: object) -> str:
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _month_day(month: str, day: str, year: int) -> pd.Timestamp:
    month_number = MONTHS[month.lower()]
    return pd.Timestamp(datetime(year, month_number, int(day)))


def effective_window(note: pd.Series) -> tuple[pd.Timestamp, pd.Timestamp | None]:
    """Infer a conservative effective interval from the note's explicit wording."""

    note_date = pd.Timestamp(note["date"]).normalize()
    text = _normalize(note["note"])
    explicit = re.search(
        r"from\s+([a-z]{3,9})\s+(\d{1,2})\s+to\s+([a-z]{3,9})\s+(\d{1,2})",
        text,
    )
    if explicit:
        start = _month_day(explicit.group(1), explicit.group(2), note_date.year)
        end_year = note_date.year
        end = _month_day(explicit.group(3), explicit.group(4), end_year)
        if end < start:
            end = _month_day(explicit.group(3), explicit.group(4), end_year + 1)
        return start, end

    if "starting this week" in text:
        return note_date, None

    if "this quarter" in text:
        period = note_date.to_period("Q")
        return period.start_time.normalize(), period.end_time.normalize()

    if re.search(r"festival\s+week|about\s+a\s+week|this\s+week", text):
        return note_date, note_date + pd.Timedelta(days=6)

    # Without explicit duration, limit applicability to the dated week. This is
    # intentionally conservative and avoids carrying temporary events forever.
    return note_date, note_date + pd.Timedelta(days=6)


def _route_applies(note: pd.Series, route: str) -> tuple[bool, bool]:
    applies_to = _normalize(note["applies_to"])
    route_normalized = _normalize(route)
    nationwide = applies_to in {"all routes", "nationwide", "all"}
    return nationwide or applies_to == route_normalized, nationwide


def _supports_cost_increase(note_text: str) -> bool:
    text = _normalize(note_text)
    if any(re.search(pattern, text) for pattern in CONTRADICTION_PATTERNS):
        return False
    return any(re.search(pattern, text) for pattern in POSITIVE_COST_PATTERNS)


def _percentage_upper_bound(note_text: str) -> float | None:
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*%",
        _normalize(note_text),
    )
    return float(match.group(2)) if match else None


def validate_note_for_observation(
    observation: pd.Series, note: pd.Series
) -> tuple[bool, str, tuple[pd.Timestamp, pd.Timestamp | None]]:
    route_valid, nationwide = _route_applies(note, str(observation["route"]))
    if not route_valid:
        return False, "wrong route", effective_window(note)

    start, end = effective_window(note)
    week_start = pd.Timestamp(observation["week_of"]).normalize()
    week_end = week_start + pd.Timedelta(days=6)
    overlaps = start <= week_end and (end is None or end >= week_start)
    if not overlaps:
        return False, "outside effective period", (start, end)

    if not _supports_cost_increase(str(note["note"])):
        return False, "no explicit positive cost impact or note contradicts impact", (start, end)

    # A nationwide factor affects peer routes in the same week too. It cannot by
    # itself explain a route that is anomalous only relative to its peers.
    if nationwide and not bool(observation.get("history_trigger", False)):
        return False, "nationwide note cannot explain a peer-only divergence", (start, end)

    upper_bound = _percentage_upper_bound(str(note["note"]))
    own_change = observation.get("vs_own_history_pct")
    if (
        upper_bound is not None
        and pd.notna(own_change)
        and float(own_change) > upper_bound + 5.0
    ):
        return False, "stated impact is materially smaller than the observed rise", (start, end)

    return True, "valid", (start, end)


def select_valid_evidence(
    observation: pd.Series, candidates: pd.DataFrame
) -> EvidenceMatch | None:
    """Return the best candidate only after all deterministic checks pass."""

    valid: list[tuple[int, float, pd.Timestamp, str, pd.Series, tuple]] = []
    for _, note in candidates.iterrows():
        is_valid, _, window = validate_note_for_observation(observation, note)
        if not is_valid:
            continue
        nationwide = _normalize(note["applies_to"]) in {"all routes", "nationwide", "all"}
        valid.append(
            (
                0 if nationwide else 1,
                float(note.get("retrieval_score", 0.0)),
                pd.Timestamp(note["date"]),
                str(note["note_id"]),
                note,
                window,
            )
        )

    if not valid:
        return None

    valid.sort(key=lambda item: (-item[0], -item[1], -item[2].value, item[3]))
    _, score, note_date, note_id, note, window = valid[0]
    return EvidenceMatch(
        note_id=note_id,
        note_date=note_date,
        note_text=str(note["note"]),
        applies_to=str(note["applies_to"]),
        effective_start=window[0],
        effective_end=window[1],
        retrieval_score=score,
    )

