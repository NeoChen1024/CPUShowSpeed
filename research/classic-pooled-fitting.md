# Pooled SPECint89/92 classical fitting

Computed and reviewed: 2026-09-26.

Status updated 2026-09-27: auxiliary native-score experiment. The primary
classical target is now [direct SPEC92 integer rate](classic-rate-composite-fitting.md);
these native-score coefficients do not enter the rate conversion chain.

## Decision and target

This experiment applies the selected fixed, equal-weight geometric composite
method to pooled **SPECint89 and SPECint92** observations. No environment
correction, fitted component weights, residual-based removal or clock scaling
is applied. Dhrystone 1.1/2.1 and Whetstone native/SP/DP remain separate variants;
LINPACK is n=100. Two- and three-family formulas have separate coefficients.

The result is **SPECint92-equivalent native integer score**, not the project's
production integer-rate VAXen. The historical claim of near agreement concerns
SPECint89/92, not SPECrate. SPECmark89, SPECfp, SPECbase_int92 and rate scores
are retained in the input and enumerated in `target-coverage.csv`, but cannot
be pooled under that particular bridge. Existing [rate results](classic-source-pair-fitting.md)
remain a separate comparison. This experiment does not change the rate CLI.

## Bridge verification

The [source-paired bridge](data/spec89/v2.0.0/csv/bridges89_92.csv) contains
17 integer pairs on 15 normalized model keys. All 17 rows remain, including
republications and development-level systems. Within-model median log ratios,
followed by the mean across model centers, give:

`SPECint92-equivalent = 0.9603866300 × SPECint89`.

The bridge-only model-bootstrap CI95 is 0.943012–0.979396.

Reported ratios span 0.892655–1.056140; **16/17 rows**, rather than all rows,
fall within 10% of equality. The remaining row is about 10.73% below equality.
The source observations and qualifications are preserved in `bridge-evidence.csv`.
This is a recomputation of the existing checked snapshot, not a new independent
verification of every original publication. See the [original evidence review](spec89-cpu92-scatter.md).

## Cohorts, fitting and uncertainty

Inputs are the `plus_cross_source_unscaled` stage of the existing source-pair
experiment. It combines DEC source-column observations and qualifying archive
pairs; uncertain configurations and shared-source lineage retain their previous
qualifications. Unknown clocks remain unknown. No missing score is imputed.

For each exact benchmark combination, `x` is the geometric mean of scores in
DMIPS, MWIPS and/or MFLOPS. Each model contributes the median of its observation
log ratios `log(y/x)`; `k` is the exponential of the mean of these model centers.
All repeated observations stay in the dataset. Model weighting prevents a
frequently reported machine from dominating simply through its row count.

A three-family vector is built only when all three pair edges exist for the
same target record, source cohort, model, and identical classical observation
IDs and values. A triangle is emitted once per unique triple of observations;
multiple pair edges are not additional independent triple runs.

Seven comparisons are emitted per pattern and predictor: pooled aligned,
pooled 1:1, 89-only, 92-only, and three common-model comparisons. Single-score
baselines use the exact same observations and held-out models as their composite.
There are 15 patterns, 803 tuples (not independent benchmark runs), and 343
comparison rows including insufficient-sample cases.

Factor CI95 uses 10,000 joint model-cluster bootstrap draws, seed 20260926.
Bridge and fitting observations of a shared model receive the same resampling
weight. Each draw recomputes the bridge and uses one common multiplier for all
SPEC89 observations, then recomputes model medians and the final factor. Empty
bridge/fitting draws are rejected and the valid count is recorded. The intervals
are conditional on source selection, model matching and unit policy; they do
not cover unidentified shared lineage or bias from missing historical systems.

Leave-one-model-out (LOMO) removes the model from both the fitting and bridge
training sets. Each held-out SPEC89 target is aligned with that fold's bridge.
Reported P95 is the interpolated 95th percentile of absolute model-center errors.
The maximum of within-model observation-error P95 values is recorded separately.
Neither is a prediction interval, and neither equals the factor CI95.

## Results

| Composite | Models 89 + 92 | Tuples | k | Joint factor CI95 | LOMO model-center P95 |
| --- | ---: | ---: | ---: | --- | ---: |
| Dhrystone 1.1 + LINPACK | 7 + 38 | 148 | 1.3973 | 1.3188–1.4837 | 36.61% |
| Dhrystone 2.1 + LINPACK | 7 + 38 | 151 | 1.4550 | 1.3669–1.5520 | 35.41% |
| Whetstone DP + LINPACK | 1 + 32 | 56 | 1.6250 | 1.5295–1.7448 | 29.38% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 0 + 32 | 48 | 1.1328 | 1.0891–1.1785 | 20.29% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 0 + 32 | 48 | 1.1634 | 1.1105–1.2206 | 22.83% |

The full [summary](data/classic/pooled-summary.csv) includes all native/SP/DP
variants and all single-component baselines; the table is not a selection rule.
For Dhrystone 1.1 + LINPACK, using a 1:1 bridge changes k to 1.4061 (**+0.63%**)
and P95 to 38.09%. For Dhrystone 2.1 + LINPACK, k becomes 1.4642 (+0.63%) and
P95 becomes 37.33%. Thus the small 89/92 scale adjustment has less effect here
than the observed classical-workload scatter.

For Dhrystone 1.1 + LINPACK, 89-only k is 1.5971 and P95 57.83%; 92-only k is
1.3634 and P95 28.20%. However, **none of the patterns has a model represented
in both target generations in this classical intersection**. The common-model
comparisons correctly report insufficient samples. These differences confound
generation, hardware and source composition; they cannot identify a generation
effect. The 15 bridge machines are a separate cohort and do not resolve this.

The three-family rows have no SPECint89 contributions. Their lower P95 therefore
does not establish that adding a third benchmark improves historical cross-era
coverage. On its exact 32-model cohort, Dhrystone 1.1 alone gives P95 20.76%,
Whetstone DP 25.97%, and LINPACK 41.56%, versus 20.29% for the triple.
On the 45-model Dhrystone 1.1 + LINPACK cohort, Dhrystone alone gives 29.62%,
better than the composite's 36.61%. Equal weighting is not uniformly superior.
The composite's maximum within-model observation P95 is 64.65%, substantially
larger than its model-center P95; individual historical estimates remain rough.

## Reproduce and artifacts

```sh
UV_CACHE_DIR=/tmp/uv-cache MPLCONFIGDIR=/tmp/cpushowspeed-mpl \
  uv run --no-sync cpushowspeed classic pooled-fit
```

Run `classic source-pair-fit` first if its derived inputs are absent. CLI options
select input pairs, bridge table, output directory, bootstrap count and seed.
Output directory: `data/derived/classic/pooled-fit/`.

- `observations.csv`: original target, generation, source IDs, component values,
  geometric mean and source provenance; the reported target is never overwritten.
- `bridge-evidence.csv`, `target-coverage.csv`: retained bridge records and metric selection.
- `summary.csv`, `predictions.csv`: factors, joint intervals, all comparison statuses
  and individual held-out outcomes with training bridge factors.
- `pooled-scatter.png` / `.svg`: all patterns, generation-colored observations;
  gray bands are factor CI95. One-model patterns show observations without a fit.
- `audit.json`: source/code hashes, seed, bridge coverage and metric boundary.

Compact summaries, target coverage, bridge evidence and audit are tracked under
`research/data/classic/pooled-*`; bulk tuples, predictions and figures are derived.
Tests check known constant factors, shared bridge uncertainty, held-out exclusion,
and the requirement for complete compatible triple edges. The rendered scatter
was inspected for labels, interval bands and insufficient-model panels.
