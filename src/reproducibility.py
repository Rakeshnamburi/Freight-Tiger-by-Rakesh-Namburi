"""Three-run determinism verification with full-output SHA-256 hashes."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from .main import run_pipeline


NUMERIC_COLUMNS = [
    "cost_per_tonne_km",
    "historical_baseline",
    "peer_baseline",
    "vs_own_history_pct",
    "vs_similar_routes_pct",
]
DECISION_COLUMNS = ["is_anomaly", "matched_note_id", "anomaly_trigger"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_reproducibility(
    data_dir: str | Path, report_path: str | Path
) -> dict[str, object]:
    hashes: list[str] = []
    analyses: list[pd.DataFrame] = []
    report_target = Path(report_path)
    report_target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".repro-tmp-", dir=report_target.parent
    ) as temp_dir:
        for run_number in range(1, 4):
            output = Path(temp_dir) / f"run_{run_number}.csv"
            analysis, _ = run_pipeline(data_dir, output)
            hashes.append(sha256(output))
            analyses.append(analysis.reset_index(drop=True))

    reference = analyses[0]
    numerical_identical = all(
        all(
            np.array_equal(
                reference[column].to_numpy(),
                candidate[column].to_numpy(),
                equal_nan=True,
            )
            for column in NUMERIC_COLUMNS
        )
        for candidate in analyses[1:]
    )
    decisions_identical = all(
        reference[DECISION_COLUMNS].equals(candidate[DECISION_COLUMNS])
        for candidate in analyses[1:]
    )
    full_hashes_identical = len(set(hashes)) == 1
    passed = numerical_identical and decisions_identical and full_hashes_identical

    report = f"""# Reproducibility Report

## Procedure

The full pipeline was executed three times in fresh temporary output locations.
Each run reloaded the unchanged CSV inputs, rebuilt TF-IDF, recalculated every
route-week, retrieved evidence, validated notes, generated explanations, and wrote
a new standards-compliant CSV.

## Results

| Run | SHA-256 of complete CSV |
|---:|---|
| 1 | `{hashes[0]}` |
| 2 | `{hashes[1]}` |
| 3 | `{hashes[2]}` |

- Full-precision numerical columns identical: **{str(numerical_identical).upper()}**
- Flags, verdict inputs, and matched note IDs identical: **{str(decisions_identical).upper()}**
- Complete CSV byte hashes identical: **{str(full_hashes_identical).upper()}**
- Overall reproducibility check: **{'PASS' if passed else 'FAIL'}**

No randomness or generative model is used. TF-IDF ranking has deterministic tie
breaking by note ID, and all output rows use a stable route/date sort.
"""
    report_target.write_text(report, encoding="utf-8", newline="\n")
    if not passed:
        raise AssertionError("three-run reproducibility check failed")
    return {
        "passed": passed,
        "hashes": hashes,
        "numerical_identical": numerical_identical,
        "decisions_identical": decisions_identical,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the pipeline three times.")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--report", default="reports/reproducibility_report.md")
    args = parser.parse_args()
    result = verify_reproducibility(args.data_dir, args.report)
    print(result)


if __name__ == "__main__":
    main()

