# Direct classical composites to speed-VAXen

Computed and reviewed: 2026-09-27. Recomputed on resolved systems: 2026-10-02.
Re-anchored to speed-VAXen: 2026-10-03. Power laws through the VAX-11/780: 2026-10-03
(method `classic-direct-speed-composites-v4-power-law-vax780`).

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

`log(estimated speed-VAXen) = b × (log C − log C₇₈₀)`,

so the VAX-11/780, scoring C₇₈₀, is one speed-VAXen for any exponent b. C₇₈₀ is
the same composite of the 780's own measured scores: each metric's median over
the 780's distinct classical runs, as in the
[network anchor](classic-network-fitting.md); a single-component baseline uses
that metric's anchor alone. One exponent b is fitted per cohort, variant,
combination and predictor.

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

A "model" in the statistics below is a resolved system (`system_id`). The
exponent is the anchored least-squares slope with every system weighing 1 and
each of its observations 1/n: `b = Σ w·dx·log y / Σ w·dx²`, where
`dx = log C − log C₇₈₀`. The conditional exponent CI95 uses 10,000
system-cluster bootstrap draws with seed 20260926; each draw also redraws the
780's log anchors from a normal distribution with the network's run-spread
standard error. `free_loglog_slope_diagnostic` is the unanchored slope of system
medians, reported only as a check on the anchored exponent.

Leave-one-model-out excludes all observations of the test system from fitting
the exponent; the anchor stays fixed.
Single-component baselines use the same tuple multiset and folds as their
composite. The main P95 statistic is the interpolated 95th percentile of the
absolute model-center percentage errors; the model-balanced observation P95
and the maximum within-model observation P95 are also retained. The shaded
CI95 (exponent and anchor draws) is not a prediction interval for an old
machine. Source selection, configuration mismatch, shared lineage and earlier
architecture extrapolation are not covered by the bootstrap.

There are 2,332 tuples across both cohorts and all combinations, and 194
composite/baseline comparison rows, including insufficient-model cases. These
are not counts of independent benchmark runs. Peak targets cover 98 results on
45 systems (`same_system`); base targets 31 results on 13 systems.

## Main results (`same_system`)

### Peak

| Composite | Systems / tuples | C₇₈₀ | Exponent b | Exponent CI95 | LOMO model-center P95 |
| --- | ---: | ---: | ---: | --- | ---: |
| Dhrystone 1.1 + LINPACK | 42 / 95 | 0.3507 | 0.8506 | 0.8222–0.8817 | 34.61% |
| Dhrystone 2.1 + LINPACK | 43 / 96 | 0.3419 | 0.8484 | 0.8128–0.8871 | 31.63% |
| Whetstone DP + LINPACK | 35 / 80 | 0.3164 | 0.8610 | 0.8056–0.9240 | 20.95% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 34 / 79 | 0.4447 | 0.8646 | 0.8250–0.9074 | 21.10% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 34 / 79 | 0.4372 | 0.8652 | 0.8240–0.9119 | 19.15% |

### Base

| Composite | Systems / tuples | Exponent b | Exponent CI95 | LOMO model-center P95 |
| --- | ---: | ---: | --- | ---: |
| Dhrystone 1.1 + LINPACK | 13 / 31 | 0.8607 | 0.8352–0.8883 | 16.94% |
| Dhrystone 2.1 + LINPACK | 13 / 31 | 0.8576 | 0.8266–0.8916 | 13.80% |
| Whetstone DP + LINPACK | 13 / 31 | 0.8593 | 0.8106–0.9145 | 15.30% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 13 / 31 | 0.8649 | 0.8299–0.9029 | 15.70% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 13 / 31 | 0.8627 | 0.8263–0.9037 | 15.63% |

The `same_result` cohort covers 62 peak targets on 38 systems; for example
Dhrystone 1.1 + LINPACK gives b 0.8478 (P95 20.78%) and the Dhrystone 1.1 +
Whetstone DP + LINPACK triple 0.8571 (32 systems, P95 17.35%).

Every fitted exponent lies between 0.85 and 0.92, below one: a proportional
factor fitted to fast systems overstates slow ones. The anchored exponents sit
below the unanchored free slopes (for example 0.8646 against 0.956 for the peak
Dhrystone 1.1 + DP + LINPACK triple), so the 780 lies above the free line
extrapolated from 1990s systems. This is the same era effect the
[network report](classic-network-fitting.md) lists as a limitation.

The [full summary](data/classic/composite-summary.csv) includes all 17
combinations per variant in the main cohort, with native/SP Whetstone and every
single-component baseline. No combination was removed because its error was
high. These tables do not select a universal winning estimator.

For the 34-system peak Dhrystone 1.1/DP/LINPACK triple cohort, single
Dhrystone, Whetstone and LINPACK P95 values are 25.70%, 26.09% and 25.89%,
versus 21.10% for the composite. Its maximum within-system observation P95 is
42.45%.

Base's smaller errors do not establish that base is intrinsically more
predictable: its source and hardware cohorts differ from peak. Pair and triple
rows above are not controlled same-machine comparisons; the matched
single-score comparisons are controlled at the tuple/fold level.

## Changes

### Power laws through the VAX-11/780 (2026-10-03)

The proportional factor `y = k × C` is replaced by the anchored power law above,
matching the [network](classic-network-fitting.md). Tuples and cohorts are
unchanged; all 194 comparison rows are fitted. Across the 114 `same_system`
rows with a holdout P95 in both versions, the median P95 is 22.7% → 22.6% (65
lower); across the 80 `same_result` rows, 22.0% → 19.4% (55 lower).

| Peak composite (`same_system`) | k / P95, proportional | b / P95, power law |
| --- | --- | --- |
| Dhrystone 1.1 + LINPACK | 1.42549 / 39.91% | 0.8506 / 34.61% |
| Dhrystone 2.1 + LINPACK | 1.45531 / 43.54% | 0.8484 / 31.63% |
| Whetstone DP + LINPACK | 1.68628 / 28.27% | 0.8610 / 20.95% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 1.21596 / 23.10% | 0.8646 / 21.10% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 1.24659 / 26.12% | 0.8652 / 19.15% |

Base is worse: the Dhrystone 1.1 + LINPACK P95 rises 11.62% → 16.94% and the
triple 13.64% → 15.70%. The 13 base systems span a narrow range far from the
780, so one anchored exponent cannot also match their local slope (free slopes
1.00–1.06). For the peak triple cohort, the single-component baselines change from
22.02%, 30.27% and 46.16% (Dhrystone, Whetstone, LINPACK) to 25.70%, 26.09% and
25.89%, so the composite now beats each one.

### HP 9000/720 1996 pairing rejected (2026-10-03)

The HP 9000/720 SPECint92 disclosure (tested January 1996, HP-UX B.10.01, C
A.10.11) is no longer paired with the 1991-era SSBA and Netlib classical results
of the same machine: same hardware, five years of compiler gains on the SPEC side
only (user decision). Tuples fall 2,356 → 2,332 and the system leaves every
SPECint92 cohort. The Dhrystone 1.1 + DP + LINPACK triple returns to 34 systems,
k 1.23696 → 1.21596 and P95 27.61% → 23.10% (peak); base patterns return to 13
systems with P95 11–14% (Dhrystone 1.1 + LINPACK 19.65% → 11.62%).

### Smaller Usenet result posts (2026-10-03)

The [SSBA and Nefzger posts](usenet-result-lists.md#smaller-result-posts-19901991)
add Dhrystone 1.1, Whetstone DP and LINPACK results for the HP 9000/720 and
SPARCstation 2, which have SPECint92 targets with matching clocks. Tuples rise
2,326 → 2,356. The Whetstone DP patterns gain both systems in peak (for example
the Dhrystone 1.1 + DP + LINPACK triple 33 → 35 systems) and the HP 9000/720 in
base (13 → 14). Peak k for that triple 1.20697 → 1.23696 and P95 22.16% →
27.61%; base Whetstone DP + LINPACK 1.51546 → 1.57110, P95 13.07% → 25.67%.
The base Dhrystone + LINPACK patterns keep 14 systems, but their P95 also rises
(13.64% → 19.65% for Dhrystone 1.1) with the same 32 tuples, because the HP
9000/720's same-system inputs now include the SSBA run. Most of the change comes from one pairing: the HP
9000/720's SPECint92 targets include a 1996 Netlib disclosure (peak 64.0, base
51.6) made with later compilers than the 1991 SSBA run (see the
[network report](classic-network-fitting.md#changes-from-the-smaller-usenet-result-posts-2026-10-03)).
`same_result` rows are unchanged.


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
