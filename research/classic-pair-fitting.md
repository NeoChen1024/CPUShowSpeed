# Two-of-three classical benchmark validation

Review date: 2026-09-26. This extends the
[three-family experiment](classic-composite-fitting.md) by requiring only two
**distinct benchmark families**. Dhrystone versions remain separate; two
Dhrystone versions alone do not satisfy the two-family requirement.

## Coverage and SPEC92 peak results

The clock-sensitivity scenario retains SPEC92's one-reported-CPU filter and
normalizes Dhrystone/Whetstone only. Missing LINPACK/SPEC clocks remain unknown.
Native/DP and 1.1/2.1 form eight experiments, not interchangeable input fields.
The union covers ten normalized SPEC92 peak model groups. Each experiment uses
all qualifying two-score tuples; the third benchmark need not be present.

| Pair | Models / tuples | Equal-weight LOO P95 | First-only P95 | Second-only P95 |
| --- | ---: | ---: | ---: | ---: |
| Dhrystone 1.1 + Whetstone native | 6 / 28 | 41.21% | 35.74% | 46.29% |
| Dhrystone 1.1 + Whetstone DP | 6 / 28 | 36.38% | 35.74% | 36.96% |
| Dhrystone 2.1 + Whetstone native | 7 / 40 | 39.82% | 35.15% | 44.55% |
| Dhrystone 2.1 + Whetstone DP | 7 / 40 | 35.46% | 35.15% | 36.04% |
| Dhrystone 1.1 + LINPACK n=100 | 6 / 10 | 25.34% | 21.82% | 29.95% |
| Dhrystone 2.1 + LINPACK n=100 | 7 / 11 | 32.51% | 35.12% | 34.33% |
| Whetstone native + LINPACK n=100 | 8 / 17 | **9.07%** | 14.35% | 12.95% |
| Whetstone DP + LINPACK n=100 | 8 / 17 | **10.36%** | 16.81% | 12.95% |

Errors are leave-one-model-out absolute percentage errors on model-center
ratios, with interpolated P95 across models. Each row's three predictors use
identical observations and folds. Different rows may use different machines;
do not rank workload quality by directly comparing those rows. In particular,
the eight Whetstone/LINPACK models are all DEC, so the smaller errors do not
establish portability to other architectures or much older machines.

The two-family relaxation does help SPEC89 coverage: with clock normalization,
Dhrystone (either version) + LINPACK has twelve SPECmark89 model groups and
seven SPECint89 groups. SPEC92 base has two to five groups depending on pair.
Raw SPEC89 targets and SPEC92 rate-VAXen targets remain separate. No automatic
switch between pair formulas, pooled any-two composite, or new production
VAXen conversion is introduced.

## Dhrystone versions cannot simply be pooled

Using **same source row** measurements, the collected Dhrystone table provides
214 rows with both versions. Descriptive ratios `v1.1 / v2.1` are:

| Statistic | Ratio |
| --- | ---: |
| Geometric mean | 1.10252 |
| Median | 1.09816 |
| P5 / P95 | 0.93924 / 1.33571 |
| Minimum / maximum | 0.74501 / 1.65284 |

Only 104/214 rows fall within 10% of equality. These are row-level descriptive
statistics, not independent-model confidence intervals or an approved version
conversion. Flags and differing version-specific compiler options remain in
raw records; no starred results were silently removed.

[Netlib's original compilation](https://www.netlib.org/performance/papers/dhrystone/)
explains that both versions use the same 1757 denominator because unoptimized
results were similar, while collecting both exposes differences in how much
version 1.1 can be optimized. Sharing DMIPS normalization does not guarantee
interchangeability. The retrieved explanation corroborates the locally
preserved source table. Do not replace missing 1.1 by 2.1 or divide all 1.1
scores by this observed mean ratio without a separate validated method.

## Method and reproducibility

```sh
uv run cpushowspeed classic pair-fit
```

For each pair, fixed unit-normalized inputs define `C = sqrt(x1 × x2)`.
Only an overall multiplier is fitted; each single-score baseline fits its own
multiplier. Model medians of log score ratios, model-balanced geometric means,
10,000-resample conditional bootstrap intervals and leave-one-model-out
validation reuse the [existing method](../docs/methods.md#fixed-equal-weight-composite-validation).
The default seed is 20260926. All repetitions are retained as tuples; no extra
independent sample count is inferred from Cartesian products.

Three scenarios are recorded: all clocks known and compatible; missing clocks
allowed with known conflicts rejected; Dhrystone/Whetstone linear adjustment.
For the latter, the frequency source is SPEC, then LINPACK if present, then
Whetstone, then Dhrystone. Only present Dhrystone/Whetstone inputs require known
clocks for adjustment. LINPACK and SPEC scores are unchanged; known conflicts
between their clocks are rejected. Same-model matching, source configuration,
compiler and source dependence remain limitations. Changing scenarios can also
change the cohort, so score changes do not isolate the effect of scaling.

There are 360 experiment/predictor summaries including empty or single-model
cohorts. Outputs under `data/derived/classic/pair-fit/` retain:

- `pairs.csv`: original/adjusted values, factors, frequency source, citations,
  original records and all exclusion reasons for each complete pair.
- `summary.csv`, `folds.csv`, `predictions.csv`: fit/CI/error statistics and all
  held-out predictions with source IDs; empty cohorts have no fitted factor.
- `dhrystone-versions.csv`, `dhrystone-version-summary.json`: the version audit.
- `heldout-comparison.png` / `.svg`: peak P95 comparisons.
- `audit.json`: input/code/output CSV hashes and calculation settings.

Tracked snapshots: [fit summary](data/classic/pair-fit-summary.csv),
[version summary](data/classic/dhrystone-version-summary.json),
[audit](data/classic/pair-fit-audit.json). Full source rows remain reproducible
derived data. Tests cover absence of a third family, scaling arithmetic,
version separation, same-row version comparisons, held-out training leakage,
and matched baselines. The chart was visually inspected.
