# Direct classical composites to SPEC92 integer-rate VAXen

Computed and reviewed: 2026-09-27.

## Selected primary target

The primary classical fitting target is now **SPEC92 integer rate**, with base
and peak fitted separately. This direct-control run excludes SPECint89: the preceding native-score
experiment added seven models to the Dhrystone/LINPACK combinations and none
to its three-family DP/SP combinations, and did not establish a rate bridge.
A subsequent [two-edge SPEC89 bridge experiment](spec89-rate-bridge.md) now
examines inferred SPEC89 targets jointly with this direct cohort; it retains
this rate-only model as the control and distinguishes estimates from observations.
The [native integer experiment](classic-pooled-fitting.md) remains auxiliary
research; its coefficients are not substituted into the rate chain.

For a reported CPU92 integer-rate score R, the target is
`y_VAXen = R × 25500 / 604800`. This defined normalization is already present in
the source-pair input's `y` field; this command does **not** apply it again.
Base and peak share the normalization constant but not a fitted coefficient.
See the [rate anchor definition](spec95-spec2026-rate-fitting.md#vax-reference-throughput-scale).

For each declared pair or triple of distinct classical benchmark families:

`C = exp(mean(log(component score / component unit)))`

`estimated SPEC92 integer-rate VAXen = k × C`.

Units are 1 DMIPS, 1 MWIPS and 1 MFLOPS. Dhrystone versions, Whetstone
native/SP/DP and LINPACK n=100 remain explicit. No environmental correction,
learned component weights, residual-based exclusion or clock scaling is used.

## Inputs and observation handling

The main cohort is `plus_cross_source_unscaled` from
[source-column experiments](classic-source-pair-fitting.md). `within_source`
is also recomputed as a source-composition comparison. All existing repeat
observations and eligibility rules are preserved. In particular, archive rate
matches require one reported CPU, while same-column DEC configurations retain
unknown active CPU/copy counts and their explicit qualification. Thus the
experiment estimates an association with observed system throughput, not a
verified intrinsic per-core performance coefficient.

Pairs retain all input rows. A triple requires all three compatible pair edges
for the same model, SPEC target record, source cohort and exact classical
observation IDs/values. Multiple ways to traverse those edges do not create
additional copies of the same triple. No missing benchmark is imputed.

For a triple, `member_ids` and `member_values` are authoritative; obsolete
first/second component fields are omitted. `provenance` retains all supporting
pair evidence. The original input file and its checksum remain unchanged.

## Estimation and evaluation

Each model's median `log(y/C)` is computed over all its observations; the
exponential mean of model centers gives k. Every model has equal fit weight.
The conditional factor CI95 uses 10,000 model-cluster bootstrap draws with
seed 20260926, matching the existing source-pair experiment. There is no fitted
generation bridge or extra bridge uncertainty in this direct rate experiment.

Leave-one-model-out excludes all observations of the test model from fitting.
Single-component baselines use the same tuple multiset and folds as their
composite. The main P95 statistic is the interpolated 95th percentile of the
absolute model-center percentage errors. The maximum within-model observation
P95 is also retained. These error summaries and the coefficient CI95 have
different meanings; the shaded CI95 is not a prediction interval for an old
machine. Source selection, configuration mismatch, shared lineage and earlier
architecture extrapolation are not covered by the bootstrap.

There are 1,418 tuples across both stages and all component combinations,
and 154 composite/baseline comparison rows, including insufficient-model cases.
These are not counts of independent benchmark runs.

## Main unscaled results

### Peak

| Composite | Models / tuples | k | Factor CI95 | LOMO model-center P95 |
| --- | ---: | ---: | --- | ---: |
| Dhrystone 1.1 + LINPACK | 25 / 74 | 1.32644 | 1.25181–1.40435 | 24.78% |
| Dhrystone 2.1 + LINPACK | 25 / 75 | 1.35087 | 1.27831–1.42548 | 27.45% |
| Whetstone DP + LINPACK | 20 / 66 | 1.57766 | 1.50643–1.64653 | 21.01% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 19 / 60 | 1.14543 | 1.08769–1.20344 | 20.08% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 19 / 62 | 1.15602 | 1.09781–1.21359 | 21.13% |

### Base

| Composite | Models / tuples | k | Factor CI95 | LOMO model-center P95 |
| --- | ---: | ---: | --- | ---: |
| Dhrystone 1.1 + LINPACK | 10 / 11 | 1.41754 | 1.35574–1.48011 | 15.34% |
| Dhrystone 2.1 + LINPACK | 10 / 12 | 1.42227 | 1.36527–1.47500 | 14.60% |
| Whetstone DP + LINPACK | 11 / 17 | 1.58366 | 1.52755–1.63831 | 11.40% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 9 / 11 | 1.15376 | 1.09701–1.20863 | 16.02% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 9 / 13 | 1.15692 | 1.10363–1.20493 | 15.40% |

The [full summary](data/classic/rate-composite-summary.csv) includes all 17
available combinations per variant in the main cohort, including native/SP
Whetstone and every single-component baseline. No combination was removed
because its error was high. These tables emphasize the previously discussed
DP combinations; they do not select a universal winning estimator.

For the exact 19-model peak Dhrystone 1.1/DP/LINPACK triple cohort, single
Dhrystone, Whetstone and LINPACK P95 values are 24.21%, 19.20% and 36.88%,
respectively, versus 20.08% for the composite. Equal averaging does not always
beat the best individual workload. Its maximum within-model observation P95
is 49.24%, larger than the model-center statistic.

Base's smaller errors here do not establish that base is intrinsically more
predictable: its source and hardware cohorts differ from peak. Likewise,
comparisons between pair and triple rows above are not controlled
same-machine comparisons. The matched single-score comparisons are controlled
at the tuple/fold level.

## Reproduction, outputs and checks

```sh
UV_CACHE_DIR=/tmp/uv-cache MPLCONFIGDIR=/tmp/cpushowspeed-mpl \
  uv run --no-sync cpushowspeed classic rate-composite-fit
```

`--pairs`, `--output`, `--bootstrap` and `--seed` select the source-pair input,
output location and bootstrap settings. Rebuild `classic source-pair-fit` first
if its derived input is missing.

Outputs under `data/derived/classic/rate-composite-fit/`:

- `observations.csv`: component identities/values, normalized target, exact
  metric/variant, source provenance and configuration qualifications.
  `rate_score_reconstructed_from_input` reverses normalization for inspection;
  it is labelled reconstructed, not a replacement for the reported source cell.
- `summary.csv` and `predictions.csv`: all factors, conditional CI95, error
  diagnostics and individual model-held-out predictions in VAXen.
- `target-coverage.csv`: all input metrics and explicit rate-only selection.
- `rate-composite-base.png/.svg`, `rate-composite-peak.png/.svg`: all primary
  combinations, source-cohort colors and factor CI95 shading.
- `audit.json`: input/code hashes, normalization, stage rules and random seed.

Compact summary, coverage and audit snapshots are retained in
`research/data/classic/rate-composite-*`. Bulk observations, predictions and
figures remain derived. Existing modern rate-chain coefficients and the
production conversion CLI are unchanged; these are exploratory classical
coefficients on the same unit scale.

Validation: all **30 overlapping pair/composite fits** reproduced the existing
source-pair point factors, CI95 endpoints and P95 errors to relative tolerance
1e-12. Synthetic tests independently check known rate factors, no double
normalization, base/peak separation, exclusion of ordinary SPECint89/92, complete
triple assembly and identical baseline cohorts. The full suite passed **91 tests**.
