# Direct classical composites to speed-VAXen

Computed and reviewed: 2026-09-27. Recomputed on resolved systems: 2026-10-02.
Re-anchored to speed-VAXen: 2026-10-03 (method `classic-direct-speed-composites-v3-resolved-systems`).

## Target

The classical fitting target is **SPECint92 speed** in speed-VAXen, with base
(`SPECbase_int92`) and peak (`SPECint92`) fitted separately. VAX-11/780 is the
SPEC92 reference machine, so one SPECint92 point is one speed-VAXen and the
target needs no conversion; see the [integer-speed chain](spec-speed-chain.md).
By the 2026-10-03 decision, historical routes are anchored to the single-job
quantity; rate-VAXen is a separate, parallel quantity with its own chain.
SPECint89 targets are examined in the [SPEC89 bridge experiment](spec89-bridge.md),
which keeps this direct fit as its control.

For each declared pair or triple of distinct classical benchmark families:

`C = exp(mean(log(component score / component unit)))`

`estimated speed-VAXen = k × C`.

Units are 1 DMIPS, 1 MWIPS and 1 MFLOPS. Dhrystone versions, Whetstone
native/SP/DP and LINPACK n=100 remain explicit. No environmental correction,
learned component weights, residual-based exclusion or clock scaling is used.

## Inputs and observation handling

The command reads the built database (`data build`). A target is any result
reporting SPECint92 or SPECbase_int92: CPU92 disclosures, the reviewed DEC
N3909 report columns and the SPEC89/92 bridge table. Classical scores pair with
it in two cohorts:

- `same_result`: classical scores and the target come from one source row or
  report column (in practice DEC N3909 columns).
- `same_system` (primary): additionally, every classical result resolving to the
  same `system_id`. Names are never compared. Reported clocks must agree within
  1% when both are known; an unknown clock is kept and labelled; no clock scaling.

Speed is one job, so a target's processor count does not exclude it (rate
targets excluded counts other than one). Classical results reporting more than
one CPU, and reference-definition targets, are excluded. Pairing over a
resolved system records, but does not establish, equal OS, compiler, cache or
FPU configuration.

Each metric's value for a target is the median over its accepted pairings, so
repeated classical rows of one system produce one tuple per target result. A
triple needs all three families paired with the same target. No missing
benchmark is imputed. `member_ids` lists the classical results behind each component.

## Estimation and evaluation

A "model" in the statistics below is a resolved system (`system_id`). Each
system's median `log(y/C)` is computed over all its observations; the
exponential mean of system centers gives k. Every system has equal fit weight.
The conditional factor CI95 uses 10,000 system-cluster bootstrap draws with
seed 20260926.

Leave-one-model-out excludes all observations of the test system from fitting.
Single-component baselines use the same tuple multiset and folds as their
composite. The main P95 statistic is the interpolated 95th percentile of the
absolute model-center percentage errors; the maximum within-model observation
P95 is also retained. The shaded CI95 is not a prediction interval for an old
machine. Source selection, configuration mismatch, shared lineage and earlier
architecture extrapolation are not covered by the bootstrap.

There are 2,326 tuples across both cohorts and all combinations, and 194
composite/baseline comparison rows, including insufficient-model cases. These
are not counts of independent benchmark runs. Peak targets cover 99 results on
46 systems (`same_system`); base targets 32 results on 14 systems.

## Main results (`same_system`)

### Peak

| Composite | Systems / tuples | k | Factor CI95 | LOMO model-center P95 |
| --- | ---: | ---: | --- | ---: |
| Dhrystone 1.1 + LINPACK | 43 / 96 | 1.43491 | 1.35285–1.51799 | 40.51% |
| Dhrystone 2.1 + LINPACK | 44 / 97 | 1.46589 | 1.37281–1.56579 | 44.26% |
| Whetstone DP + LINPACK | 34 / 79 | 1.67217 | 1.59938–1.74613 | 27.26% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 33 / 78 | 1.20697 | 1.16535–1.24744 | 22.16% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 33 / 78 | 1.23738 | 1.18868–1.28518 | 25.24% |

### Base

| Composite | Systems / tuples | k | Factor CI95 | LOMO model-center P95 |
| --- | ---: | ---: | --- | ---: |
| Dhrystone 1.1 + LINPACK | 14 / 32 | 1.39423 | 1.33866–1.45294 | 13.64% |
| Dhrystone 2.1 + LINPACK | 14 / 32 | 1.40611 | 1.34634–1.46906 | 15.92% |
| Whetstone DP + LINPACK | 13 / 31 | 1.51546 | 1.46194–1.56930 | 13.07% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 13 / 31 | 1.11684 | 1.07485–1.15880 | 13.64% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 13 / 31 | 1.12121 | 1.07519–1.16670 | 14.15% |

The `same_result` cohort covers 62 peak targets on 38 systems; for example
Dhrystone 1.1 + LINPACK gives 1.36335 (P95 28.20%) and the Dhrystone 1.1 +
Whetstone DP + LINPACK triple 1.13282 (32 systems, P95 20.29%).

The [full summary](data/classic/composite-summary.csv) includes all 17
combinations per variant in the main cohort, with native/SP Whetstone and every
single-component baseline. No combination was removed because its error was
high. These tables do not select a universal winning estimator.

For the 33-system peak Dhrystone 1.1/DP/LINPACK triple cohort, single
Dhrystone, Whetstone and LINPACK P95 values are 21.49%, 30.38% and 44.42%,
versus 22.16% for the composite: on this cohort the composite does not beat
Dhrystone alone. Its maximum within-system observation P95 is 55.46%.

Base's smaller errors do not establish that base is intrinsically more
predictable: its source and hardware cohorts differ from peak. Pair and triple
rows above are not controlled same-machine comparisons; the matched
single-score comparisons are controlled at the tuple/fold level.

## Changes

### Rate target to speed target (2026-10-03)

The target changed from SPEC92 integer rate in rate-VAXen to SPECint92 speed.
More results report SPECint92 than one-processor rate, so the peak cohort grows
from 25 to 43 systems for Dhrystone 1.1 + LINPACK and from 20 to 33 for the
Dhrystone 1.1 + DP + LINPACK triple; base grows from 13 to 14.

| Composite | Rate target systems / k / P95 | Speed target systems / k / P95 |
| --- | --- | --- |
| Peak Dhrystone 1.1 + LINPACK | 25 / 1.36746 / 28.19% | 43 / 1.43491 / 40.51% |
| Peak Whetstone DP + LINPACK | 20 / 1.64569 / 13.06% | 34 / 1.67217 / 27.26% |
| Peak Dhrystone 1.1 + DP + LINPACK | 20 / 1.20101 / 12.84% | 33 / 1.20697 / 22.16% |
| Base Dhrystone 1.1 + LINPACK | 13 / 1.39757 / 13.19% | 14 / 1.39423 / 13.64% |
| Base Whetstone DP + LINPACK | 13 / 1.54715 / 13.29% | 13 / 1.51546 / 13.07% |

The higher peak P95 is measured on a different and larger set of systems, so
it is not a like-for-like deterioration. The added targets include the SPEC89
bridge table's RS/6000 results, whose LINPACK is high relative to integer speed.

### Changes from the name-matched fit (2026-10-02)

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
MPLCONFIGDIR=/tmp/cpushowspeed-mpl .venv/bin/cpushowspeed classic composite-fit
```

`--database`, `--output`, `--research-dir`, `--bootstrap` and `--seed` select the
built database, output locations and bootstrap settings. Run `data build` first.

Outputs under `data/derived/classic/composite-fit/`:

- `observations.csv`: one row per target result, metric, cohort and pattern, with
  member classical result IDs and values, pairing status and speed-VAXen target.
- `summary.csv` and `predictions.csv`: all factors, conditional CI95, error
  diagnostics and individual system-held-out predictions.
- `target-coverage.csv`: target results and systems per cohort and variant.
- `composite-base.png/.svg`, `composite-peak.png/.svg`: all primary
  combinations and factor CI95 shading.

Compact summary, coverage and audit (database input digest, seed, pairing rule)
are retained in `research/data/classic/composite-*`. Bulk observations,
predictions and figures remain derived.

Validation: synthetic tests (`tests/test_classical_fit.py`) check known base/peak
factors, that rate values never become targets, cohort/pattern counts,
exclusion of clock-conflicting siblings and identical baseline tuples; pairing
rules are tested in `tests/test_classical_store.py`.
