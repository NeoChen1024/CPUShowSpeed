# Sparse joint calibration of individual classical benchmarks

Computed and reviewed: 2026-09-27; recomputed on resolved systems 2026-10-02
(method `sparse-family-balanced-log-network-v2-resolved-systems`). This is an
implemented **new experimental model**, alongside the earlier fixed-composite multiplier fits. It does not
replace measured rate observations or the production SPEC rate converter.

## Objective and model

Estimate a separate coefficient for Dhrystone 1.1, Dhrystone 2.1, Whetstone
native precision, Whetstone SP, Whetstone DP and LINPACK n=100. A machine with
one available measurement can then obtain an estimate; multiple measurements
combine on the log scale with equal family weight. Native Whetstone is not
silently renamed SP.

For configuration node i and benchmark b, let `s_ib = ln(score_ib)` and
`alpha_b = ln(k_b)`. Each node has a common log-throughput `theta_i`. Minimize:

`sum_i sum_b w_ib * (s_ib + alpha_b - theta_i)^2`.

- Observed SPEC92 peak rate fixes theta to `ln(rate * 25500 / 604800)`.
- In the SPEC89-enabled cohort, theta for an 89 node is the original log
  SPECint89 plus the fitted two-edge bridge log multiplier.
- A node without a target has a free theta, eliminated analytically as its
  weighted mean of `s + alpha`. Co-observations therefore constrain relative
  benchmark coefficients without inventing measured SPEC values.
- A component disconnected from all anchored metrics gets no coefficient.
  Unanchored one-metric nodes provide no calibration information; once their
  metric is identified elsewhere, they can still receive predictions.

This remains `V_b = k_b * score_b` for each benchmark: there is no intercept in
ordinary score space. Unlike the previous separate composite fits, this uses
**joint weighted least squares in log space**, not a single model-median
log-ratio coefficient. Within each node/metric, source runs first contribute a
median log score. All original observations remain in the export.

Each informative resolved system ("model" below) gets total weight one; its weight
is split equally across informative configuration nodes, then across available
families, then across versions/precision variants in a family. Dhrystone 1.1
and 2.1 do not create two family votes. Whetstone native/SP/DP share one family
vote. Source frequency and configuration ambiguity remain visible.

For a target with available metrics A:

`ln(estimated VAXen) = sum_b w_b * (ln(score_b) + alpha_b)`,

where weights sum to one, balancing families first. With one benchmark this
reduces to `k_b * score_b`. With a missing or unidentifiable metric, a partial
single/subset result can be reported, but it is not labelled a full-availability
prediction. Factor draws are combined jointly when calculating estimate CI95.

## Input construction and clock assumption

The command reads the built database. Anchored nodes are target results: CPU92
integer-rate results (Netlib, manufacturer and the reviewed DEC report columns)
and, in the SPEC89-enabled cohort, SPECint89 results. A target's classical
scores come from its own result (DEC columns) and from every classical result
resolving to the same `system_id`; names are never compared. A single
interpretable classical metric is enough for an anchor association.

Classical results not attached to any target become unanchored nodes, grouped by
resolved system (or the result itself when unresolved), reported clock and
explicit FPU-option labels. This grouping does not prove identical compiler,
cache, memory or OS. Classical results reporting more than one CPU, rate values
with a reported CPU count other than one, and reference-definition targets are
excluded. Unknown same-column DEC concurrency is not invented as one. A result
already attached to a target is not reused as an unanchored node. Holdout groups
and bootstrap clusters are resolved systems, so all uses of one result share a fold.

Two scenarios are run:

- `reported_clock`: reject known frequency conflicts (more than 1%); retain
  unknown clocks as explicitly unscaled candidates.
- `linear_clock`: for Dhrystone and Whetstone, use
  `score_at_target = original_score * target_clock / measured_clock` only when
  both results resolve to the same processor entity. Unknown clocks stay
  unscaled; a conflict without one resolved processor stays excluded
  (`clock_conflict_processor_unverified`). LINPACK is never clock-scaled.

Frequency normalization applies only to target associations. An unanchored
historical measurement stays at its actual reported frequency. Same processor is
necessary but does not establish equal cache, memory or compiler behavior.

### Clock decisions

Of the target/classical pairings, 48 are same-result, 109 clock-compatible,
246 clock-unknown, 14 clock-conflicting and 21 reference-definition targets.
Under `linear_clock`, two conflicts are scaled and twelve stay excluded because
the processors do not resolve to one entity: processor changes such as a
SPARCstation 2 Weitek upgrade or PA-RISC 7100 versus 7100LC can no longer
authorize scaling. The two scaled pairings are one Netlib Dhrystone row for the
DEC 7000/610 at 182 MHz carried to two 200 MHz CPU92 rate results (factor 1.0989,
four metric links). The two scenarios therefore differ by at most 0.03% in any
coefficient. Every decision is recorded in `clock-audit.csv`.

The earlier name-matched run scaled 25 metric links from 13 source rows with
factors 0.6–1.3333. Most of those pairs relied on clock-suffixed model names or
CPU-text identity checks that resolved-system pairing does not reproduce.

A separate conditional same-label frequency check finds **7 Dhrystone comparisons
on 4 systems**, but no Whetstone sweep. For HP 9000/715, matching PA-RISC7100,
HP-UX 9.0 and reference-5 source labels, 33→50 MHz linear predictions differ
from the observed score ratios by +0.68% (1.1) and −0.36% (2.1). This is limited
support, not proof for every architecture. Missing software/configuration fields
still prevent exact equivalence claims. Whetstone linearity remains an assumed
sensitivity rule in this dataset. Full rows/qualifications are in
[frequency-checks](data/classic/network-frequency-checks.csv).

## Calibration, uncertainty and holdouts

Both clock scenarios are fitted with rate targets only and with the additional
SPEC89 estimated targets. The two-edge SPEC89 bridge is recomputed with the
same system grouping and excluded-system rule. An `anchored_only` log-regression
control uses the same anchor population but omits unanchored coupling; it is
not identical to the previous pair/triple model with a different cohort.

10,000 bootstrap draws, seed 20260927, resample model groups jointly across the
network and bridge edges. A shared model gets the same draw weight everywhere.
Each draw refits both bridge factors and the network coefficients; rank-deficient
draws are rejected and valid counts exported. CI95 is the linear percentile
interval of coefficients or final VAXen estimates, not a prediction interval.
It omits source bias, matching mistakes, within-model measurement uncertainty,
unknown architecture transport error and uncertainty in the fixed clock exponent.

All observations of each test model are removed from network training and from
both bridge edges. Availability masks test each individual benchmark, each
single family, each two-family subset and all available measurements. Observed
rate errors are separate from agreement with inferred SPEC89 targets. The
primary statistic is the shared model-center relative-error P95.

`complete_family_nodes` restricts comparisons to the same nodes containing all
three families. Precision-specific single-benchmark masks can still have smaller
coverage (native Whetstone has seven models, unlike the 19-model DP/SP cohort);
counts accompany every row. Missing held-out coefficients and evaluated subset
counts are recorded in `fold-coverage.csv`, not silently scored as success.

## Results

Both scenarios identify all six coefficients. The rate-only network has 466
informative systems; the SPEC89-enabled network has 475. These include
unanchored co-observations constraining relative scales and are **not** hundreds
of measured SPEC anchor machines. The SPEC89-enabled run has 73 observed-rate
nodes, 80 inferred-89 nodes and 1,172 unanchored nodes; one-metric unanchored
nodes do not influence training.

For `linear_clock / with_spec89`:

| Input metric | Score unit | VAXen coefficient k | Conditional factor CI95 |
| --- | --- | ---: | --- |
| Dhrystone 1.1 | DMIPS | 0.65970 | 0.60694–0.71935 |
| Dhrystone 2.1 | DMIPS | 0.70850 | 0.65607–0.76996 |
| Whetstone native | MWIPS | 0.55661 | 0.45215–0.66058 |
| Whetstone SP | MWIPS | 0.52290 | 0.44663–0.59725 |
| Whetstone DP | MWIPS | 0.97946 | 0.80867–1.15050 |
| LINPACK n=100 | MFLOPS | 3.75630 | 3.32136–4.22859 |

For example, a Dhrystone **1.1** score of **10 DMIPS** maps to approximately
6.597 VAXen using this experimental coefficient. Raw Dhrystones/second first
need the declared /1757 DMIPS conversion; coefficients must not be applied to
uninterpreted KIPS or printed unit labels with unresolved meaning.

On the common 20-system, 59-node observed-rate holdout cohort with all three
families (`linear_clock / with_spec89`):

| Available inputs | Network P95 | Anchored-only control P95 |
| --- | ---: | ---: |
| Dhrystone 1.1 only | 27.15% | 18.76% |
| Dhrystone 2.1 only | 43.26% | 32.02% |
| Whetstone SP only (19 systems) | 36.70% | 27.54% |
| Whetstone DP only | 66.35% | 47.44% |
| LINPACK only | 39.30% | 37.19% |
| Dhrystone + Whetstone families | 21.19% | 17.26% |
| Dhrystone + LINPACK families | 31.98% | 26.07% |
| Whetstone + LINPACK families | 16.15% | 20.07% |
| All available measurements | 14.74% | 15.42% |

More available workloads do not guarantee a lower error, and the unanchored
coupling does not uniformly beat the anchored-only control on this population.
All combinations remain; the table is not a residual-based selection rule.

The network emits full-availability estimates for **1,172 unanchored nodes on
1,130 system keys** (an unresolved result counts as its own key). Of these, 1,139
nodes have one benchmark family, 12 have two and 21 have three. They are not
1,172 newly verified machines: configuration identity and source interpretation
still need source-specific review. Their estimates are stored separately from
observed SPEC targets.

### Changes from the name-matched run (2026-10-02)

Coefficients moved by −8% to +4% (for example `reported_clock / rate_only`
LINPACK 3.595 → 3.326, Dhrystone 1.1 0.635 → 0.614; `linear_clock /
with_spec89` LINPACK 4.080 → 3.756, Dhrystone 1.1 0.647 → 0.660). Informative
groups rose from 457/467 to 466/475. Anchored rate systems fell from 32 to 28
because names no longer link archive rate results to classical rows of other
configurations, while SPEC89 anchors grew as in the
[SPEC89 bridge](spec89-rate-bridge.md#changes-from-the-name-matched-run-2026-10-02).
The all-available observed-rate holdout P95 improved (for example
`reported_clock / rate_only` anchored-only 50.7% → 33.6%). Cohorts differ, so
the improvement is not a controlled comparison.

## Predict from new measurements

The [classical prediction CLI](../docs/classical-prediction.md) accepts any
nonempty subset and uses joint coefficient draws to estimate peak SPEC92 rate
and VAXen with conditional CI95. It does not refit the experiment per request.

## Reproduce and artifacts

```sh
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/cpushowspeed-mpl .venv/bin/cpushowspeed classic network-fit
```

Options `--database`, `--output`, `--research-dir`, `--bootstrap` and `--seed`
select the built database, outputs and resampling. The default output is
`data/derived/classic/network-fit/`.

- `coefficients.csv`: per-benchmark coefficients, units, cohort/scenario and CI95.
- `nodes.csv`, `observations.csv`: original/adjusted values, classical result
  IDs, pairing status, target kind and whether an observation enters its node summary.
- `clock-audit.csv`, `frequency-checks.csv`: every target/classical pairing
  decision and the conditional frequency-sweep check.
- `summary.csv`, `predictions.csv`, `fold-coverage.csv`: system-held-out masked
  evaluations; observed and inferred targets remain distinct.
- `hardware-estimates.csv`: single, family, pair and available-input estimates
  with conditional calibration intervals, never labelled measured rate scores.
- `coefficient-log-draws.npz`: correlated coefficient samples for combining inputs.
- `availability-comparison.png/.svg`: joint/control errors on complete-family nodes.
- `prediction-calibration.json`: hash-bound coefficient/draw bundle, with ordered metric columns for the predictor.

Compact coefficients, summary, frequency checks and audit (database input
digest, counts and assumptions) are retained under
`research/data/classic/network-*`. Tests cover known analytic coefficients from
an unanchored bridge, disconnected metrics, shared bridge covariance,
family/variant weights, single/partial prediction, held-out bridge exclusion and
processor-change rejection (`tests/test_classic_network.py`,
`tests/test_classical_store.py`).
