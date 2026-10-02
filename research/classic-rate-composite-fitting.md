# Direct classical composites to SPEC92 integer-rate VAXen

Computed and reviewed: 2026-09-27. Recomputed on resolved systems: 2026-10-02
(method `classic-direct-rate-composites-v2-resolved-systems`).

## Selected primary target

The primary classical fitting target is now **SPEC92 integer rate**, with base
and peak fitted separately. This direct-control run excludes SPECint89: the preceding native-score
experiment added seven models to the Dhrystone/LINPACK combinations and none
to its three-family DP/SP combinations, and did not establish a rate bridge.
A subsequent [two-edge SPEC89 bridge experiment](spec89-rate-bridge.md) now
examines inferred SPEC89 targets jointly with this direct cohort; it retains
this rate-only model as the control and distinguishes estimates from observations.

For a reported CPU92 integer-rate score R, the target is
`y_VAXen = R × 25500 / 604800`, applied once when the target is read.
Base and peak share the normalization constant but not a fitted coefficient.
See the [rate anchor definition](spec95-spec2026-rate-fitting.md#vax-reference-throughput-scale).

For each declared pair or triple of distinct classical benchmark families:

`C = exp(mean(log(component score / component unit)))`

`estimated SPEC92 integer-rate VAXen = k × C`.

Units are 1 DMIPS, 1 MWIPS and 1 MFLOPS. Dhrystone versions, Whetstone
native/SP/DP and LINPACK n=100 remain explicit. No environmental correction,
learned component weights, residual-based exclusion or clock scaling is used.

## Inputs and observation handling

The command reads the built database (`data build`). A target is any result
reporting CPU92 integer rate: the Netlib and manufacturer CPU92 rate results and
the reviewed DEC N3909 report columns. Classical scores pair with it in two cohorts:

- `same_result`: classical scores and the rate value come from one source row or
  report column (in practice the 24 DEC columns with a peak rate).
- `same_system` (primary): additionally, every classical result resolving to the
  same `system_id`. Names are never compared. Reported clocks must agree within
  1% when both are known; an unknown clock is kept and labelled; no clock scaling.

The rate value is dropped when a CPU count other than one is reported; the DEC
columns report none and keep their qualification that active CPU/copy counts are
unverified. Classical results reporting more than one CPU, and reference-definition
targets, are excluded. Thus the experiment estimates an association with observed
system throughput, not a verified intrinsic per-core performance coefficient.
Pairing over a resolved system records, but does not establish, equal OS,
compiler, cache or FPU configuration; those pairs are not yet individually reviewed.

Each metric's value for a target is the median over its accepted pairings, so
repeated classical rows of one system produce one tuple per target result rather
than one per row combination. A triple needs all three families paired with the
same target. No missing benchmark is imputed. `member_ids` lists the classical
results behind each component.

## Estimation and evaluation

A "model" in the statistics below is a resolved system (`system_id`). Each
system's median `log(y/C)` is computed over all its observations; the
exponential mean of system centers gives k. Every system has equal fit weight.
The conditional factor CI95 uses 10,000 system-cluster bootstrap draws with
seed 20260926. There is no fitted
generation bridge or extra bridge uncertainty in this direct rate experiment.

Leave-one-model-out excludes all observations of the test model from fitting.
Single-component baselines use the same tuple multiset and folds as their
composite. The main P95 statistic is the interpolated 95th percentile of the
absolute model-center percentage errors. The maximum within-model observation
P95 is also retained. These error summaries and the coefficient CI95 have
different meanings; the shaded CI95 is not a prediction interval for an old
machine. Source selection, configuration mismatch, shared lineage and earlier
architecture extrapolation are not covered by the bootstrap.

There are 1,474 tuples across both cohorts and all component combinations,
and 154 composite/baseline comparison rows, including insufficient-model cases.
These are not counts of independent benchmark runs.

## Main results (`same_system`)

### Peak

| Composite | Systems / tuples | k | Factor CI95 | LOMO model-center P95 |
| --- | ---: | ---: | --- | ---: |
| Dhrystone 1.1 + LINPACK | 25 / 70 | 1.36746 | 1.28679–1.44478 | 28.19% |
| Dhrystone 2.1 + LINPACK | 25 / 70 | 1.38349 | 1.30554–1.46218 | 29.87% |
| Whetstone DP + LINPACK | 20 / 59 | 1.64569 | 1.59004–1.69594 | 13.06% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 20 / 59 | 1.20101 | 1.15708–1.24165 | 12.84% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 20 / 59 | 1.20626 | 1.15945–1.24994 | 15.87% |

### Base

| Composite | Systems / tuples | k | Factor CI95 | LOMO model-center P95 |
| --- | ---: | ---: | --- | ---: |
| Dhrystone 1.1 + LINPACK | 13 / 14 | 1.39757 | 1.34348–1.45506 | 13.19% |
| Dhrystone 2.1 + LINPACK | 13 / 14 | 1.40660 | 1.35301–1.45910 | 11.69% |
| Whetstone DP + LINPACK | 13 / 14 | 1.54715 | 1.49019–1.60393 | 13.29% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 13 / 14 | 1.13879 | 1.09264–1.18468 | 13.88% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 13 / 14 | 1.14369 | 1.09531–1.18933 | 14.39% |

The `same_result` cohort has peak targets only (24 DEC columns); it reproduces
the former `within_source` stage exactly (for example Dhrystone 1.1 + LINPACK
1.23970 on 24 models, Whetstone DP + LINPACK 1.43035 on 18).

The [full summary](data/classic/rate-composite-summary.csv) includes all 17
available combinations per variant in the main cohort, including native/SP
Whetstone and every single-component baseline. No combination was removed
because its error was high. These tables emphasize the previously discussed
DP combinations; they do not select a universal winning estimator.

For the exact 20-system peak Dhrystone 1.1/DP/LINPACK triple cohort, single
Dhrystone, Whetstone and LINPACK P95 values are 24.17%, 41.01% and 22.93%,
respectively, versus 12.84% for the composite. Equal averaging does not always
beat the best individual workload (compare other patterns in the summary). Its
maximum within-system observation P95 is 55.76%, larger than the system-center
statistic.

Base's smaller errors here do not establish that base is intrinsically more
predictable: its source and hardware cohorts differ from peak. Likewise,
comparisons between pair and triple rows above are not controlled
same-machine comparisons. The matched single-score comparisons are controlled
at the tuple/fold level.

## Changes from the name-matched fit (2026-10-02)

The earlier run (2026-09-27) paired targets by normalized model name through
`classic prepare-sources`, with its main cohort `plus_cross_source_unscaled`.
Pairing by resolved system changes the cross-source cohort:

| Peak/base composite | Name-matched models / k | Resolved systems / k |
| --- | --- | --- |
| Peak Dhrystone 1.1 + LINPACK | 25 / 1.32644 | 25 / 1.36746 |
| Peak Whetstone DP + LINPACK | 20 / 1.57766 | 20 / 1.64569 |
| Peak Dhrystone 1.1 + DP + LINPACK | 19 / 1.14543 | 20 / 1.20101 |
| Base Dhrystone 1.1 + LINPACK | 10 / 1.41754 | 13 / 1.39757 |
| Base Whetstone DP + LINPACK | 11 / 1.58366 | 13 / 1.54715 |

The same-column cohort is unchanged. Repeated classical rows now enter as one
median per target and metric instead of one tuple per row pair, so tuple counts
fall (peak D1.1+L 74 → 70) while system counts are equal or larger. These are
pairing-policy changes, not new measurements; the cross-source pairs await review.

## Reproduction, outputs and checks

```sh
MPLCONFIGDIR=/tmp/cpushowspeed-mpl .venv/bin/cpushowspeed classic rate-composite-fit
```

`--database`, `--output`, `--research-dir`, `--bootstrap` and `--seed` select the
built database, output locations and bootstrap settings. Run `data build` first.

Outputs under `data/derived/classic/rate-composite-fit/`:

- `observations.csv`: one row per target result, metric, cohort and pattern, with
  member classical result IDs and values, pairing status and VAXen target.
- `summary.csv` and `predictions.csv`: all factors, conditional CI95, error
  diagnostics and individual system-held-out predictions in VAXen.
- `target-coverage.csv`: target results and systems per cohort and variant.
- `rate-composite-base.png/.svg`, `rate-composite-peak.png/.svg`: all primary
  combinations and factor CI95 shading.

Compact summary, coverage and audit (database input digest, seed, pairing rule)
are retained in `research/data/classic/rate-composite-*`. Bulk observations,
predictions and figures remain derived. These are exploratory classical
coefficients on the modern rate-chain unit scale.

Validation: the `same_result` cohort reproduced every former `within_source`
factor, CI95 endpoint and P95. Synthetic tests (`tests/test_classical_fit.py`)
check known base/peak factors, single normalization, cohort/pattern counts,
exclusion of clock-conflicting siblings and identical baseline tuples; pairing
rules are tested in `tests/test_classical_store.py`.
