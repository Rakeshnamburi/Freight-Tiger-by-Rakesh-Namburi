"""Manual labeled-set evaluation and justified-row evidence audit."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .data_loader import load_context_notes
from .evidence_validator import validate_note_for_observation
from .main import run_pipeline


def _binary_metrics(expected: list[bool], predicted: list[bool]) -> dict[str, float | int]:
    tp = sum(e and p for e, p in zip(expected, predicted))
    tn = sum((not e) and (not p) for e, p in zip(expected, predicted))
    fp = sum((not e) and p for e, p in zip(expected, predicted))
    fn = sum(e and (not p) for e, p in zip(expected, predicted))
    accuracy = (tp + tn) / len(expected) if expected else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def evaluate_analysis(
    analysis: pd.DataFrame,
    notes: pd.DataFrame,
    cases_path: str | Path,
    report_path: str | Path,
) -> dict[str, float | int]:
    cases = pd.read_csv(cases_path, keep_default_na=False)
    indexed = analysis.set_index(["route", "week_of"], drop=False)

    anomaly_cases = cases[cases["case_type"].eq("anomaly")].copy()
    expected_anomalies: list[bool] = []
    predicted_anomalies: list[bool] = []
    anomaly_rows: list[str] = []
    for _, case in anomaly_cases.iterrows():
        key = (case["route"], pd.Timestamp(case["week_of"]))
        row = indexed.loc[key]
        expected = case["expected_anomaly"].strip().lower() == "true"
        predicted = bool(row["is_anomaly"])
        expected_anomalies.append(expected)
        predicted_anomalies.append(predicted)
        anomaly_rows.append(
            f"| {case['route']} | {case['week_of']} | {expected} | {predicted} | "
            f"{'PASS' if expected == predicted else 'FAIL'} |"
        )
    anomaly_metrics = _binary_metrics(expected_anomalies, predicted_anomalies)

    evidence_cases = cases[cases["case_type"].eq("evidence")].copy()
    evidence_correct = 0
    expected_justified: list[bool] = []
    predicted_justified: list[bool] = []
    evidence_rows: list[str] = []
    for _, case in evidence_cases.iterrows():
        key = (case["route"], pd.Timestamp(case["week_of"]))
        row = indexed.loc[key]
        expected_note = case["expected_note_id"].strip()
        predicted_note = str(row["matched_note_id"] or "")
        correct = expected_note == predicted_note
        evidence_correct += int(correct)
        expected_justified.append(bool(expected_note))
        predicted_justified.append(bool(predicted_note))
        evidence_rows.append(
            f"| {case['route']} | {case['week_of']} | {expected_note or '(blank)'} | "
            f"{predicted_note or '(blank)'} | {'PASS' if correct else 'FAIL'} |"
        )
    evidence_metrics = _binary_metrics(expected_justified, predicted_justified)
    evidence_exact_accuracy = evidence_correct / len(evidence_cases)

    note_lookup = notes.set_index("note_id", drop=False)
    justified = analysis[
        analysis["is_anomaly"] & analysis["matched_note_id"].ne("")
    ]
    audit_rows: list[str] = []
    audit_failures: list[str] = []
    for _, observation in justified.iterrows():
        note_id = observation["matched_note_id"]
        note = note_lookup.loc[note_id]
        valid, detail, window = validate_note_for_observation(observation, note)
        status = "PASS" if valid else "FAIL"
        if not valid:
            audit_failures.append(
                f"{observation['route']} {observation['week_of']:%Y-%m-%d} {note_id}: {detail}"
            )
        end_text = window[1].strftime("%Y-%m-%d") if window[1] is not None else "open"
        audit_rows.append(
            f"| {observation['route']} | {observation['week_of']:%Y-%m-%d} | "
            f"{note_id} | {window[0]:%Y-%m-%d} to {end_text} | {status} |"
        )
    if audit_failures:
        raise AssertionError("Justified-row audit failed: " + "; ".join(audit_failures))

    report = f"""# Evaluation Report

## Method

The evaluation uses the manually reviewed cases in `evaluation/labeled_cases.csv`.
Anomaly labels and evidence labels are scored separately. The set is intentionally
small and includes boundary cases such as a peer-only high level with a negative
own-history change and notes that explicitly say costs were unaffected.

## Anomaly detection

- Cases: {len(anomaly_cases)}
- Accuracy: {anomaly_metrics['accuracy']:.3f}
- Precision: {anomaly_metrics['precision']:.3f}
- Recall: {anomaly_metrics['recall']:.3f}
- F1: {anomaly_metrics['f1']:.3f}
- Confusion counts: TP={anomaly_metrics['tp']}, TN={anomaly_metrics['tn']}, FP={anomaly_metrics['fp']}, FN={anomaly_metrics['fn']}

| Route | Week | Expected | Predicted | Result |
|---|---:|---:|---:|---|
{chr(10).join(anomaly_rows)}

## Evidence matching

- Cases: {len(evidence_cases)}
- Exact note-ID accuracy: {evidence_exact_accuracy:.3f}
- Justification precision: {evidence_metrics['precision']:.3f}
- Justification recall: {evidence_metrics['recall']:.3f}
- Justification F1: {evidence_metrics['f1']:.3f}

| Route | Week | Expected note | Predicted note | Result |
|---|---:|---|---|---|
{chr(10).join(evidence_rows)}

## Full justified-row audit

Every justified output row was revalidated against its exact original note.

| Route | Week | Note | Effective interval | Result |
|---|---:|---|---|---|
{chr(10).join(audit_rows)}

Audit result: {len(justified)} of {len(justified)} justified rows passed.

## Limitations

- The labeled set is small and curated from this synthetic dataset; the metrics do not establish production generalization.
- Threshold labels reflect the documented 20% policy and the requirement for a positive own-history change.
- Note validation uses conservative language and date rules. Unfamiliar phrasing may be rejected as unexplained rather than guessed.
"""
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8", newline="\n")
    return {
        "anomaly_cases": len(anomaly_cases),
        "anomaly_accuracy": anomaly_metrics["accuracy"],
        "anomaly_f1": anomaly_metrics["f1"],
        "evidence_cases": len(evidence_cases),
        "evidence_exact_accuracy": evidence_exact_accuracy,
        "justified_rows_audited": len(justified),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the labeled evaluation harness.")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--cases", default="evaluation/labeled_cases.csv")
    parser.add_argument("--output", default="output/freight_cost_analysis.csv")
    parser.add_argument("--report", default="reports/evaluation_report.md")
    args = parser.parse_args()
    analysis, _ = run_pipeline(args.data_dir, args.output)
    notes = load_context_notes(Path(args.data_dir) / "context_notes.csv")
    metrics = evaluate_analysis(analysis, notes, args.cases, args.report)
    print(metrics)


if __name__ == "__main__":
    main()

