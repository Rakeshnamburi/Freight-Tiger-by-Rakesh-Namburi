# Ten-Minute Walkthrough and Interview Guide

## Demo script

### 0:00-1:00 - State the trust problem

Open `output/freight_cost_analysis.csv`. Explain that the system processes every
shipment, creates one record per directed route and Monday-based week, identifies
unusual positive cost increases, and refuses to invent explanations. The output
contains 728 route-weeks, with 19 anomalies: three justified and 16 unexplained.

### 1:00-2:00 - Show input validation and data grain

Open `src/validator.py` and `src/weekly_aggregator.py`.

- The validator checks required columns, unique shipment IDs, valid dates, the
  Short/Medium/Long domain, finite numeric values, and positive quantity/distance.
- `week_of` subtracts the shipment date's weekday so Monday maps to itself and
  Sunday maps to the preceding Monday.
- The weighted weekly ratio divides total freight cost by total tonne-km.

### 2:00-3:15 - Explain both baselines

Open `src/historical_baseline.py` and `src/peer_comparison.py`.

- History uses `shift(1)` before an eight-observation rolling mean. That one line
  is the main no-look-ahead guarantee.
- The first week stays missing. Weeks two through eight use only available prior
  observations.
- Peer cost subtracts the current route from the same-week same-type group sum and
  count. Other route types cannot leak into the denominator.

### 3:15-4:15 - Explain the anomaly policy

Open `src/anomaly_detector.py`. The default rule requires a positive own-history
change and a 20% threshold breach versus history or peers. This catches all three
supplied format examples while avoiding a peer-high route that is actually
decreasing versus its own recent cost. Show that thresholds are command-line
configurable.

### 4:15-6:00 - Demonstrate grounded retrieval

Open `src/context_retriever.py` and `src/evidence_validator.py`.

TF-IDF retrieves candidates, but retrieval score never decides truth. The validator
checks scope, date overlap, explicit positive cost impact, contradictions, nationwide
signal alignment, and stated magnitude. This separation is the main hallucination
control.

Use Chennai-Bangalore as the example:

- Week 2025-02-24: N001 applies and explicitly says flood detours raised trip costs.
- Week 2025-03-03: the Monday-Sunday week overlaps N001 through March 8, so it is
  also justified.
- Week 2025-03-10: N001 has ended. N009 later says conditions returned to normal,
  so no justification is allowed.

### 6:00-7:15 - Walk a numerical row

For Delhi-Jaipur on 2024-11-11:

```text
INR 84,388 / 20,222.59 tonne-km = 4.172957 INR/tonne-km
history baseline = 3.079217 -> +35.520091%
Short-route peer = 3.447746 -> +21.034360%
```

It is anomalous. No valid route-and-time cost note exists, so the assistant leaves
`matched_note_id` blank and marks the row `Yes` for review.

### 7:15-8:15 - Show tests and evaluation

Run:

```powershell
python -m pytest -q
python -m src.evaluation --data-dir data --cases evaluation/labeled_cases.csv --output output/freight_cost_analysis.csv --report reports/evaluation_report.md
```

Point out the 19 passing tests and the separate metrics: 10 anomaly cases and eight
evidence cases. Then show the full justified-row audit in the evaluation report.

### 8:15-9:00 - Show reproducibility and cost

Run:

```powershell
python -m src.reproducibility --data-dir data --report reports/reproducibility_report.md
```

All three runs produce SHA-256
`444675348b190483531f6fb53aae8ce9fac3d5d8ca221eafd2b4c7946167dca5`.
Open `reports/token_cost_report.md`: 19 local retrieval queries, zero LLM calls,
zero tokens, and zero API cost.

### 9:00-10:00 - Close with trade-offs

The main strengths are exact baseline definitions, conservative evidence checks,
standard CSV handling, deterministic output, and explicit tests. The main limits
are a fixed threshold, small peer groups, a small synthetic evaluation set, and a
conservative rule parser that may reject unfamiliar valid evidence. In production,
the next step would be threshold calibration and monitored human feedback, not an
LLM deciding the mathematics or verdict.

## Module map

| Module | Interview explanation |
|---|---|
| `validator.py` | Fails fast before invalid denominators or dates reach analytics |
| `weekly_aggregator.py` | Establishes Monday week grain and weighted unit cost |
| `historical_baseline.py` | Uses only prior route observations through `shift(1)` |
| `peer_comparison.py` | Compares other routes only within type and exact week |
| `anomaly_detector.py` | Keeps the configurable numeric decision separate from evidence |
| `context_retriever.py` | Provides deterministic lexical candidate retrieval |
| `evidence_validator.py` | Acts as the factual gate after retrieval |
| `explanation_generator.py` | Converts validated facts into concise fixed templates |
| `output_writer.py` | Enforces header order, formatting, quoting, sorting, and strict reparse |
| `evaluation.py` | Measures anomaly and evidence behavior independently |
| `reproducibility.py` | Compares full precision decisions and complete CSV hashes |
| `cost_tracker.py` | Reports real model usage rather than estimating nonexistent calls |

## Fifteen likely interview questions and answers

### 1. Why is weekly cost calculated as a ratio of sums?

Shipments have different quantities and distances. A mean of row-level ratios gives
small shipments the same influence as large ones. Dividing total cost by total
tonne-km gives the correct exposure-weighted rate.

### 2. How do you prove there is no look-ahead leakage?

The route series is sorted by week and shifted by one row before rolling. Tests
change a future value by several orders of magnitude and confirm earlier baselines
do not move.

### 3. Why use eight available observations rather than eight calendar weeks?

That is the exact case requirement. If a route has missing calendar weeks, the last
eight observations remain the defined baseline. The current dataset happens to
contain all 104 weeks for every route.

### 4. Why require a positive own-history change for a peer anomaly?

The task asks for cost increases. A route can be above peers because it is
structurally expensive while its own cost is falling. Requiring `vs_own_history > 0`
keeps the verdict aligned with a positive increase.

### 5. Why choose 20%?

The brief intentionally leaves the threshold open. Twenty percent captures the
provided +21.0% and +23.6% peer examples, isolates a manageable tail of 19 out of
728 observations, and is easy to explain. It remains a configuration parameter.

### 6. Why not use a z-score or isolation forest?

With only 104 points per route and known comparison definitions, a threshold is
more transparent and reproducible. A robust statistical model could be evaluated
later, but it should not obscure the graded baselines.

### 7. Is TF-IDF really AI or RAG?

It is a lightweight information-retrieval component: notes are vectorized, a query
is embedded in the same sparse space, and cosine similarity ranks context. The
retrieved text is then grounded by deterministic validation before generation.

### 8. Why is retrieval score not enough to justify a route?

Similarity does not prove scope, timing, direction of cost impact, or absence of a
contradiction. A semantically close note saying costs were unaffected must be
rejected.

### 9. How are temporary events handled?

Explicit dates win. Phrases such as `festival week` or `about a week` receive a
seven-day interval. Ambiguous dated events are limited to their dated week. The
system does not carry temporary disruptions forward indefinitely.

### 10. Why does N001 justify two weekly rows?

Its explicit Feb 24-Mar 8 interval overlaps the weeks beginning Feb 24 and Mar 3.
The second weekly bucket contains six event days. The week beginning Mar 10 has no
overlap.

### 11. Why can N003 not explain Mumbai-Pune's peer-only divergence?

N003 is nationwide, so the same-week Short peer is exposed to the diesel change as
well. It also states roughly 5-7%, while the route's unusual signal is more than
20% versus its peer. Treating N003 as full justification would overclaim the note.

### 12. What happens when there are no peers?

The peer baseline and percentage remain missing. The system can still flag on a
valid historical comparison; it never invents a peer value.

### 13. How do you guarantee deterministic output?

There is no randomness. Rows use stable mergesort ordering, TF-IDF ties break on
note ID, explanations are templates, and CSV formatting is fixed. Three complete
runs produced the same bytes and hash.

### 14. What would you change for production?

Add schema/version monitoring, calibrated thresholds by route segment, persistent
lineage, alert deduplication, human-review feedback, drift metrics, and a governed
note-ingestion process. I would keep calculations and final evidence gates outside
the LLM.

### 15. If an LLM were added, where would it belong?

Only after the deterministic verdict, to rewrite an already validated explanation
or answer questions from the computed table and approved note. It must not change
numbers, anomaly status, matched note ID, or justification status. Its temperature,
tokens, calls, model price, and cost would be logged.

