# Exploratory SPEC CPU92–CPU2026 integer-rate fitting

**Resolved-identity refit (2026-10-02):** the fitters now read the built
database (`data/derived/schema/cpushowspeed.sqlite`) and pair results over resolved
system and processor identity instead of normalized names. The tables below
are from this refit; [Changes from the name-matched fit](#changes-from-the-name-matched-fit)
compares it with the 2026-09-29 [full-disclosure refit](spec-resource-field-audit.md#full-disclosure-refresh).

Reviewed on 2026-09-26. This is the primary account of the project's
**throughput/rate** reconstruction from SPEC CPU92 through CPU2026. The
adjacent-suite fits are reproducible and source-linked; their cumulative
VAX-reference scale remains an exploratory estimate, not a measured modern
VAX result or a validated universal benchmark conversion.

## Reproduce and inspect

From the repository root, using the uv-managed `.venv`:

```sh
./.venv/bin/cpushowspeed spec legacy92-rate-parse
./.venv/bin/cpushowspeed data extract
./.venv/bin/cpushowspeed data build
./.venv/bin/cpushowspeed bridge fit-rate-generations
./.venv/bin/cpushowspeed bridge fit-rate92-anchor
```

Every fit command takes `--database` (default the built database). A factor
table records `inputs_sha256`, one digest of the database's input hashes;
downstream commands refuse factors whose digest differs from the database.

The CPU92 [factor table](data/spec/fitting/cpu92-cpu95-rate-direct-factors.csv)
and [source-linked pairings](../data/derived/spec/fitting/cpu92-cpu95-rate-pairs.csv)
accompany its [base/peak scatterplot](../data/derived/spec/fitting/cpu92-cpu95-rate-overlap.png)
([SVG](../data/derived/spec/fitting/cpu92-cpu95-rate-overlap.svg)). The
[CPU95–CPU2026 factors](data/spec/fitting/integer-rate-factors.csv),
[scatter points with both disclosure URLs](../data/derived/spec/fitting/integer-rate-scatter-points.csv),
[base panels](../data/derived/spec/fitting/integer-rate-base-overlaps.png), and
[peak panels](../data/derived/spec/fitting/integer-rate-peak-overlaps.png)
show the later four edges. The [CPU95-relative chain](data/spec/fitting/integer-rate-cpu95-relative-chain.csv)
and [CPU92-anchored VAXen chain](data/spec/fitting/integer-rate-cpu92-vaxen-chain.csv)
are distinct machine-readable outputs. JSON diagnostics and full generated
pair records reside under `data/derived/spec/fitting/`.

## Data and metric boundary

The [Netlib CPU92 rate archive audit](spec92-archive-expansion.md) recovered
**274** `SPECrate_int92` disclosures from 22 issue summaries; 199 also report
`SPECrate_base_int92`. The parser checks each score against its issue summary
and the geometric mean of its six per-benchmark rates. It retains each
benchmark's copy count and timing, original URL and SHA-256. The direct fit
checks every cached CPU92 page against that hash again. The separately
recovered 1992 Digital vendor brief is excluded from this official-submission
cohort.

For CPU95, CPU2000, CPU2006, CPU2017 and CPU2026, the input is the cached,
SHA-256-checked official SPEC bulk CSV, selecting positive integer-rate base
or peak scores. The parsed submission counts are respectively **773, 2,481,
15,039, 13,359 and 176**. Speed submissions, including CPU92 `SPECint92`,
never enter these rate-to-rate fits. One reported rate score describes a
configured machine running concurrent benchmark copies, which need not equal
its chip or core count. Do not create a rate score by multiplying speed by
core count.

## Matching and estimator

For every adjacent suite pair, candidate submissions match resolved system
identity (`system_id`), resolved processor identity and chip count. The
processor key depends on how far the [processor resolver](processor-identity.md)
reached:

- `sku`: the catalogued SKU;
- `uncatalogued_model`: the family plus the model number the SKU rule parsed
  but the catalogue lacks;
- `clock_variants_only`: a family the curated
  [processor family table](../data/curated/processor_family.jsonl) flags as
  differing only in clock or core count, so family plus clock identifies the
  part. The 19 flags are a pairing judgement from general architecture
  knowledge, not source-checked per part; Pentium Pro and Pentium III are
  deliberately unflagged;
- `broad_family`: any other family. Such a pair counts as hardware near only
  when both disclosures give the identical normalized system text;
- unresolved: no key, never paired.

The **hardware-near** tier further
requires clock agreement within 1%, equal parsed RAM capacity, and no known
core or enabled-thread contradiction. CPU92→CPU95 also has a **same-OS**
sensitivity tier: apply the hardware-near conditions, then require normalized
OS strings to agree. The reported `UnixWare 2.0` and `UnixWare 2.0, SDK`
strings count as equivalent. This tier does not establish identical compiler
versions or tuning.

All candidate pairings and repeated submissions remain in the exported CSVs
and figures. The current later-suite fit uses the hardware-near tier only.

For base and peak separately, calculate each pair's
`old_rate_score / new_rate_score`. Take the median log ratio within a system,
then within a processor configuration; exponentiate the mean of the resulting
configuration log ratios. Thus the line is `old_rate_score = k ×
new_rate_score`, where `k` is a configuration-weighted geometric mean ratio.
Repeated submissions remain observations but do not each receive an
independent fit weight. A log-log regression slope is recorded as a diagnostic
and is **not** used as the conversion factor.

## Adjacent-suite results

| Edge and fit tier | Base `k` | Base configurations | Peak `k` | Peak configurations |
| --- | ---: | ---: | ---: | ---: |
| CPU92 → CPU95, hardware near | 98.172 | 24 | 108.897 | 24 |
| CPU92 → CPU95, same OS | 97.914 | 14 | 110.370 | 14 |
| CPU95 → CPU2000, hardware near | 70.751 | 13 | 74.230 | 13 |
| CPU2000 → CPU2006, hardware near | 1.999 | 60 | 1.868 | 50 |
| CPU2006 → CPU2017, hardware near | 9.456 | 150 | 9.400 | 125 |
| CPU2017 → CPU2026, hardware near | 2.331 | 78 | 2.452 | 38 |

The CPU92→CPU95 search found **152** system/processor/chip candidate pairings.
Of these, **44** satisfy hardware-near conditions, representing 34 systems and
24 processor configurations; **23** satisfy the same-OS tier, representing
23 systems and 14 configurations. Both modes have scores for all 44 or 23
selected pairings. The CPU95–CPU2026 row counts, full-precision factors,
bootstrap ranges and source hashes are in the linked factor CSV. A large
`k`, especially CPU95→CPU2000, reflects a change in suite score scale; it is
not the performance gain of one machine.

On the CPU92→CPU95 edge, leave one processor configuration out, refit on the
others, then evaluate `abs(predicted/actual - 1)`. The linearly
interpolated **p95 error** is 17.8% base / 16.7% peak for hardware-near
pairings and 17.9% base / 11.3% peak for same-OS pairings. This measures
prediction within the selected cohort. The bootstrap 95% ranges in the CSVs
resample configurations and likewise describe conditional sampling variation;
**neither is a full-chain 95% error band**. All five edges now export both held-out median and p95 errors using the same
configuration-level definition.

In the same-OS CPU92→CPU95 cohort, PA-RISC configurations (PA-7100,
PA-7100LC and four PA-7200) have peak centers 102.2–103.0 and base centers
84.2–92.8. The three P5 Pentium configurations center at 120.09 peak /
110.57 base and the four Pentium Pro configurations at 117.86 / 109.32; the
single R4400 configuration gives 103.51 / 96.54. The pooled factors therefore depend on architecture mix,
compiler and tuning choices. The broader hardware-near tier also contains
Alpha systems with changed OS releases. These differences limit a single
unqualified conversion, even though the two pooled peak factors happen to be
close.

## Per-edge confidence intervals

Error policy updated 2026-09-27: primary P95 now uses observed-target relative
error consistently with classical models. Factors and CI95 did not change. See
[before/after checks](calibration-cleanup.md). New factor CSVs also expose
`model_center_p95_percent` in percent; the legacy error field remains a fraction.

Recomputed on 2026-10-02. The [combined machine-readable table](data/spec/fitting/integer-rate-edge-intervals.csv)
includes both CPU92 anchor scenarios and all four later edges, separately for
base and peak. Each interval uses **10,000 bootstrap resamples of processor
configurations**, seed `892026`, with sorted configuration keys for stable
input order and linearly interpolated 2.5th/97.5th percentiles. The estimator
within a replicate is the geometric mean of sampled configuration ratios;
source rows, repeated submissions, and cohort membership are unchanged.
Within-configuration median summaries are held fixed during resampling.
These are percentile bootstrap intervals, conditional on treating the selected
configuration summaries as exchangeable sampling units. They do not cover
matching errors, unseen architectures or arbitrary individual machines.

The table below follows the annual chart's same-OS CPU92 anchor and strict
later edges. `k` multiplies a newer-suite score into older-suite score units.
P95 is a held-out relative prediction-error diagnostic, stored as a
fraction in the CSV and shown here as a percentage.

| Edge | Mode | Configurations | k | 95% CI for k | Held-out p95 error |
| --- | --- | ---: | ---: | --- | ---: |
| CPU92 → CPU95 | base | 14 | 97.914 | 91.825–104.32 | 17.9% |
| CPU92 → CPU95 | peak | 14 | 110.37 | 105.97–114.94 | 11.3% |
| CPU95 → CPU2000 | base | 13 | 70.751 | 66.344–75.099 | 20.3% |
| CPU95 → CPU2000 | peak | 13 | 74.23 | 70.798–78.192 | 16.1% |
| CPU2000 → CPU2006 | base | 60 | 1.9993 | 1.9264–2.0743 | 26.6% |
| CPU2000 → CPU2006 | peak | 50 | 1.8677 | 1.7974–1.9451 | 24.0% |
| CPU2006 → CPU2017 | base | 150 | 9.4562 | 9.3563–9.5555 | 16.3% |
| CPU2006 → CPU2017 | peak | 125 | 9.3999 | 9.3142–9.4879 | 13.1% |
| CPU2017 → CPU2026 | base | 78 | 2.3314 | 2.3037–2.3604 | 8.8% |
| CPU2017 → CPU2026 | peak | 38 | 2.4518 | 2.3985–2.5032 | 12.2% |

These are **separate edge intervals**, not simultaneous 95% coverage for all
edges. The whole-chain bootstrap below propagates draws rather than interval
endpoints and audits shared configurations and submissions before assuming
independence between the five edge cohorts.
The CPU92 VAX reference `604800 / 25500` is a defined scale constant and does
not itself need an estimated CI. No observations were removed as outliers.

## VAX-reference throughput scale

[SPEC's CPU92 capacity-method definition](https://www.spec.org/cpu92/specrate.txt)
gives each benchmark rate as `copies × (reference seconds / 25,500) ×
604,800 / elapsed seconds`. On the VAX-11/780 reference machine running one
copy, each benchmark's rate, and hence their geometric mean, is
`604,800 / 25,500 = 23.717647…`. For this **CPU92 integer-rate throughput**
convention, define `VAXen = CPU92_rate_score / 23.717647…`. This is a
whole-machine capacity reference. It does not turn a multicopy rate into
single-task speed or assert that another suite used the same workloads.

The first rate-chain output uses CPU95 rate score 1 as its bookkeeping unit.
The VAXen chain divides the fitted CPU92→CPU95 factor by 23.717647… and
multiplies it by the four strict later rate factors. The direct-anchor command
checks that those later factors were fitted from the same database inputs
before emitting the chain.

| Generation | Same-OS base VAXen / rate point | Same-OS peak VAXen / rate point |
| --- | ---: | ---: |
| CPU92 | 0.04216 | 0.04216 |
| CPU95 | 4.128 | 4.653 |
| CPU2000 | 292.1 | 345.4 |
| CPU2006 | 584.0 | 645.2 |
| CPU2017 | 5,522 | 6,064 |
| CPU2026 | 12,874 | 14,869 |

These are **scale factors per one reported score point**, not annual machine
scores. The linked chain CSV also retains the hardware-near CPU92-anchor
scenario. The conditional whole-chain intervals below quantify sampling
variation under an explicitly stated edge-independence assumption.

## Conditional whole-chain confidence intervals

Run `./.venv/bin/cpushowspeed bridge bootstrap-rate-chain` after both rate
fitting commands. The [chain interval CSV](data/spec/fitting/integer-rate-chain-intervals.csv)
contains both anchor scenarios and modes. The [bootstrap NPZ](../data/derived/spec/fitting/integer-rate-chain-bootstrap.npz)
contains complete multiplier vectors for later annual-statistic propagation;
the [JSON audit](../data/derived/spec/fitting/integer-rate-chain-bootstrap.json)
records input hashes, stream definition, NumPy version, edge overlap and
within-chain log-scale covariance. Configuration log-ratio summaries are
exported beside it for inspection.

The audit compared all ten edge pairs in the broad hardware-near cohorts.
It found **zero shared submission URLs and zero shared resolved
processor/chip/clock configuration keys**. The calculation therefore assumes
independent sampling of the five observed edge cohorts, conditional on those
identities. This is not evidence that unobserved workload or compiler biases
are independent. If future data introduce a shared key or source, the command
stops and requires a model that resamples those dependencies together.

For each mode and anchor scenario, 10,000 replicates resample the original
configuration log-ratio summaries with replacement, with the same number of
configurations as that edge's cohort. Each replicate averages the sampled log
ratios, cumulatively sums them, and exponentiates after applying the fixed
CPU92 VAX reference. Distinct SHA-256-derived PCG64 streams per edge avoid
artificial correlation from reusing the same seed. Thus every generation
within one replicate shares its earlier edges' uncertainty. Later-edge draws
are reused between the two anchor sensitivity scenarios. Base and peak are
simulated separately; this does not support joint base/peak or joint
anchor-scenario inference.

| Generation | Base VAXen / point, 95% CI | Peak VAXen / point, 95% CI |
| --- | ---: | ---: |
| CPU92 | 0.0421627 [0.0421627, 0.0421627] | 0.0421627 [0.0421627, 0.0421627] |
| CPU95 | 4.12833 [3.86891, 4.3998] | 4.65348 [4.47035, 4.84655] |
| CPU2000 | 292.084 [266.797, 318.676] | 345.428 [323.932, 368.657] |
| CPU2006 | 583.977 [531.407, 641.955] | 645.165 [598.859, 697.113] |
| CPU2017 | 5522.19 [5021.09, 6070.91] | 6064.48 [5626.23, 6556.14] |
| CPU2026 | 12874.4 [11691.1, 14166] | 14868.7 [13750.4, 16136.5] |

These are pointwise percentile 95% intervals for **mean calibration scales**,
using the same-OS CPU92 anchor and strict later edges in the table. CPU92's
zero-width interval reflects a defined unit, not a claim of error-free
measurements. Individual-machine prediction errors, identity mistakes,
architecture coverage and systematic workload/compiler effects are outside
these intervals. They are not simultaneous confidence bands over all years.
No outliers were removed.

For plotting, use `vaxen_per_rate_score[scenario, mode, replicate, generation]`
from the NPZ. Multiply every submission of a given generation by that same
draw before recomputing yearly quartiles and maxima. This preserves the shared
calibration error; independent per-submission jitter would destroy it. The
[combined annual figures](annual-rate-vaxen.md#combined-distribution-hardware-and-confidence-figures)
now use these vectors to recompute quartiles, fixed-leader scores and frontiers.

## Changes from the name-matched fit

Compared on 2026-10-02 with the 2026-09-29 name-matched outputs:

| Edge, tier | Mode | Configurations before → after | `k` before → after | Change |
| --- | --- | --- | --- | ---: |
| CPU92 → CPU95, hardware near | base | 19 → 24 | 97.713 → 98.172 | +0.47% |
| CPU92 → CPU95, hardware near | peak | 19 → 24 | 109.210 → 108.897 | −0.29% |
| CPU92 → CPU95, same OS | base | 11 → 14 | 95.900 → 97.914 | +2.10% |
| CPU92 → CPU95, same OS | peak | 11 → 14 | 109.107 → 110.370 | +1.16% |
| CPU95 → CPU2000 | base | 13 → 13 | 70.751 → 70.751 | 0% |
| CPU95 → CPU2000 | peak | 13 → 13 | 74.599 → 74.230 | −0.49% |
| CPU2000 → CPU2006 | base | 25 → 60 | 2.014 → 1.999 | −0.72% |
| CPU2000 → CPU2006 | peak | 22 → 50 | 1.962 → 1.868 | −4.80% |
| CPU2006 → CPU2017 | base | 150 → 150 | 9.586 → 9.456 | −1.36% |
| CPU2006 → CPU2017 | peak | 124 → 125 | 9.403 → 9.400 | −0.03% |
| CPU2017 → CPU2026 | base | 79 → 78 | 2.335 → 2.331 | −0.14% |
| CPU2017 → CPU2026 | peak | 39 → 38 | 2.451 → 2.452 | +0.03% |

All 28 old CPU92→CPU95 hardware-near pairs remain. The 16 added pairs are
12 P5 Pentium pairs (Dell Dimension XPS and XXpress Deskside systems whose CPU92 processor text `NNMHz Pentium Processor` was
unresolved before a P5 pattern alias was added) and 4 R4400 pairs reached
through the R4400 `clock_variants_only` flag. On CPU2000→CPU2006 the gain
comes from disclosures whose processor text carries extra prose that defeated
exact name matching but resolves to the same SKU. Name matching had also
paired some different SKUs within one family (for example Itanium 2 9040 with
9050); the `broad_family` rule excludes those.

The accepted CPU92/CPU95 result pairs in `result_pair.jsonl` are speed pairs.
No current fitter consumes them; the rate fit derives its own pairs.

## Source checks and remaining limits

The [HP J210 CPU92 rate disclosure](https://www.netlib.org/performance/html/spec.j210ir.crint92.12_95.notes.html)
reports peak 4,027 and base 3,330. Its matched [CPU95 rate
disclosure](https://www.spec.org/cpu95/results/res9509/p086.html) reports 39.4
in both modes, giving ratios 102.208 and 84.518; the pair CSV retains both
sources and hardware fields. The official [CPU95 RS/6000 44P-270 rate
disclosure](https://www.spec.org/cpu95/results/res2000q1/cpu95-20000124-04013.html)
reports base 811, versus [CPU2000 rate 10.8](https://www.spec.org/cpu2000/results/res2000q1/cpu2000-20000125-00038.html),
a ratio of 75.0926. The [CPU2017 HPE EPYC 9654 rate
disclosure](https://www.spec.org/cpu2017/results/res2022q4/cpu2017-20221024-32619.html)
reports base 1,630 with 384 copies; the [CPU2026 rate
disclosure](https://www.spec.org/cpu2026/results/res2026q2/cpu2026-20260210-00140.html)
reports base 661 with 384 copies, a ratio of 2.46596. These spot checks
confirm selected published values, not every pair's OS, compiler, tuning or
copy setting.

The automated audit found no candidate exact hardware key for a **nonadjacent
CPU95–CPU2026** suite pair. Therefore that segment has no independent
three-suite cycle check. CPU92 nonadjacent overlaps have not been audited by
this command. CPU2026 also has only 176 parsed integer-rate submissions in
this snapshot. Full CPU95 and later disclosures, copy counts, OS, compiler and
tuning for the fit cohorts require further review. The new intervals cover
conditional sampling variation; a universal error margin or validated public
historical index is not claimed.
