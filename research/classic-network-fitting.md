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

Of the 487 target/classical pairings, 48 are same-result, 132 clock-compatible,
263 clock-unknown, 6 clock-conflicting and 21 reference-definition targets;
reviews reject 14 and accept 3 unscaled (see
[pair review](#pair-review-and-spelling-merges-2026-10-02)). Under `linear_clock`,
two conflicts are scaled and four stay excluded because the processors do not
resolve to one entity: processor changes such as PA-RISC 7100 versus 7150 or
R4400 versus R10000 can no longer authorize scaling. The two scaled pairings are one Netlib Dhrystone row for the
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

Both scenarios identify all six coefficients. The rate-only network has 468
informative systems; the SPEC89-enabled network has 486. These include
unanchored co-observations constraining relative scales and are **not** hundreds
of measured SPEC anchor machines. The SPEC89-enabled run has 74 observed-rate
nodes, 107 inferred-89 nodes and 1,151 unanchored nodes; one-metric unanchored
nodes do not influence training.

For `linear_clock / with_spec89`:

| Input metric | Score unit | VAXen coefficient k | Conditional factor CI95 |
| --- | --- | ---: | --- |
| Dhrystone 1.1 | DMIPS | 0.63251 | 0.58505–0.68527 |
| Dhrystone 2.1 | DMIPS | 0.67856 | 0.62928–0.73304 |
| Whetstone native | MWIPS | 0.52517 | 0.42479–0.62905 |
| Whetstone SP | MWIPS | 0.50084 | 0.42453–0.57576 |
| Whetstone DP | MWIPS | 0.92958 | 0.76675–1.09691 |
| LINPACK n=100 | MFLOPS | 3.01985 | 2.62306–3.50192 |

For example, a Dhrystone **1.1** score of **10 DMIPS** maps to approximately
6.325 VAXen using this experimental coefficient. Raw Dhrystones/second first
need the declared /1757 DMIPS conversion; coefficients must not be applied to
uninterpreted KIPS or printed unit labels with unresolved meaning.

On the common 20-system, 59-node observed-rate holdout cohort with all three
families (`linear_clock / with_spec89`):

| Available inputs | Network P95 | Anchored-only control P95 |
| --- | ---: | ---: |
| Dhrystone 1.1 only | 21.75% | 18.92% |
| Dhrystone 2.1 only | 37.00% | 29.48% |
| Whetstone SP only (19 systems) | 39.45% | 27.54% |
| Whetstone DP only | 57.72% | 48.11% |
| LINPACK only | 23.27% | 25.76% |
| Dhrystone + Whetstone families | 17.54% | 16.86% |
| Dhrystone + LINPACK families | 15.59% | 17.47% |
| Whetstone + LINPACK families | 18.07% | 12.36% |
| All available measurements | 15.06% | 14.36% |

More available workloads do not guarantee a lower error, and the unanchored
coupling does not uniformly beat the anchored-only control on this population.
All combinations remain; the table is not a residual-based selection rule.

The network emits full-availability estimates for **1,151 unanchored nodes on
1,102 system keys** (an unresolved result counts as its own key). Of these, 1,116
nodes have one benchmark family, 14 have two and 21 have three. They are not
1,151 newly verified machines: configuration identity and source interpretation
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

### Pair review and spelling merges (2026-10-02)

Two curated changes reached the network. Exact-text
[catalogue spelling aliases](chronology.md#catalogue-spelling-aliases-2026-10-02)
merged duplicate systems (34 fewer system IDs), so IBM RS/6000 "RISC Sys/6000-NNN"
and "Model NNN" rows, HP9000/J200 and others now pair with SPEC results of the
same model. Five classical↔SPEC `result_pair` reviews reject the upgraded
SPARCstation 2 Dhrystone rows and accept two clock-convention pairs unscaled
(details in the [SPEC89 bridge](spec89-rate-bridge.md#pair-review-and-spelling-merges-2026-10-02)).

Nearly all of the change comes from the merges; the reviews move coefficients by
at most 0.13%. With SPEC89 targets, coefficients fall 4–6% and LINPACK 19.6%
(`linear_clock / with_spec89` 3.756 → 3.020). The inferred-89 nodes grew from 80
to 107, among them three RS/6000 systems with high LINPACK relative to
SPECint89. Rate-only coefficients rise 1.7–10.3%. On the all-node observed-rate holdout, the
SPEC89-enabled network improves (P95 48.0% → 42.5%; LINPACK only 53.2% → 27.9%),
but its agreement with the inferred SPEC89 targets worsens (P95 73.9% → 129.8%;
33 → 47 models),
while the rate-only network worsens (39.2% → 49.1%) because it gains the
HP 9000/J200 (29 observed-rate models), which it underpredicts by 67% (anchored-only
control: 70%). Its two
LINPACK rows are 38 MFLOPS (`+O3`) and 5.5 MFLOPS (`fort77 -o`) for the same
machine; both are source values and both remain.

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
