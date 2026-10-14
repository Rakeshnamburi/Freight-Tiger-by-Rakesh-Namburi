# Reproducibility Report

## Procedure

The full pipeline was executed three times in fresh temporary output locations.
Each run reloaded the unchanged CSV inputs, rebuilt TF-IDF, recalculated every
route-week, retrieved evidence, validated notes, generated explanations, and wrote
a new standards-compliant CSV.

## Results

| Run | SHA-256 of complete CSV |
|---:|---|
| 1 | `444675348b190483531f6fb53aae8ce9fac3d5d8ca221eafd2b4c7946167dca5` |
| 2 | `444675348b190483531f6fb53aae8ce9fac3d5d8ca221eafd2b4c7946167dca5` |
| 3 | `444675348b190483531f6fb53aae8ce9fac3d5d8ca221eafd2b4c7946167dca5` |

- Full-precision numerical columns identical: **TRUE**
- Flags, verdict inputs, and matched note IDs identical: **TRUE**
- Complete CSV byte hashes identical: **TRUE**
- Overall reproducibility check: **PASS**

No randomness or generative model is used. TF-IDF ranking has deterministic tie
breaking by note ID, and all output rows use a stable route/date sort.
