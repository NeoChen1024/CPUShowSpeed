# Sparse joint calibration of individual classical benchmarks

Computed and reviewed: 2026-09-27; recomputed on resolved systems 2026-10-02;
re-anchored to speed-VAXen 2026-10-03 (method
`sparse-family-balanced-log-network-v3-speed-anchor`). This is an implemented
**experimental model**, alongside the fixed-composite multiplier fits. It does
not replace measured SPEC observations or the SPEC chains.

Its unit is **speed-VAXen**: one SPECint92 speed point, VAX-11/780 = 1 (see the
[integer-speed chain](spec-speed-chain.md)). By the 2026-10-03 decision the
historical routes are anchored to the single-job quantity; rate-VAXen is a
separate quantity and is not an anchor here.

## Objective and model

Estimate a separate coefficient for Dhrystone 1.1, Dhrystone 2.1, Whetstone
native precision, Whetstone SP, Whetstone DP and LINPACK n=100. A machine with
one available measurement can then obtain an estimate; multiple measurements
combine on the log scale with equal family weight. Native Whetstone is not
silently renamed SP.

For configuration node i and benchmark b, let `s_ib = ln(score_ib)` and
`alpha_b = ln(k_b)`. Each node has a common log-throughput `theta_i`. Minimize:

`sum_i sum_b w_ib * (s_ib + alpha_b - theta_i)^2`.

- Observed SPECint92 peak fixes theta to `ln(SPECint92)`.
- In the SPEC89-enabled cohort, theta for an 89 node is the original log
  SPECint89 plus the fitted int89_to_int92 bridge log multiplier.
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

`ln(estimated speed-VAXen) = sum_b w_b * (ln(score_b) + alpha_b)`,

where weights sum to one, balancing families first. With one benchmark this
reduces to `k_b * score_b`. With a missing or unidentifiable metric, a partial
single/subset result can be reported, but it is not labelled a full-availability
prediction. Factor draws are combined jointly when calculating estimate CI95.

## Input construction and clock assumption

The command reads the built database. Anchored nodes are target results
reporting SPECint92 peak (CPU92 disclosures, the reviewed DEC report columns and
the SPEC89/92 bridge table) and, in the SPEC89-enabled cohort, SPECint89 results. A target's classical
scores come from its own result (DEC columns) and from every classical result
resolving to the same `system_id`; names are never compared. A single
interpretable classical metric is enough for an anchor association.

Classical results not attached to any target become unanchored nodes, grouped by
resolved system (or the result itself when unresolved), reported clock and
explicit FPU-option labels. This grouping does not prove identical compiler,
cache, memory or OS. Classical results reporting more than one CPU and reference-definition targets
are excluded. A speed target is one job, so a multi-processor system's SPECint92
remains an anchor. A result
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

Of the 590 target/classical pairings, 62 are same-result, 146 clock-compatible,
322 clock-unknown, 18 clock-conflicting and 21 reference-definition targets;
reviews reject 14 and accept 7 unscaled (see
[pair review](#pair-review-and-spelling-merges-2026-10-02)). Under `linear_clock`,
one conflict is scaled and 17 stay excluded because the processors do not
resolve to one entity: processor changes such as PA-RISC 7100 versus 7150 or
R4400 versus R10000 cannot authorize scaling. The scaled pairing is one Netlib
Dhrystone row for the DEC 7000/610 at 182 MHz carried to a 200 MHz CPU92 result
(factor 1.0989, two metric links). The two scenarios therefore differ by at
most 0.01% in any coefficient. Every decision is recorded in `clock-audit.csv`.

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

Both clock scenarios are fitted with SPECint92 targets only (`spec92_only`) and
with the additional SPEC89 estimated targets (`with_spec89`). The SPEC89 bridge
is recomputed with the same system grouping and excluded-system rule. An `anchored_only` log-regression
control uses the same anchor population but omits unanchored coupling; it is
not identical to the previous pair/triple model with a different cohort.

10,000 bootstrap draws, seed 20260927, resample model groups jointly across the
network and bridge edges. A shared model gets the same draw weight everywhere.
Each draw refits the bridge factor and the network coefficients; rank-deficient
draws are rejected and valid counts exported. CI95 is the linear percentile
interval of coefficients or final VAXen estimates, not a prediction interval.
It omits source bias, matching mistakes, within-model measurement uncertainty,
unknown architecture transport error and uncertainty in the fixed clock exponent.

All observations of each test model are removed from network training and from
the bridge edge. Availability masks test each individual benchmark, each
single family, each two-family subset and all available measurements. Observed
SPECint92 errors are separate from agreement with inferred SPEC89 targets. The
primary statistic is the shared model-center relative-error P95.

`complete_family_nodes` restricts comparisons to the same nodes containing all
three families. Precision-specific single-benchmark masks can still have smaller
coverage (native Whetstone has eight models, unlike the 32–33-model DP/SP cohort);
counts accompany every row. Missing held-out coefficients and evaluated subset
counts are recorded in `fold-coverage.csv`, not silently scored as success.

## Results

Both scenarios identify all six coefficients. The SPECint92-only network has
505 informative systems; the SPEC89-enabled network has 515. These include
unanchored co-observations constraining relative scales and are **not** hundreds
of measured SPEC anchor machines. The SPEC89-enabled run has 115 observed
SPECint92 nodes, 122 inferred-89 nodes and 1,420 unanchored nodes; one-metric
unanchored nodes do not influence training.

For `linear_clock / with_spec89`:

| Input metric | Score unit | speed-VAXen coefficient k | Conditional factor CI95 |
| --- | --- | ---: | --- |
| Dhrystone 1.1 | DMIPS | 0.64515 | 0.60039–0.69353 |
| Dhrystone 2.1 | DMIPS | 0.68424 | 0.63335–0.73805 |
| Whetstone native | MWIPS | 0.53870 | 0.45779–0.62680 |
| Whetstone SP | MWIPS | 0.59767 | 0.52016–0.67364 |
| Whetstone DP | MWIPS | 0.95903 | 0.83128–1.09194 |
| LINPACK n=100 | MFLOPS | 3.13484 | 2.75594–3.59550 |

For example, a Dhrystone **1.1** score of **10 DMIPS** maps to approximately
6.45 speed-VAXen (SPECint92 ≈ 6.5) using this experimental coefficient. Raw
Dhrystones/second first need the declared /1757 DMIPS conversion; coefficients
must not be applied to uninterpreted KIPS or printed unit labels with unresolved meaning.

On the common 35-system, 80-node observed-SPECint92 holdout cohort with all three
families (`linear_clock / with_spec89`):

| Available inputs | Network P95 | Anchored-only control P95 |
| --- | ---: | ---: |
| Dhrystone 1.1 only | 28.62% | 26.24% |
| Dhrystone 2.1 only | 34.61% | 33.15% |
| Whetstone SP only (34 systems) | 39.55% | 38.82% |
| Whetstone DP only | 54.55% | 49.33% |
| LINPACK only | 44.86% | 46.74% |
| Dhrystone + Whetstone families | 28.65% | 29.62% |
| Dhrystone + LINPACK families | 28.99% | 30.73% |
| Whetstone + LINPACK families | 25.52% | 25.90% |
| All available measurements | 20.17% | 24.12% |

More available workloads do not guarantee a lower error, and the unanchored
coupling does not uniformly beat the anchored-only control on this population.
All combinations remain; the table is not a residual-based selection rule.

Over all 115 observed-SPECint92 nodes (59 systems), the all-available network
P95 is 85.1% (84.4% before the smaller Usenet posts, 83.5% before Richardson's lists). Before the 2026-10-03
vendor-report rows (82.3%), on the 48 nodes that also carry a one-processor rate (the former
anchor population) it is 31.5%; on 42 further DEC, multi-processor and
speed-only nodes 37.8%; on the 25 bridge-table nodes 122.7%, dominated by IBM
RS/6000 systems overpredicted by 78–129% because their LINPACK n=100 is high
relative to integer speed, and by the HP 9000/J200 (−69%, see below).

The network emits full-availability estimates for **1,420 unanchored nodes on
1,322 system keys** (an unresolved result counts as its own key). Of these,
1,376 nodes have one benchmark family, 28 have two and 16 have three. They are
not 1,420 newly verified machines: configuration identity and source
interpretation still need source-specific review. Their estimates are stored
separately from observed SPEC targets.

### Changes from the smaller Usenet result posts (2026-10-03)

[SSBA, Nefzger's LINPACK and McCalpin's Livermore posts](usenet-result-lists.md#smaller-result-posts-19901991)
add five results with eleven calibration inputs, all on systems the network
already had: HP 9000/720 and SPARCstation 2 (SSBA Dhrystone 1.1, Whetstone SP and
DP, LINPACK) and SPARCstation 2, SPARCstation 1+ and Sun 4/490 (LINPACK). The
Livermore rows are context. Node and informative-system counts are unchanged
(115 observed, 122 inferred-89, 1,420 unanchored; 505 and 515 informative).
`linear_clock / with_spec89` coefficients: Whetstone SP 0.59119 → 0.59767
(+1.10%), LINPACK 3.12475 → 3.13484 (+0.32%), the others within ±0.13%.

HP 9000/720 and SPARCstation 2 are new to the common holdout cohort (33 → 35
systems, 78 → 80 nodes), and its P95 rises (all-available 17.99% → 20.17%,
Whetstone SP alone 26.98% → 39.55%). The cause is one pairing: the HP 9000/720's
observed SPECint92 node is a 1996 Netlib disclosure (peak 64.0, base 51.6) made
with later compilers, while its 1991 classical vector predicts 33.9 speed-VAXen
(47% low all-available; 64% low from Whetstone SP alone). The same vector is
8–11% below its 1991 SPECint89 results (38.5–39.5). All-available
observed P95: 84.4% → 85.1%. Whether to reject that pair is open.

### Changes from Richardson's Dhrystone lists (2026-10-03)

[Richardson's Usenet lists](usenet-result-lists.md) add 570 Dhrystone results
(296 version 1.1, 274 version 2) on mostly pre-SPEC systems. About 20 of those
systems already had Whetstone or LINPACK results, so informative systems rise
486 → 505 (`spec92_only`) and 495 → 515 (`with_spec89`). Observed anchors are
unchanged (115 nodes); VAX 8700 adds one inferred-89 node (121 → 122).
Unanchored nodes rise from 1,146 on 1,094 system keys to 1,420 on 1,322 keys
(1,376 with one family, 28 with two, 16 with three). `linear_clock /
with_spec89` coefficients: Dhrystone 1.1 0.64775 → 0.64513 (−0.40%), Dhrystone
2.1 0.69674 → 0.68453 (−1.75%), LINPACK 3.09026 → 3.12475 (+1.12%), Whetstone
native −1.13%, DP −0.91%, SP −0.45%. Without SPEC89 targets Dhrystone 2.1 falls
2.77% and Dhrystone 1.1 0.87%. All-available observed P95: 83.5% → 84.4%;
common-cohort all-available 18.11% → 17.99%, Dhrystone 2.1 alone 33.94% → 31.55%.

### Changes from MIPS Performance Brief 3.5 (2026-10-03)

The 30 calibration rows of [Brief 3.5](vendor-performance-reports.md#mips-performance-brief-35-1988)
add 14 results: MIPS M/500, M/800, M/1000, M/120-5 and M/2000, VAX 11/780,
8550 and 8600, Sun-3/160M, Sun-3/260 and Sun-4/200. M/120-5 and M/2000 add
inferred-89 nodes (117 → 121); none adds an observed anchor. They are again
underpredicted (Dhrystone −19% to −24%, Whetstone −38% to −40%, LINPACK −23%).
`linear_clock / with_spec89` coefficients move −0.28% to +0.42%, except
Whetstone SP +5.1% (0.56493 → 0.59387); without SPEC89 targets Dhrystone falls
1.2–1.4% and Whetstone SP rises 3.8%. All-available observed P95: 83.8% →
83.5%; common-cohort all-available 17.37% → 18.11%.

### Changes from the 1990 DEC report rows (2026-10-03)

The 43 calibration rows of the
[1990 DEC RISC summary](vendor-performance-reports.md) add nine results on nine
systems (DECstation 2100/3100/5000-200, DECsystem 5400/5810, SPARCstation 1/330,
Sun-4/260, HP 9000/835). None carries a SPECint92 value, so observed anchors are
unchanged (115 nodes); they add SPECint89-inferred nodes (107 → 117 on 47 → 51
systems) and one unanchored node. `linear_clock / with_spec89` coefficients:
Dhrystone 1.1 +0.43%, Dhrystone 2.1 +0.28%, LINPACK +1.27%, Whetstone native
+1.22%, DP +1.44%, SP +10.92% (0.50931 → 0.56492). Without SPEC89 targets
Dhrystone falls 2.3–2.6%, LINPACK +1.3%, Whetstone SP +3.2%.

Every new inferred-89 node is underpredicted (single-metric, joint SPEC89 fit):
Dhrystone −14% to −30%, Whetstone −9% to −57%, LINPACK −5% to −65%. These 1989–90
RISC workstations have higher SPECint89 relative to Dhrystone, Whetstone and
LINPACK than the training population, which raises the coefficients and the
observed-SPECint92 holdout errors (all available: 82.3% → 83.8%). Whetstone
inferred-89 P95 falls (DP 277% → 88%, SP 295% → 119%) because the cohort grows
from 23 to 48 (DP) nodes and dilutes one outlier: the DEC N3909 VAX 4000/300 column
(p.29) has 62.5 DP / 89.3 SP read as MWIPS under the N3909 KWIPS rule, which
overpredicts its SPECint89 by about 700%. That interpretation predates this change
and is not revised here.

### Changes from the rate-anchored run (2026-10-03)

The anchor changed from SPEC92 peak rate in rate-VAXen to SPECint92 peak in
speed-VAXen, and the SPEC89 bridge from two edges (factor 0.95707) to one
(0.96039). Observed anchors grew from 74 to 115 nodes (29 → 59 systems):
SPECint92 is reported by DEC columns without a rate row, by multi-processor
disclosures and by the bridge table. With SPEC89 targets, coefficients rise
1.3–2.3% (Dhrystone 1.1 0.63251 → 0.64637, LINPACK 3.01985 → 3.06007); about
0.35% of that is the removed rate edge. Without SPEC89 targets they fall
1.0–2.2%, and LINPACK 12.7% (3.38392 → 2.95334), as the RS/6000 bridge-table
results now anchor it. The inferred-89 nodes are unchanged (107 on 47 systems;
P95 129.8% → 131.9%).

### Changes from the name-matched run (2026-10-02)

Coefficients moved by −8% to +4% (for example `reported_clock / rate_only`
LINPACK 3.595 → 3.326, Dhrystone 1.1 0.635 → 0.614; `linear_clock /
with_spec89` LINPACK 4.080 → 3.756, Dhrystone 1.1 0.647 → 0.660). Informative
groups rose from 457/467 to 466/475. Anchored rate systems fell from 32 to 28
because names no longer link archive rate results to classical rows of other
configurations, while SPEC89 anchors grew as in the
[SPEC89 bridge](spec89-bridge.md#changes-from-the-name-matched-run-2026-10-02).
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
(details in the [SPEC89 bridge](spec89-bridge.md#pair-review-and-spelling-merges-2026-10-02)).

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
nonempty subset and uses joint coefficient draws to estimate speed-VAXen
(SPECint92 peak) with conditional CI95. It does not refit the experiment per request.

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
  with conditional calibration intervals, never labelled measured SPEC scores.
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
