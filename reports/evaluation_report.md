# Evaluation Report

## Method

The evaluation uses the manually reviewed cases in `evaluation/labeled_cases.csv`.
Anomaly labels and evidence labels are scored separately. The set is intentionally
small and includes boundary cases such as a peer-only high level with a negative
own-history change and notes that explicitly say costs were unaffected.

## Anomaly detection

- Cases: 10
- Accuracy: 1.000
- Precision: 1.000
- Recall: 1.000
- F1: 1.000
- Confusion counts: TP=5, TN=5, FP=0, FN=0

| Route | Week | Expected | Predicted | Result |
|---|---:|---:|---:|---|
| Ahmedabad-Mumbai | 2025-01-20 | True | True | PASS |
| Ahmedabad-Mumbai | 2025-01-13 | False | False | PASS |
| Chennai-Bangalore | 2025-02-24 | True | True | PASS |
| Chennai-Bangalore | 2025-03-10 | True | True | PASS |
| Delhi-Jaipur | 2024-11-11 | True | True | PASS |
| Delhi-Jaipur | 2024-11-04 | False | False | PASS |
| Mumbai-Pune | 2025-09-15 | True | True | PASS |
| Mumbai-Pune | 2025-09-08 | False | False | PASS |
| Mumbai-Pune | 2025-11-10 | False | False | PASS |
| Kolkata-Bhubaneswar | 2025-06-09 | False | False | PASS |

## Evidence matching

- Cases: 8
- Exact note-ID accuracy: 1.000
- Justification precision: 1.000
- Justification recall: 1.000
- Justification F1: 1.000

| Route | Week | Expected note | Predicted note | Result |
|---|---:|---|---|---|
| Ahmedabad-Mumbai | 2025-01-20 | N002 | N002 | PASS |
| Chennai-Bangalore | 2025-02-24 | N001 | N001 | PASS |
| Chennai-Bangalore | 2025-03-03 | N001 | N001 | PASS |
| Chennai-Bangalore | 2025-03-10 | (blank) | (blank) | PASS |
| Chennai-Bangalore | 2025-03-17 | (blank) | (blank) | PASS |
| Delhi-Jaipur | 2024-11-11 | (blank) | (blank) | PASS |
| Mumbai-Pune | 2025-06-23 | (blank) | (blank) | PASS |
| Mumbai-Pune | 2025-10-27 | (blank) | (blank) | PASS |

## Full justified-row audit

Every justified output row was revalidated against its exact original note.

| Route | Week | Note | Effective interval | Result |
|---|---:|---|---|---|
| Ahmedabad-Mumbai | 2025-01-20 | N002 | 2025-01-20 to 2025-01-26 | PASS |
| Chennai-Bangalore | 2025-02-24 | N001 | 2025-02-24 to 2025-03-08 | PASS |
| Chennai-Bangalore | 2025-03-03 | N001 | 2025-02-24 to 2025-03-08 | PASS |

Audit result: 3 of 3 justified rows passed.

## Limitations

- The labeled set is small and curated from this synthetic dataset; the metrics do not establish production generalization.
- Threshold labels reflect the documented 20% policy and the requirement for a positive own-history change.
- Note validation uses conservative language and date rules. Unfamiliar phrasing may be rejected as unexplained rather than guessed.
