# Classical benchmark calibration

Reviewed: 2026-09-26 to 2026-10-03. This report owns how Dhrystone, Whetstone
and LINPACK results are paired with SPEC targets and calibrated to
**speed-VAXen** (one SPECint92 point; VAX-11/780 = 1; see the
[speed chain](spec-chains.md#speed-chain)). Three fits share the same inputs:

- [Direct composites](#direct-composites): fixed pair/triple composites against
  observed SPECint92 (method `classic-direct-speed-composites-v4-power-law-vax780`).
- [Sparse network](#sparse-network): individual benchmarks jointly, including
  machines with a single measurement (method
  `sparse-family-balanced-log-network-v6-two-stage-power-law-vax780`). The
  timeline and the [prediction CLI](../docs/classical-prediction.md) use it.
- [Power-law sensitivity](#power-law-sensitivity): the single-metric study that
  led both to power laws through the VAX-11/780.

The SPEC89 joint experiment is in [SPEC89](spec89.md#joint-model-experiment);
Gibson/ADP ratings join the network in [instruction mixes](instruction-mix.md).
Source acquisition and transcriptions are in
[historical sources](historical-sources.md). These are implemented experimental
models; they do not replace measured SPEC observations.

## Hardware overlap

`classic overlap-spec` parses records (parser `classic-hardware-overlap-v2-records-only`;
semantics in the [collection guide](../docs/classic-collection.md#hardware-overlap-discovery)).
It extracted 3,794 records from eight acquired sources, including CPU-only rows,
instruction-mix listings and unreviewed PDF machine-line candidates, so the
count is not independent measurements.

| Reader | Records | Boundary |
| --- | ---: | --- |
| Netlib Dhrystone | 328 | All source row IDs, including repeats and starred scores |
| Longbottom Whetstone history | 504 | Historical supplier section; excludes the later PC section |
| Gibson / ADP | 190 each | Includes missing-score listings |
| Later PC Whetstone / Dhrystone / LINPACK / Livermore | 574 / 121 / 158 / 356 | CPU-only labels |
| Netlib LINPACK PDF | 1,373 | Table 1 machine-line candidates; wrapped names rejoined for display only |

Pairing is done by the fitters on the built database (`classical_store`): a
classical result pairs with a SPEC target only when both resolve to the same
`system_id`. Names are never compared. Reported clocks are compared (within 1%),
CPU counts and reference definitions are checked; OS, compiler, cache and FPU
options remain unverified. As first counted (2026-10-02), 1,684 of 1,727
classical results resolved to a system, giving 533 cross-result pairings on 68
systems plus 62 same-result DEC columns; clocks were 158 compatible, 32
conflicting and 322 unknown. The [coverage CSV](data/classic/overlap-coverage.csv)
and [audit](data/classic/overlap-audit.json) are saved. Gabriel, NAS, Dhampstone
and Sieve results are not yet included; vendor MIPS claims are not treated as
executed benchmarks. Livermore has only CPU-only parsed rows. Pair reviews are
listed in [SPEC89](spec89.md#pair-review).

## Direct composites

For each declared pair or triple of distinct benchmark families:

`C = exp(mean(log(component score / component unit)))`

`log(estimated speed-VAXen) = b × (log C − log C₇₈₀)`,

so the VAX-11/780, scoring C₇₈₀, is one speed-VAXen for any exponent b. C₇₈₀ is
the same composite of the 780's own measured scores (each metric's median over
its distinct classical runs, as in the [network anchor](#model)). One exponent b
is fitted per cohort, variant, combination and predictor. Units are 1 DMIPS,
1 MWIPS and 1 MFLOPS; Dhrystone versions, Whetstone native/SP/DP and LINPACK
n=100 stay distinct. No environmental correction, learned weights,
residual-based exclusion or clock scaling is used.

A target is any result reporting SPECint92 (peak) or SPECbase_int92 (base): CPU92
disclosures, the reviewed DEC N3909 columns and the SPEC89/92 bridge table. Two
cohorts: `same_result` (scores and target from one source row or report column)
and `same_system` (primary; every classical result on the same resolved system,
clocks within 1% when both known, unknown clocks kept and labelled). Speed is one
job, so a target's processor count does not exclude it; classical results
reporting more than one CPU and reference-definition targets are excluded. Each
metric's value for a target is the median over its accepted pairings; a triple
needs all three families paired with the same target; nothing is imputed.

A "model" is a resolved system. The exponent is the anchored least-squares slope
with each system weighing 1 and each of its observations 1/n:
`b = Σ w·dx·log y / Σ w·dx²`, `dx = log C − log C₇₈₀`. CI95 uses 10,000
system-cluster bootstrap draws (seed 20260926), each also redrawing the 780's log
anchors with the network's robust run-spread standard error. Leave-one-model-out
keeps the anchor fixed. Single-component baselines use the same tuples and folds.
The main statistic is the P95 of absolute model-center percentage errors.

There are 2,332 tuples across both cohorts and all combinations, and 194
comparison rows. Peak targets cover 98 results on 45 systems (`same_system`),
base targets 31 results on 13 systems.

### Results (`same_system`)

| Peak composite | Systems / tuples | C₇₈₀ | Exponent b | Exponent CI95 | LOMO model-center P95 |
| --- | ---: | ---: | ---: | --- | ---: |
| Dhrystone 1.1 + LINPACK | 42 / 95 | 0.3507 | 0.8506 | 0.8382–0.8632 | 34.61% |
| Dhrystone 2.1 + LINPACK | 43 / 96 | 0.3419 | 0.8484 | 0.8319–0.8644 | 31.63% |
| Whetstone DP + LINPACK | 35 / 80 | 0.3164 | 0.8610 | 0.8492–0.8723 | 20.95% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 34 / 79 | 0.4447 | 0.8646 | 0.8542–0.8744 | 21.10% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 34 / 79 | 0.4372 | 0.8652 | 0.8534–0.8769 | 19.15% |

| Base composite | Systems / tuples | Exponent b | Exponent CI95 | LOMO model-center P95 |
| --- | ---: | ---: | --- | ---: |
| Dhrystone 1.1 + LINPACK | 13 / 31 | 0.8607 | 0.8495–0.8715 | 16.94% |
| Dhrystone 2.1 + LINPACK | 13 / 31 | 0.8576 | 0.8447–0.8706 | 13.80% |
| Whetstone DP + LINPACK | 13 / 31 | 0.8593 | 0.8484–0.8703 | 15.30% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 13 / 31 | 0.8649 | 0.8540–0.8755 | 15.70% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 13 / 31 | 0.8627 | 0.8513–0.8746 | 15.63% |

The `same_result` cohort covers 62 peak targets on 38 systems (Dhrystone 1.1 +
LINPACK b 0.8478, P95 20.78%; the Dhrystone 1.1 + Whetstone DP + LINPACK triple
0.8571, 32 systems, P95 17.35%). Every fitted exponent lies between 0.85 and
0.92. The anchored exponents sit below the unanchored free slopes (0.8646 against
0.956 for the peak triple), so the 780 lies above the free line extrapolated from
1990s systems: the era effect the [network](#limitations) lists as a limitation.

For the 34-system peak triple cohort, single Dhrystone, Whetstone and LINPACK P95
are 25.70%, 26.09% and 25.89%, against 21.10% for the composite; its maximum
within-system observation P95 is 42.45%. Base is worse than under the former
proportional factor (Dhrystone 1.1 + LINPACK 11.62% → 16.94%): the 13 base
systems span a narrow range far from the 780, whose local free slopes are
1.00–1.06. Base and peak cohorts differ, so base's smaller errors do not show it
is more predictable. The [full summary](data/classic/composite-summary.csv) has
all 17 combinations per variant and every baseline; no combination was removed
for high error, and no universal winning estimator is selected.

```sh
MPLCONFIGDIR=/tmp/cpushowspeed-mpl .venv/bin/cpushowspeed classic composite-fit
```

Outputs under `data/derived/classic/composite-fit/` (observations, summary,
predictions and target coverage); compact summary, coverage and audit in
`research/data/classic/composite-*`. Tests: `tests/test_classical_fit.py`,
`tests/test_classical_store.py`.

## Sparse network

### Model

Calibrate Dhrystone 1.1, Dhrystone 2.1, Whetstone native, Whetstone SP,
Whetstone DP and LINPACK n=100 to speed-VAXen, so that a machine with one
measurement can be estimated and several measurements combine on the log scale
with equal family weight. Each metric b follows a **power law** with one
exponent per group g (user decisions 2026-10-03): Dhrystone 1.1 and 2.1 share
one; Whetstone native, SP and DP each have their own; LINPACK has one.

`ln V_b = a_b + beta_g * ln(score_b)`, with the intercept **tied to the
VAX-11/780**: `a_b = -beta_g * c_b`, where `c_b` is the log median of the 780's
own distinct classical runs. The 780 therefore predicts exactly 1 speed-VAXen by
every metric; its measured scores are used, not the definitional 1 DMIPS:

| Metric | 780 runs | Median score | Run scores |
| --- | ---: | ---: | --- |
| Dhrystone 1.1 | 8 | 0.878 DMIPS | 0.744–0.933 |
| Dhrystone 2.1 | 2 | 0.835 DMIPS | 0.807, 0.863 |
| Whetstone native | 3 | 1.02 MWIPS | 0.494, 1.02, 1.18 |
| Whetstone SP | 2 | 0.736 MWIPS | 0.5, 1.083 |
| Whetstone DP | 3 | 0.715 MWIPS | 0.41, 0.715, 0.76 |
| LINPACK n=100 | 3 | 0.14 MFLOPS | 0.11, 0.14, 0.14 |

For configuration node i, with `s_ib = ln(score_ib)` and `theta_i` its log
speed-VAXen, minimize `sum_i sum_b w_ib * (a_b + beta_g(b) * s_ib - theta_i)^2`:

- Observed SPECint92 peak fixes theta to `ln(SPECint92)`.
- In the SPEC89-enabled cohort, an 89 node's theta is its log SPECint89 plus the
  fitted int89_to_int92 bridge log multiplier.
- A node without a target has a free theta, eliminated analytically, so
  co-observations constrain the parameters without inventing SPEC values.
- A component disconnected from all anchored metrics gets no coefficient.

The fit has two weighted least-squares stages (user decision 2026-10-03):
(1) all parameters from anchored nodes and from unanchored nodes spanning two or
more families; (2) with those exponents fixed, the free intercepts (the
instruction mixes) re-solved from all nodes. An unanchored one-family node
compares variants measured side by side, whose ratios drift by era; letting them
set exponents had pulled the Whetstone exponents down.

Each informative resolved system weighs one, split equally across its nodes, then
across available families, then across variants in a family; Dhrystone 1.1 and
2.1 do not create two family votes. Within each node and metric, source runs
contribute a median log score. A target's estimate is
`ln V = sum_b w_b * (a_b + beta_g(b) * ln(score_b))` with family-balanced weights
summing to one; with one benchmark it is `exp(a_b) * score_b^beta`. A partial
result is not labelled a full-availability prediction.

### Inputs and clock assumption

Anchored nodes are target results reporting SPECint92 peak (CPU92 disclosures,
the reviewed DEC columns and the bridge table) and, in the SPEC89-enabled cohort,
SPECint89 results from any source except the bridge table. A target's classical
scores come from its own result and every classical result on the same resolved
system. Other classical results become unanchored nodes, grouped by resolved
system (or the result itself), reported clock and explicit FPU-option labels.
Multi-CPU classical results and reference-definition targets are excluded; a
speed target is one job, so a multi-processor SPECint92 remains an anchor.
Holdout groups and bootstrap clusters are resolved systems.

- `reported_clock`: reject known frequency conflicts (more than 1%); keep
  unknown clocks unscaled.
- `linear_clock`: for Dhrystone and Whetstone, scale
  `score × target_clock / measured_clock` only when both results resolve to the
  same processor entity; LINPACK is never clock-scaled.

Of 590 target/classical pairings, 62 are same-result, 146 clock-compatible, 322
clock-unknown, 18 clock-conflicting and 21 reference-definition targets; reviews
reject 14 and accept 7 unscaled. Under `linear_clock` one conflict is scaled (a
Netlib Dhrystone row for the DEC 7000/610 at 182 MHz carried to 200 MHz, factor
1.0989) and 17 stay excluded because the processors differ (PA-RISC 7100 versus
7150, R4400 versus R10000). The scenarios differ by at most 0.01% in any
coefficient; every decision is in `clock-audit.csv`. A conditional same-label
check finds 7 Dhrystone comparisons on 4 systems (HP 9000/715 33→50 MHz: +0.68%
for 1.1, −0.36% for 2.1) and no Whetstone sweep, so Whetstone linearity remains
an assumption ([frequency checks](data/classic/network-frequency-checks.csv)).

### Uncertainty and holdouts

Both clock scenarios are fitted with SPECint92 targets only (`spec92_only`) and
with SPEC89 targets (`with_spec89`). Comparisons on the same anchors:
`anchored_only` omits unanchored coupling; `free_intercept` frees every
intercept instead of tying it to the 780 (comparison only).

10,000 bootstrap draws (seed 20260927) resample resolved systems jointly across
the network and bridge; each draw refits both and redraws the 780 anchor as
`c_b + N(0, sd_b)`. `sd_b` is the standard error of the 780's median: a robust
run-to-run log spread (1.4826 × the median absolute deviation of distinct runs
from their system/clock group median, pooled over groups with two or more runs)
divided by the square root of the 780's run count (`vax780-anchor.csv`). The
robust spread replaced the pooled variance on 2026-10-03 because Longbottom's
language and compiler variants (Cyber 173 from 0.009 to 0.73 MWIPS) inflated the
Whetstone native anchor error from 0.19 to 0.56 in log. CI95 is a percentile
interval of coefficients or estimates, not a prediction interval; it omits source
bias, matching mistakes, transport error and era drift.

All observations of a test system leave both the network and the bridge.
Availability masks test each benchmark, family, two-family subset and all
measurements; observed SPECint92 errors stay separate from agreement with
inferred SPEC89 targets. `complete_family_nodes` restricts comparisons to nodes
with all three families; missing held-out coefficients are recorded in
`fold-coverage.csv`, not scored as success.

### Results

Both scenarios identify all six coefficients. The SPECint92-only network has 505
informative systems and the SPEC89-enabled one 516; the latter has 114 observed
SPECint92 nodes, 127 inferred-89 nodes and 1,415 unanchored nodes. These are
not hundreds of measured SPEC anchor machines.

For `linear_clock / with_spec89`:

| Input metric | Score unit | Exponent β (CI95) | speed-VAXen at score 1 (CI95) | At 10 units |
| --- | --- | --- | --- | ---: |
| Dhrystone 1.1 | DMIPS | 0.868 (0.846–0.889) | 1.119 (1.055–1.187) | 8.26 |
| Dhrystone 2.1 | DMIPS | 0.868 (shared) | 1.170 (1.044–1.312) | 8.63 |
| Whetstone native | MWIPS | 0.972 (0.883–1.068) | 0.981 (0.662–1.378) | 9.20 |
| Whetstone SP | MWIPS | 0.816 (0.786–0.844) | 1.284 (1.188–1.386) | 8.40 |
| Whetstone DP | MWIPS | 0.877 (0.852–0.900) | 1.342 (1.253–1.435) | 10.10 |
| LINPACK n=100 | MFLOPS | 0.796 (0.768–0.826) | 4.778 (4.519–5.082) | 29.8 |

A Dhrystone 1.1 score of 10 DMIPS maps to about 8.26 speed-VAXen (CI95
7.73–8.78), and the 780's own 0.878 DMIPS to 1.00 (0.94–1.06). Raw
Dhrystones/second first need the /1757 DMIPS conversion; coefficients must not
be applied to uninterpreted KIPS. The [coefficient table](data/classic/network-coefficients.csv)
holds every scenario and cohort.

On the common 34-system, 79-node observed-SPECint92 cohort with all three
families (`linear_clock / with_spec89`):

| Available inputs | Network P95 | Anchored-only P95 | Free-intercept P95 | Proportional (v3) P95 |
| --- | ---: | ---: | ---: | ---: |
| Dhrystone 1.1 only | 25.29% | 26.56% | 28.21% | 26.36% |
| Dhrystone 2.1 only | 23.88% | 25.24% | 25.72% | 31.34% |
| Whetstone SP only (33 systems) | 38.48% | 29.86% | 37.63% | 21.22% |
| Whetstone DP only | 27.82% | 35.21% | 34.29% | 62.11% |
| LINPACK only | 40.63% | 39.93% | 48.30% | 44.00% |
| Dhrystone + Whetstone families | 25.49% | 23.23% | 28.02% | 32.17% |
| Dhrystone + LINPACK families | 31.96% | 32.29% | 37.63% | 27.36% |
| Whetstone + LINPACK families | 30.26% | 26.41% | 36.19% | 22.83% |
| All available measurements | 27.24% | 25.27% | 32.29% | 21.13% |

On this cohort the power law is not better than the former proportional form
overall (27.24% against 21.13%), and Whetstone SP remains the weakest metric.
Over all 114 observed-SPECint92 nodes (58 systems) the all-available P95 is
67.9% (proportional 89.3%), and against inferred-89 targets 87.2% (proportional
139.8%), which is where the power law is far better. The broad observed
population includes the bridge-table IBM RS/6000 systems, overpredicted because
their LINPACK n=100 is high relative to integer speed, and the HP 9000/J200,
whose two LINPACK rows are 38 MFLOPS (`+O3`) and 5.5 MFLOPS (`fort77 -o`).

The network emits full-availability estimates for **1,415 unanchored nodes on
1,316 system keys** (1,374 with one family, 28 with two, 16 with three). They are
not newly verified machines and are stored separately from observed targets.
The VAX-11/780's 17 classical results estimate 0.49–1.17 speed-VAXen (median
1.0), the spread of its own source runs.

### Limitations

- **Era drift is a limitation, not a model term.** At a fixed score later systems
  earn less SPEC; the pooled exponent below one absorbs both that drift and any
  true sub-linearity (see [power-law sensitivity](#power-law-sensitivity)).
- 1987–90 RISC workstations score higher on SPECint89 relative to Dhrystone,
  Whetstone and LINPACK than the training population: the vendor-report and
  printed-mean systems are all underpredicted as inferred-89 nodes.
- Pairing by resolved system does not catch configuration mismatches such as a
  later compiler on the SPEC side; reviews handle known cases.
- Generic names ("PC/AT", "Homebrew", "Macintosh") group different machines
  under one system key; the frequency checks list these groups.

```sh
OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/cpushowspeed-mpl .venv/bin/cpushowspeed classic network-fit
```

`--jobs` sets worker processes for the four scenario/cohort fits (results are
identical for any value). Outputs under `data/derived/classic/network-fit/`:
coefficients, nodes and observations, clock and frequency audits, summary,
predictions and fold coverage, hardware estimates, correlated coefficient draws
and the hash-bound `prediction-calibration.json`.
Compact coefficients, summary, frequency checks and audit are kept in
`research/data/classic/network-*`. Tests: `tests/test_classic_network.py`,
`tests/test_classical_store.py`.

## Power-law sensitivity

Is speed-VAXen proportional to each classical score, or `speed = a × score^b`
with `b ≠ 1`? `classic power-law-sensitivity` fits each metric alone on the
network's anchored nodes (`linear_clock`; observed SPECint92 and bridged
SPECint89), each system weighing 1.

| Method | Form |
| --- | --- |
| `proportional` | log y = α + log x |
| `free_ols` | log y = a + b log x |
| `free_deming` | the same, with errors in both variables |
| `anchored_ols`, `anchored_deming` | log y = b (log x − log x₇₈₀) |
| `proportional_year` | log y = α + log x + c (year − 1990) |
| `free_ols_year` | log y = a + b log x + c (year − 1990) |

x₇₈₀ is the median of the 780's own measured nodes for that metric. Deming δ (y
over x error variance, pooled from replicates within system and clock) is 0.23
for Dhrystone, 0.17 for LINPACK and 0.81–0.89 for Whetstone SP/DP; replicates mix
compiler and OS differences, so these are upper bounds. Validation is
leave-one-system-out error, the predicted 780 speed for the free and year
methods, and 2,000-draw system-cluster bootstrap CIs.

| Metric | Method | Exponent b | 780 | LOSO median | LOSO P95 |
| --- | --- | --- | ---: | ---: | ---: |
| Dhrystone 1.1 (69 systems) | proportional | 1 | 0.55 | 16.9% | 38.7% |
|  | free OLS | 0.935 (0.901–0.966) | 0.72 | 15.0% | 39.2% |
|  | free Deming | 0.964 (0.932–0.994) | 0.64 | 15.0% | 38.7% |
|  | anchored OLS | 0.862 (0.854–0.871) | 1 | 8.2% | 48.3% |
|  | free + year | 0.972 (0.906–1.029) | 0.83 | 14.8% | 37.9% |
| Dhrystone 2.1 (66) | proportional | 1 | 0.56 | 19.4% | 39.5% |
|  | free OLS | 0.894 (0.868–0.915) | 0.88 | 12.1% | 39.1% |
|  | free Deming | 0.920 (0.894–0.942) | 0.78 | 13.2% | 38.9% |
|  | anchored OLS | 0.865 (0.856–0.873) | 1 | 10.4% | 38.9% |
|  | free + year | 0.867 (0.813–0.926) | 0.73 | 13.2% | 39.2% |
| Whetstone DP (57) | proportional | 1 | 0.59 | 26.8% | 50.4% |
|  | free OLS | 0.840 (0.816–0.867) | 1.12 | 21.3% | 35.1% |
|  | free Deming | 0.854 (0.829–0.882) | 1.05 | 21.8% | 34.9% |
|  | anchored OLS | 0.864 (0.855–0.874) | 1 | 20.9% | 34.1% |
|  | free + year | 0.936 (0.889–1.013) | 2.43 | 18.6% | 32.4% |
| Whetstone SP (50) | proportional | 1 | 0.51 | 20.0% | 45.5% |
|  | free OLS | 0.875 (0.843–0.910) | 0.86 | 21.8% | 32.6% |
|  | free Deming | 0.897 (0.870–0.933) | 0.79 | 19.8% | 34.9% |
|  | anchored OLS | 0.842 (0.830–0.854) | 1 | 23.3% | 29.7% |
|  | free + year | 0.981 (0.933–1.040) | 1.80 | 21.7% | 29.1% |
| LINPACK n=100 (83) | proportional | 1 | 0.45 | 45.8% | 152.6% |
|  | free OLS | 0.722 (0.681–0.755) | 1.48 | 23.7% | 106.8% |
|  | free Deming | 0.829 (0.785–0.883) | 0.94 | 29.5% | 115.3% |
|  | anchored OLS | 0.807 (0.792–0.822) | 1 | 31.1% | 106.5% |
|  | free + year | 0.553 (0.481–0.621) | 0.25 | 30.1% | 69.0% |

Whetstone native, the remaining methods and every CI are in the
[machine-readable table](data/classic/power-law-sensitivity.csv) and
[audit](data/classic/power-law-sensitivity-audit.json).

1. **Free exponents are below 1 for every metric** (0.72–0.96), and every CI
   excludes 1 except with a year term. Errors in x do not explain this: Deming
   moves b only 0.01–0.11 toward 1.
2. **The proportional form underpredicts the 780 by 41–55%** (except Whetstone
   native, 0.89); the free power laws predict 0.64–1.56.
3. **Anchoring through the 780 costs little in held-out error**: anchored LOSO
   P95 is equal or lower than free OLS except for Dhrystone 1.1 (48.3% vs
   39.2%), and 16–46 points below the proportional form for Whetstone SP/DP and
   LINPACK.
4. **Era is confounded with the slope.** With the exponent fixed at 1 the year
   term is −29% to −69% per decade; with a free exponent b returns near 1 for
   Dhrystone 1.1 and Whetstone, not Dhrystone 2.1; year models extrapolate badly
   to 1977. The data cannot separate sub-linear growth from classical scores
   inflating relative to SPEC over time.

Single-metric fits ignore the network's coupling and family balancing, and the
780 is one system with one or two nodes per metric: a single validation point.
Selected (user decisions 2026-10-03): the 780 anchor for the network, composites
and SPEC89 joint fits, with era confounding left as a limitation.

## History

- 2026-09-26/27: overlap parsing on normalized names; direct composites and the
  network fitted as proportional factors against SPEC92 rate.
- 2026-10-02: pairing over resolved systems; catalogue spelling merges (34 fewer
  system IDs) moved network coefficients by 4–6% (LINPACK −19.6%).
- 2026-10-03, data: re-anchored to SPECint92 speed (observed anchors 74 → 115
  nodes); added the 1990 DEC report, MIPS Brief 3.5, Richardson's Dhrystone lists
  (570 results), the SSBA and Nefzger posts, printed SPEC89 means and the DEC N3909
  curated readings; rejected the HP 9000/720 1996 pairing; merged the VAX
  6310/6410 spellings.
- 2026-10-03, model: power laws through the VAX-11/780 (v4), separate Whetstone
  precision exponents (v5), the two-stage fit (v6) and the robust anchor error.
  Against v3 a Dhrystone 1.1 rating gains 74% at 1 DMIPS and 27% at 10 DMIPS and
  loses 7% at 100 DMIPS.
