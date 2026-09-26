# Exploratory SPEC CPU92–CPU2026 integer-rate fitting

Reviewed on 2026-09-26. This is the primary account of the project's
**throughput/rate** reconstruction from SPEC CPU92 through CPU2026. The
adjacent-suite fits are reproducible and source-linked; their cumulative
VAX-reference scale remains an exploratory estimate, not a measured modern
VAX result or a validated universal benchmark conversion.

## Reproduce and inspect

From the repository root, using the uv-managed `.venv`:

```sh
./.venv/bin/cpushowspeed spec legacy92-rate-parse
./.venv/bin/cpushowspeed bridge fit-rate-generations
./.venv/bin/cpushowspeed bridge fit-rate92-anchor
```

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

For every adjacent suite pair, candidate submissions match normalized system
name, processor name and chip count. The **hardware-near** tier further
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
| CPU92 → CPU95, hardware near | 97.713 | 19 | 109.210 | 19 |
| CPU92 → CPU95, same OS | 95.900 | 11 | 109.107 | 11 |
| CPU95 → CPU2000, hardware near | 70.751 | 13 | 74.599 | 13 |
| CPU2000 → CPU2006, hardware near | 2.014 | 25 | 1.962 | 22 |
| CPU2006 → CPU2017, hardware near | 9.586 | 150 | 9.403 | 124 |
| CPU2017 → CPU2026, hardware near | 2.335 | 79 | 2.451 | 39 |

The CPU92→CPU95 search found **60** name/processor/chip candidate pairings.
Of these, **28** satisfy hardware-near conditions, representing 24 systems and
19 processor configurations; **16** satisfy the same-OS tier, representing
16 systems and 11 configurations. Both modes have scores for all 28 or 16
selected pairings. The CPU95–CPU2026 row counts, full-precision factors,
bootstrap ranges and source hashes are in the linked factor CSV. A large
`k`, especially CPU95→CPU2000, reflects a change in suite score scale; it is
not the performance gain of one machine.

On the CPU92→CPU95 edge, leave one processor configuration out, refit on the
others, then evaluate `exp(abs(log(actual/predicted))) - 1`. The linearly
interpolated **p95 error** is 19.3% base / 18.2% peak for hardware-near
pairings and 19.4% base / 13.1% peak for same-OS pairings. This measures
prediction within the selected cohort. The bootstrap 95% ranges in the CSVs
resample configurations and likewise describe conditional sampling variation;
**neither is a full-chain 95% error band**. The later-edge fit CSV currently
reports held-out *median* errors, so those numbers should not be presented as
comparable p95 values.

The same-OS CPU92→CPU95 peak center is 102.37 for six PA-RISC
configurations and 117.78 for five Pentium configurations; base centers are
85.81 and 109.58. The pooled factors therefore depend on architecture mix,
compiler and tuning choices. The broader hardware-near tier also contains
Alpha systems with changed OS releases. These differences limit a single
unqualified conversion, even though the two pooled peak factors happen to be
close.

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
checks that those later factors still correspond to the current bulk-file
hashes before emitting the chain.

| Generation | Same-OS base VAXen / rate point | Same-OS peak VAXen / rate point |
| --- | ---: | ---: |
| CPU92 | 0.04216 | 0.04216 |
| CPU95 | 4.043 | 4.600 |
| CPU2000 | 286.1 | 343.2 |
| CPU2006 | 576.1 | 673.3 |
| CPU2017 | 5,523 | 6,331 |
| CPU2026 | 12,893 | 15,517 |

These are **scale factors per one reported score point**, not annual machine
scores. The linked chain CSV also retains the hardware-near CPU92-anchor
scenario. Neither scenario compounds the edge uncertainties into a defensible
full-chain interval.

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
tuning for the fit cohorts require further review; no universal error margin
or historically comparable public index is claimed at this stage.
