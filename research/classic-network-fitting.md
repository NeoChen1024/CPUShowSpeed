# Sparse joint calibration of individual classical benchmarks

Computed and reviewed: 2026-09-27. This is an implemented **new experimental
model**, alongside the earlier fixed-composite multiplier fits. It does not
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

Each informative normalized hardware model gets total weight one; its weight
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

The inputs are existing normalized classical records, SPEC records and candidate
pairings, plus reviewed DEC source vectors and the approved candidate extension
table. A single interpretable classical metric is sufficient for an anchor
association; the old two-family intersection is not required.

Same-column DEC vectors are kept as configuration nodes. Other unanchored
classical co-observations are grouped by normalized model, reported clock and
explicit FPU-option labels. This is candidate grouping, not proof of identical
compiler, cache, memory or OS. Their full source records are exported. Known
classical processor counts other than one and archive SPEC rate processor
counts other than one retain the prior eligibility policy. Unknown same-column
DEC concurrency is not invented as one.

An observation already used in an anchored/89 candidate node is not reused as
an additional standalone unanchored training observation. Repeated published
records remain distinct; repeated enumeration of the same node/metric/source ID
is not a new observation. Alias closure across existing candidate links ensures
all uses of a source observation share a model holdout group. A data check found
zero source observation IDs split across model folds.

Two scenarios are run:

- `reported_clock`: reject known frequency conflicts; retain unknown clocks as
  explicitly unscaled candidates.
- `linear_clock`: for Dhrystone and Whetstone, use
  `score_at_target = original_score * target_clock / measured_clock` only when
  the existing model candidate also has a recognized compatible CPU identity.
  Unknown clocks stay unscaled; unresolved CPU identities cannot authorize a
  frequency-conflict conversion. LINPACK is never clock-scaled.

Frequency normalization applies only to existing SPEC-target associations. An
unanchored historical measurement stays at its actual reported frequency; it is
not scaled again when multiplying by its final coefficient. Same CPU model is
necessary but does not establish equal cache, memory or compiler behavior.

### Source checks that constrained scaling

The initial model-only candidates included SPARCstation 2 with a Weitek upgrade
at 80 MHz versus the original CY7C601 configuration at 40 MHz, and PA-RISC 7100
at 33 MHz versus 7100LC at 100 MHz. These are processor changes, so their 0.5×
and 3.03× adjustments are rejected on identity evidence, not residual magnitude.
Original scores remain intact.

The final run applies non-unit scaling to **25 candidate metric links from 13
source rows**, with factors **0.6–1.3333**. The linear scenario excludes 11
metric links for CPU identity conflict, 29 for unverified identity and two for
unscaled clock conflict. Eligibility and factors are recorded in `clock-audit.csv`.

A separate conditional same-label frequency check finds **7 Dhrystone comparisons
on 4 model keys**, but no Whetstone sweep. For HP 9000/715, matching PA-RISC7100,
HP-UX 9.0 and reference-5 source labels, 33→50 MHz linear predictions differ
from the observed score ratios by +0.686% (1.1) and −0.362% (2.1). This is limited
support, not proof for every architecture. Missing software/configuration fields
still prevent exact equivalence claims. Whetstone linearity remains an assumed
sensitivity rule in this dataset. Full rows/qualifications are in
[frequency-checks](data/classic/network-frequency-checks.csv).

## Calibration, uncertainty and holdouts

Both clock scenarios are fitted with rate targets only and with the additional
SPEC89 estimated targets. The two-edge SPEC89 bridge is recomputed under the
same alias grouping and excluded-model rule. An `anchored_only` log-regression
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

Both scenarios identify all six coefficients. The rate-only network has 457
informative model groups; the SPEC89-enabled network has 467. These include
unanchored co-observations constraining relative scales and are **not** hundreds
of measured SPEC anchor machines. The linear/SPEC89 run has 75 observed-rate
nodes, 77 inferred-89 nodes and 1,165 unanchored nodes; one-metric unanchored
nodes do not influence training.

For `linear_clock / with_spec89`:

| Input metric | Score unit | VAXen coefficient k | Conditional factor CI95 |
| --- | --- | ---: | --- |
| Dhrystone 1.1 | DMIPS | 0.64719 | 0.58877–0.71321 |
| Dhrystone 2.1 | DMIPS | 0.68518 | 0.62304–0.75547 |
| Whetstone native | MWIPS | 0.54200 | 0.43686–0.65032 |
| Whetstone SP | MWIPS | 0.52698 | 0.46131–0.59137 |
| Whetstone DP | MWIPS | 0.96013 | 0.78858–1.13601 |
| LINPACK n=100 | MFLOPS | 4.07990 | 3.56991–4.63690 |

For example, a Dhrystone **1.1** score of **10 DMIPS** maps to approximately
6.4719 VAXen using this experimental coefficient. Raw Dhrystones/second first
need the declared /1757 DMIPS conversion; coefficients must not be applied to
uninterpreted KIPS or printed unit labels with unresolved meaning.

On the common 19-model, 51-node observed-rate holdout cohort:

| Available inputs | Network P95, linear/SPEC89 |
| --- | ---: |
| Dhrystone 1.1 only | 25.43% |
| Dhrystone 2.1 only | 31.97% |
| Whetstone SP only | 37.93% |
| Whetstone DP only | 47.11% |
| LINPACK only | 54.20% |
| Dhrystone + Whetstone families | 23.74% |
| Dhrystone + LINPACK families | 38.29% |
| Whetstone + LINPACK families | 33.83% |
| All available measurements | 31.19% |

More available workloads do not guarantee a lower error against this integer-rate
population. All combinations remain; the table is not a residual-based selection
rule. Joint coverage and uncertainty remain explicit research objectives.

The network emits full-availability estimates for **1,165 unanchored candidate
nodes on 1,116 normalized model keys**. Of these, 1,119 nodes have one benchmark
family, 12 have two and 34 have three. They are not 1,165 newly verified machines:
configuration identity and source interpretation still need source-specific
review. Their estimates are stored separately from observed SPEC targets.

## Predict from new measurements

The [classical prediction CLI](../docs/classical-prediction.md) accepts any
nonempty subset and uses joint coefficient draws to estimate peak SPEC92 rate
and VAXen with conditional CI95. It does not refit the experiment per request.

## Reproduce and artifacts

```sh
UV_CACHE_DIR=/tmp/uv-cache OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/cpushowspeed-mpl \
  uv run --no-sync cpushowspeed classic network-fit
```

Inputs and resampling can be selected with `--input-root`, `--source-root`,
`--native-bridge`, `--linpack-text`, `--bootstrap`, `--seed` and `--output`.
The default output is `data/derived/classic/network-fit/`.

- `coefficients.csv`: per-benchmark coefficients, units, cohort/scenario and CI95.
- `nodes.csv`, `observations.csv`: original/adjusted values, source identities,
  qualified matching, target kind and whether an observation enters its node summary.
- `clock-audit.csv`, `frequency-checks.csv`: every frequency decision and the
  independent conditional frequency-sweep check.
- `summary.csv`, `predictions.csv`, `fold-coverage.csv`: model-held-out masked
  evaluations; observed and inferred targets remain distinct.
- `hardware-estimates.csv`: single, family, pair and available-input estimates
  with conditional calibration intervals, never labelled measured rate scores.
- `coefficient-log-draws.npz`: correlated coefficient samples for combining inputs.
- `availability-comparison.png/.svg`: joint/control errors on complete-family nodes.
- `prediction-calibration.json`: hash-bound coefficient/draw bundle, with ordered metric columns for the predictor.
- `audit.json`: input hashes, source/code dependency hashes, counts and assumptions.

Compact coefficients, summary, frequency checks and audit are retained under
`research/data/classic/network-*`. Bulk evidence/predictions/estimates remain
reproducible derived products. Tests cover known analytic coefficients from an
unanchored bridge, disconnected metrics, shared bridge covariance, family/variant
weights, single/partial prediction, held-out bridge exclusion and CPU-upgrade
rejection. The full suite passes **111 tests**.
