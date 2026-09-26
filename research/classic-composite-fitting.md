# Equal-weight classical composite: held-out comparison

Review date: 2026-09-26. Follow-up to the
[complete-vector audit](classic-composite-overlap.md). The implementation fixes
three weights at 1/3 and fits only an overall multiplier. All single-benchmark
baselines use precisely the same candidate tuples and leave out the same whole
model at each fold. These are exploratory results; configurations remain
unverified and the active VAXen conversion chain is unchanged.

## SPEC92 integer-rate peak

Values below are **leave-one-model-out P95 absolute percentage errors on model
centers**, not prediction intervals. Each column compares identical tuples
across predictors. Both clock scenarios permit unknown LINPACK/SPEC clocks.

| Predictor | No adjustment, 4 models / 11 tuples | Clock sensitivity, 5 models / 14 tuples |
| --- | ---: | ---: |
| Equal weights, native Whetstone | 12.57% | 11.73% |
| Equal weights, DP Whetstone | 13.25% | 12.26% |
| Dhrystone 1.1 alone | 16.25% | 15.82% |
| Whetstone native alone | 20.85% | 19.77% |
| Whetstone DP alone | 23.33% | 21.82% |
| LINPACK n=100 alone | **7.24%** | **7.45%** |

Thus equal weighting reduces this error relative to Dhrystone or Whetstone,
but not LINPACK, within this small DEC cohort. This does not establish LINPACK
as a generally better predictor of integer performance. Intersecting available
scores selects a much narrower population than the previous single-benchmark
fits; compare against these matched-cohort baselines, not previous broad-cohort
error percentages. No residual-based record removal was applied.

For the clock-sensitivity scenario, native composite k is **1.17634** with
conditional bootstrap CI95 **1.11683–1.21971**; DP k is **1.22663** with CI95
**1.16302–1.27489**. These coefficients apply to the fixed unit-normalized
composite index defined in [methods](../docs/methods.md#fixed-equal-weight-composite-validation).
They are not VAX reference definitions or validated historical conversions.

The median held-out model error is 4.73% (native composite), 5.46% (DP), and
3.02% (LINPACK). However, the maximum across models of each model's held-out
**tuple-level P95** is 38.70% (native composite) and 39.20% (DP). Model-center
summaries hide some source/submission spread; neither 11.73% nor 12.26% should
be advertised as a universal per-machine error bound.

The added fifth model is DEC 7000/610. The four-model and five-model experiments
have different populations, so the modest composite error decrease is not
isolated evidence that clock normalization improves accuracy.

## Other targets and empty cohorts

The command emits 120 target / Whetstone / clock / predictor combinations,
including explicit insufficient-model results, and 104 usable model folds.
All-known-clock cohorts are empty. SPECint89 and SPECfp89 remain empty after
excluding reference-definition records. SPECmark89 and SPEC92 base have two
models only in the clock-sensitivity scenario. Their statistics are recorded,
but two-group fits and bootstrap intervals are too fragile for transfer claims.
SPEC89 scores remain in their original units, separately from SPEC92 rate.

## Reproduction and outputs

```sh
uv run cpushowspeed classic composite-overlap
uv run cpushowspeed classic composite-fit
```

Default bootstrap: 10,000 model resamples, seed 20260926. Under
`data/derived/classic/composite-fit/`:

- `summary.csv`: coefficients, conditional CI95 and held-out error summaries.
- `folds.csv`: every held-out model and training-only coefficient.
- `predictions.csv`: every held-out tuple, observed/predicted values and original
  source IDs; join to the input vectors for URLs, locators and raw records.
- `heldout-errors.png` / `.svg`: per-model peak errors for the four comparisons.
- `audit.json`: input, code and output CSV hashes, fixed weights and seed.

Compact checked snapshots: [summary](data/classic/composite-fit-summary.csv),
[folds](data/classic/composite-fit-folds.csv),
[audit](data/classic/composite-fit-audit.json).
Tests verify geometric-mean arithmetic, identical folds for every predictor,
manual held-out error arithmetic, and that changing a held-out model's outcome
does not alter its training coefficient. Existing parser/source checks remain
in the overlap and individual-fitting tests. Plot layout was inspected.
