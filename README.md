# Freight Tiger Smart Shipping Cost Monitoring Assistant

A deterministic Python pipeline that monitors weekly route costs, finds unusual
positive increases, retrieves context with TF-IDF, and validates every proposed
justification before writing the required eight-column CSV.

The implementation processes the complete supplied dataset locally. It makes no
network calls and uses no generative LLM, so calculations, note IDs, verdicts,
explanations, and output ordering are reproducible.

## Reviewer quick start

1. Read this README for the approach, formulas, evidence safeguards, and results.
2. Open `output/freight_cost_analysis.csv` for the required eight-column submission.
3. Optionally open `output/FreightTiger_Cost_Analysis.xlsx` for a visual dashboard
   and editable route-level anomaly chart.
4. Follow the commands below to reproduce the CSV and run all automated tests.
5. Use `WALKTHROUGH.md` for the prepared 10-minute Round 2 demonstration.

## Executed results

| Measure | Result |
|---|---:|
| Shipment records | 2,940 |
| Shipment date range | 2024-01-01 to 2025-12-28 |
| Routes | 7 |
| Route types | Short, Medium, Long |
| Route-week observations | 728 |
| Normal observations | 709 |
| Detected anomalies | 19 |
| Justified anomalies | 3 |
| Unexplained anomalies | 16 |
| Automated tests | 19 passed |
| Labeled anomaly cases | 10/10 correct |
| Labeled evidence cases | 8/8 exact note-ID matches |
| Three-run SHA-256 | `444675348b190483531f6fb53aae8ce9fac3d5d8ca221eafd2b4c7946167dca5` |
| LLM calls / tokens / cost | 0 / 0 / USD 0.00 |

## Input profile

The source contains seven directed routes, each with 104 weekly observations:

- Short: Delhi-Jaipur, Mumbai-Pune
- Medium: Ahmedabad-Mumbai, Chennai-Bangalore, Kolkata-Bhubaneswar
- Long: Delhi-Chennai, Mumbai-Delhi

There are no null input values or duplicate shipment IDs. Quantity ranges from
9.0 to 22.0 tonnes, distance from 147.0 to 2,220.0 km, and freight cost from
INR 4,710 to INR 105,839. Validation still rejects missing fields, duplicate IDs,
invalid dates, unsupported route types, non-finite values, and zero or negative
quantity/distance before calculations begin.

## Architecture

| Module | Responsibility |
|---|---|
| `data_loader.py`, `validator.py` | Read CSVs and enforce data contracts |
| `weekly_aggregator.py` | Assign Monday weeks and calculate weighted cost |
| `historical_baseline.py` | Build the prior-eight-available-week route baseline |
| `peer_comparison.py` | Build the other-route same-type same-week baseline |
| `anomaly_detector.py` | Apply configurable positive-increase rules |
| `context_retriever.py` | Rank supplied notes with TF-IDF cosine similarity |
| `evidence_validator.py` | Enforce route, time, impact, contradiction, and magnitude checks |
| `explanation_generator.py` | Produce deterministic grounded explanations |
| `output_writer.py` | Write and strictly re-parse the exact CSV contract |
| `evaluation.py` | Score the manual labeled set and audit every justified row |
| `reproducibility.py` | Execute three clean runs and compare values and hashes |
| `cost_tracker.py` | Report actual LLM calls, tokens, and API cost |

Data flow:

```text
shipments -> validation -> Monday route-week aggregation
          -> trailing history + same-week peers -> anomaly decision
context notes -> TF-IDF retrieval -> deterministic evidence validation
          -> grounded reason -> strict eight-column CSV
```

## Calculations

For shipment `i`:

```text
tonne_km_i = quantity_tonnes_i * distance_km_i
```

For route-week `r,w`:

```text
cost_per_tonne_km_r,w = sum(freight_cost_inr_i) / sum(tonne_km_i)
```

This is a weighted calculation. The pipeline never averages shipment-level
cost-per-tonne-km ratios.

The historical baseline is the arithmetic mean of the route's previous eight
available weekly cost observations. The current week and all future weeks are
excluded. With one to seven prior observations, all available prior observations
are used. With none, the comparison stays blank.

The peer baseline is the arithmetic mean of weekly cost-per-tonne-km for all
other routes with the same `route_type` in the exact same week. The current route
is removed, and different route types never enter the calculation.

Both percentages use:

```text
percentage_difference = (current / baseline - 1) * 100
```

Full precision is retained internally. Output cost is rounded to two decimals and
comparison percentages to one decimal, matching the supplied format examples.

## Anomaly policy

Default thresholds are 20% above own history or 20% above same-type peers. A row
also must be above its own historical baseline. Formally:

```text
has_prior_history
AND vs_own_history > 0
AND (vs_own_history >= 20% OR vs_similar_routes >= 20%)
```

This separates a positive cost increase from a route that is structurally costly
but currently decreasing. The 20% setting captures the supplied example flags
(including the +21.0% and +23.6% peer examples) and limits the dataset result to
19 of 728 route-weeks (2.6%). It is intentionally configurable rather than a
claim of a universal business threshold:

```powershell
python -m src.main --history-threshold 25 --peer-threshold 25
```

Lower thresholds improve sensitivity but increase operational review volume and
peer-structure false positives. Higher thresholds reduce review volume but can
miss moderate increases.

## Grounded retrieval and evidence validation

`context_notes.csv` is the only factual source. A local TF-IDF model indexes note
scope, date, month, and note text using word unigrams and bigrams. For each numeric
anomaly it retrieves the five highest-scoring notes with deterministic note-ID tie
breaking.

Retrieval is only candidate generation. A note can justify a row only when all of
these checks pass:

1. Scope is the exact route or explicitly all routes.
2. Its explicit effective interval overlaps the Monday-Sunday week.
3. The text explicitly states a positive transportation-cost impact.
4. It does not say costs were unaffected, stable, normal, restored, absorbed, or
   outside this dataset.
5. A nationwide note is not used to explain a peer-only divergence because the
   same-week peers were exposed too.
6. When a note states a percentage range, a materially larger observed rise is
   rejected rather than overclaimed.

Temporary events default to a one-week window unless the note gives dates. A
state change explicitly described as starting on a date can remain open-ended.
N001 therefore applies to weeks beginning 2025-02-24 and 2025-03-03, but not
2025-03-10. N002 applies only to the festival week beginning 2025-01-20.

An anomaly with valid evidence receives `No (justified)` and the exact note ID.
An anomaly without valid evidence receives `Yes` and a blank note ID. A normal
observation receives `No` and a blank note ID.

## Worked route-week example

For Delhi-Jaipur during the week of 2024-11-11:

```text
total freight cost = INR 84,388
total tonne-km     = 20,222.59
weekly cost        = 84,388 / 20,222.59 = 4.172957 INR/tonne-km
prior-8-week mean  = 3.079217
other Short route = 3.447746
vs own history     = +35.520091%
vs peers           = +21.034360%
```

The row exceeds both thresholds. No supplied note passes the evidence checks, so
the final verdict is `Yes`, `matched_note_id` is blank, and the reason requests
human review.

## Output contract

The generated file is `output/freight_cost_analysis.csv`. Its header is exactly:

```text
route,week_of,cost_per_tonne_km,vs_own_history,vs_similar_routes,flagged,matched_note_id,reason
```

Rows are sorted by route then week. Python's standard `csv` writer handles quoting,
and the completed file is immediately re-read with `csv.DictReader(strict=True)`
to verify its header, row count, and structure.

## Installation and execution

Python 3.11 or newer is required. The verified host used Python 3.13.14, pandas
3.0.5, NumPy 2.5.1, scikit-learn 1.9.1, and pytest 8.3.5.

```powershell
cd FreightTiger-AI-CaseStudy
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.main --data-dir data --output output/freight_cost_analysis.csv --reports-dir reports
```

Run verification:

```powershell
python -m pytest -q
python -m src.evaluation --data-dir data --cases evaluation/labeled_cases.csv --output output/freight_cost_analysis.csv --report reports/evaluation_report.md
python -m src.reproducibility --data-dir data --report reports/reproducibility_report.md
```

On macOS or Linux, activate with `source .venv/bin/activate`; the Python module
commands are unchanged.

## Verification performed

- All 19 pytest tests passed in the final run.
- The independent source-data spot check recalculates a weekly weighted cost
  without using the aggregator's result.
- Sample-format examples were reproduced to rounding: Delhi-Jaipur 4.17 / +35.5%
  / +21.0%; Ahmedabad-Mumbai 3.29 / +29.5% / +22.5%; Mumbai-Pune 3.98 /
  +9.2% / +23.6%.
- The manual labeled set scored anomaly detection and evidence matching separately.
- Every one of the three justified output rows was revalidated against its exact
  original note.
- Three full untouched runs produced identical full-precision numbers, decisions,
  note IDs, complete CSV bytes, and SHA-256 hashes.

Detailed results are in `reports/evaluation_report.md`,
`reports/reproducibility_report.md`, and `reports/token_cost_report.md`.

## Token and cost accounting

One complete run made 19 local retrieval queries and zero LLM calls. LLM input
tokens, output tokens, and API cost are all exactly zero. TF-IDF and rule-based
templates do not consume LLM tokens. No model price is applicable.

## Limitations and trade-offs

- A fixed 20% threshold is transparent and easy to audit but is not seasonally or
  statistically calibrated for production use.
- Short and Long route types have only one peer per route, so peer baselines can be
  sensitive to that one comparison route.
- The evidence parser intentionally rejects unfamiliar or ambiguous phrasing. This
  favors unexplained results over fabricated justifications.
- Overlap with any day in a weekly bucket permits a temporary note to support that
  week; daily proration is not attempted.
- The labeled evaluation set is small and synthetic, so perfect case-study metrics
  do not imply production accuracy.
- No optional Streamlit dashboard or free-text question interface is included; the
  mandatory calculation, evidence, testing, evaluation, reproducibility, and
  reporting requirements are prioritized.

