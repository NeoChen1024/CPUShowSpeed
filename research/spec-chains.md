# SPEC92–2026 integer rate and speed chains

Reviewed: 2026-10-03. This report owns the two modern calibration chains:

- **rate-VAXen** (throughput): CPU2026 rate → … → `SPECrate_int92`, then the
  defined CPU92 VAX factor.
- **speed-VAXen** (one job): CPU2026 speed → … → `SPECint92`, which is
  speed-VAXen by definition.

By user decision (2026-10-03) the two chains are parallel and never merged or
converted into each other. Both are implemented conditional estimates: the
adjacent-suite fits are reproducible and source-linked, but their cumulative
scale is not a measured modern VAX result or a validated universal conversion.
Source collection and the field/resource audits behind these inputs are in
[SPEC sources and audits](spec-sources.md).

## Reproduce and inspect

From the repository root, using the uv-managed `.venv`:

```sh
./.venv/bin/cpushowspeed spec cpu92-rate-parse
./.venv/bin/cpushowspeed data extract
./.venv/bin/cpushowspeed data build
./.venv/bin/cpushowspeed chain fit-rate-generations
./.venv/bin/cpushowspeed chain fit-cpu92-rate-anchor
./.venv/bin/cpushowspeed chain bootstrap-rate
./.venv/bin/cpushowspeed chain fit-speed
```

Every fit command takes `--database` (default the built database). A factor
table records `inputs_sha256`, one digest of the database's input hashes;
downstream commands refuse factors whose digest differs from the database.

Tracked results are in [`data/spec/fitting/`](data/spec/fitting/):
[CPU92 rate factors](data/spec/fitting/cpu92-cpu95-rate-direct-factors.csv),
[CPU95–CPU2026 rate factors](data/spec/fitting/integer-rate-factors.csv),
[rate edge intervals](data/spec/fitting/integer-rate-edge-intervals.csv),
the [CPU95-relative](data/spec/fitting/integer-rate-cpu95-relative-chain.csv) and
[CPU92-anchored](data/spec/fitting/integer-rate-cpu92-vaxen-chain.csv) rate chains,
[rate chain intervals](data/spec/fitting/integer-rate-chain-intervals.csv),
[speed factors](data/spec/fitting/integer-speed-factors.csv) and
[speed chain intervals](data/spec/fitting/integer-speed-chain-intervals.csv).
Pair records with both disclosure URLs, paired-score points, bootstrap draws and JSON
audits are generated under `data/derived/spec/fitting/`.

## Inputs and metric boundary

CPU92 rate comes from the 274 hash-checked Netlib `SPECrate_int92` disclosures
(199 also report `SPECrate_base_int92`); see the
[CPU92 rate archive](spec-sources.md#spec-cpu92-integer-rate-archive). The
parser checks each score against its issue summary and the geometric mean of its
six per-benchmark rates, and keeps copy counts, timings, URL and SHA-256. The
1992 Digital vendor brief is excluded from this official-submission cohort.

CPU95, CPU2000, CPU2006, CPU2017 and CPU2026 come from the cached,
SHA-256-checked official bulk CSVs: positive integer-rate submissions number
**773, 2,481, 15,039, 13,359 and 176**. Speed submissions never enter rate fits,
and rate never enters speed fits. One rate score describes a configured machine
running concurrent copies, which need not equal its chip or core count. No rate
score is created by multiplying speed by a core count.

## Matching and estimator

For every adjacent suite pair, candidate submissions match resolved system
identity (`system_id`), resolved processor identity and chip count. The
processor key depends on how far the
[processor resolver](identity-and-dates.md#processor-identity) reached:

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

The **hardware-near** tier further requires clock agreement within 1%, equal
parsed RAM capacity, and no known core or enabled-thread contradiction. A known
equal-count conflict between two reported constant copy or thread counts in one
mode drops that mode's ratio; unknown counts stay admitted and labelled.
CPU92→CPU95 rate also has a **same-OS** sensitivity tier: hardware near plus
agreeing normalized OS strings (`UnixWare 2.0` and `UnixWare 2.0, SDK` count as
equivalent). It does not establish identical compiler versions or tuning.

For base and peak separately, each pair gives `old_score / new_score`. Take the
median log ratio within a system, then within a processor configuration
(processor, chips, clock), and exponentiate the mean of the configuration log
ratios: `old_score = k × new_score`, a configuration-weighted geometric mean.
Repeated submissions remain observations but do not each receive an independent
weight. A log-log regression slope is recorded only as a diagnostic. Held-out
error leaves out one processor configuration and reports the linearly
interpolated P95 of `abs(predicted / observed − 1)` (the shared
[error policy](../docs/methods.md#unified-weighting-and-error-policy)).

## Rate chain

### CPU92→CPU95 pair review

The CPU92 anchor fits only pairs with an accepted `result_pair` row in
[`review.jsonl`](../data/curated/review.jsonl); unreviewed hardware-near pairs
are counted, warned about and left out. On 2026-10-02 all 44 automatic
hardware-near pairs were reviewed against both cached disclosures (Netlib CPU92
rate notes, SPEC CPU95 rate result): model, CPU and clock, CPU count, cache and
memory.

- **42 accepted.** Each review records how OS release, compiler version and
  per-benchmark copy counts differ. Most single-CPU HP CPU92 runs used two to
  five copies per benchmark where CPU95 used one; the SNI multiprocessor runs
  also differ in copies. These are run conditions of throughput, not hardware.
- **2 rejected** as different configurations: the AlphaStation 250 4/266 CPU92
  result (2 MB secondary cache) against CPU95 `res9509/p077` (512 KB), and the
  AlphaStation 600 5/266 CPU92 result (2 MB off-chip cache) against CPU95
  `res96q3/cpu95-960708-01025` (4 MB). The same AlphaStation 250 result remains
  paired with CPU95 `res96q3/cpu95-960708-01042`, which reports 2 MB.

The search found **152** system/processor/chip candidates; **44** are hardware
near and **42** accepted (33 systems, 23 processor configurations); **23** of
those also satisfy same OS (23 systems, 14 configurations). All candidate
pairings and repeated submissions remain in the exported CSVs.

### Adjacent-suite results

| Edge and fit tier | Base `k` | Base configurations | Peak `k` | Peak configurations |
| --- | ---: | ---: | ---: | ---: |
| CPU92 → CPU95, hardware near (reviewed) | 97.914 | 23 | 108.872 | 23 |
| CPU92 → CPU95, same OS (reviewed) | 97.914 | 14 | 110.370 | 14 |
| CPU95 → CPU2000, hardware near | 70.751 | 13 | 74.230 | 13 |
| CPU2000 → CPU2006, hardware near | 1.999 | 60 | 1.868 | 50 |
| CPU2006 → CPU2017, hardware near | 9.456 | 150 | 9.400 | 125 |
| CPU2017 → CPU2026, hardware near | 2.331 | 78 | 2.452 | 38 |

The hardware-near and same-OS CPU92 base factors agree to three decimals
(97.9145 and 97.9142) by coincidence; the cohorts differ. A large `k`,
especially CPU95→CPU2000, reflects a change in suite score scale, not one
machine's performance gain.

In the same-OS CPU92→CPU95 cohort, PA-RISC configurations (PA-7100, PA-7100LC
and four PA-7200) have peak centers 102.2–103.0 and base centers 84.2–92.8. The
three P5 Pentium configurations center at 120.09 peak / 110.57 base, the four
Pentium Pro at 117.86 / 109.32 and the single R4400 at 103.51 / 96.54. The
pooled factors therefore depend on architecture mix, compiler and tuning. The
hardware-near tier also contains Alpha systems with changed OS releases.

### Per-edge confidence intervals

Recomputed on 2026-10-02. Each interval uses **10,000 bootstrap resamples of
processor configurations**, seed `892026`, sorted configuration keys and
linearly interpolated 2.5th/97.5th percentiles; within-configuration medians are
held fixed. These are percentile intervals conditional on treating the selected
configuration summaries as exchangeable. They do not cover matching errors,
unseen architectures or arbitrary individual machines. The table follows the
timeline's same-OS CPU92 anchor and the later hardware-near edges; `k`
multiplies a newer-suite score into older-suite units.

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

For the hardware-near CPU92 tier the held-out P95 is 17.5% base / 16.8% peak.
The CSV stores held-out P95 as a fraction (legacy field) and
`model_center_p95_percent` in percent. These are **separate edge intervals**,
not simultaneous coverage for all edges. No observations were removed as
outliers.

### VAX-reference throughput scale

[SPEC's CPU92 capacity-method definition](https://www.spec.org/cpu92/specrate.txt)
gives each benchmark rate as `copies × (reference seconds / 25,500) × 604,800 /
elapsed seconds`. On the VAX-11/780 reference machine running one copy, each
benchmark's rate, and hence their geometric mean, is `604,800 / 25,500 =
23.717647…`. For this **CPU92 integer-rate throughput** convention,
`rate-VAXen = SPECrate_int92 / 23.717647…`. This is a whole-machine capacity
reference; it does not turn a multicopy rate into single-task speed or assert
that another suite used the same workloads. The constant is defined and needs
no estimated CI.

The chain divides the fitted CPU92→CPU95 factor by 23.717647… and multiplies by
the four later rate factors; the anchor command checks that those factors were
fitted from the same database inputs.

### Conditional whole-chain confidence intervals

`chain bootstrap-rate` writes the [chain interval CSV](data/spec/fitting/integer-rate-chain-intervals.csv)
for both anchor scenarios and modes, a bootstrap NPZ of complete multiplier
vectors and a JSON audit (input hashes, stream definition, NumPy version, edge
overlap and within-chain log-scale covariance).

The audit compared all ten edge pairs in the hardware-near cohorts and found
**zero shared submission URLs and zero shared resolved processor/chip/clock
configuration keys**. The calculation therefore assumes independent sampling of
the five edge cohorts, conditional on those identities; this is not evidence
that unobserved workload or compiler biases are independent. If future data
introduce a shared key or source, the command stops and requires a model that
resamples those dependencies together.

For each mode and anchor scenario, 10,000 replicates resample each edge's
configuration log-ratio summaries, cumulatively sum the sampled means and
exponentiate after the fixed CPU92 constant. Distinct SHA-256-derived PCG64
streams per edge avoid artificial correlation. Every generation within one
replicate shares its earlier edges' uncertainty. Base and peak are simulated
separately; this does not support joint base/peak inference.

| Generation | Base VAXen / point, 95% CI | Peak VAXen / point, 95% CI |
| --- | ---: | ---: |
| CPU92 | 0.0421627 [0.0421627, 0.0421627] | 0.0421627 [0.0421627, 0.0421627] |
| CPU95 | 4.12833 [3.86891, 4.3998] | 4.65348 [4.47035, 4.84655] |
| CPU2000 | 292.084 [266.797, 318.676] | 345.428 [323.932, 368.657] |
| CPU2006 | 583.977 [531.407, 641.955] | 645.165 [598.859, 697.113] |
| CPU2017 | 5522.19 [5021.09, 6070.91] | 6064.48 [5626.23, 6556.14] |
| CPU2026 | 12874.4 [11691.1, 14166] | 14868.7 [13750.4, 16136.5] |

These are pointwise percentile intervals for **mean calibration scales per
reported score point** (same-OS anchor), not individual machine scores and not
simultaneous bands over all generations. CPU92's zero width reflects a defined unit.
Individual-machine prediction errors, identity mistakes, architecture coverage
and systematic workload/compiler effects are outside them. To propagate them,
multiply every submission of a generation by the same draw
`vaxen_per_rate_score[scenario, mode, replicate, generation]`; independent
per-submission jitter would destroy the shared calibration error.

### Source checks and remaining limits

The [HP J210 CPU92 rate disclosure](https://www.netlib.org/performance/html/spec.j210ir.crint92.12_95.notes.html)
reports peak 4,027 and base 3,330; its [CPU95 rate disclosure](https://www.spec.org/cpu95/results/res9509/p086.html)
reports 39.4 in both modes (ratios 102.208 and 84.518). The [CPU95 RS/6000
44P-270 rate disclosure](https://www.spec.org/cpu95/results/res2000q1/cpu95-20000124-04013.html)
reports base 811 versus [CPU2000 rate 10.8](https://www.spec.org/cpu2000/results/res2000q1/cpu2000-20000125-00038.html)
(75.0926). The [CPU2017 HPE EPYC 9654 rate disclosure](https://www.spec.org/cpu2017/results/res2022q4/cpu2017-20221024-32619.html)
reports base 1,630 with 384 copies and the [CPU2026 disclosure](https://www.spec.org/cpu2026/results/res2026q2/cpu2026-20260210-00140.html)
base 661 with 384 copies (2.46596). These spot checks confirm selected published
values, not every pair's OS, compiler, tuning or copy setting.

No candidate exact hardware key was found for a **nonadjacent CPU95–CPU2026**
pair, so that segment has no independent three-suite cycle check; CPU92
nonadjacent overlaps have not been audited. CPU2026 has only 176 parsed
integer-rate submissions. The intervals cover conditional sampling variation; a
universal error margin or validated public historical index is not claimed.

## Speed chain

`chain fit-speed` (`integer-speed-chain-v1`) fits each adjacent speed edge
exactly as the later rate edges: automatic hardware-near speed pairs over
resolved identity, the same system/configuration estimator, a
configuration-cluster bootstrap per edge (10,000 draws, seed 20261003) and
held-out error leaving out one configuration. The edges share no configuration
or submission (checked; the fit refuses otherwise) and are combined as
independent. Unlike the rate anchor, the CPU92/CPU95 speed pairs are not
individually reviewed.

VAX-11/780 is the SPEC92 reference machine, so **one speed-VAXen is one
SPECint92 point**. For one-processor machines the two quantities nearly agree
(the [DEC N3909 diagnostic](spec89.md#evidence-path): 0.9966 rate-VAXen per
SPECint92). On multi-core machines their ratio approximates effective
parallelism; it is a diagnostic, not a combination. Historical routes
(classical, mixes, SPEC89) are anchored to speed-VAXen.

### Results

2026-10-03, base / peak. Factor = older-suite speed points per newer-suite point.

| Edge | Pairs | Configs | Models | Factor (CI95) | Held-out P95 |
| --- | --- | --- | --- | --- | --- |
| CPU95 → CPU92 | 45 / 45 | 21 / 21 | 9 / 9 | 37.885 (35.866–39.896) / 41.665 (40.029–43.257) | 19.4% / 17.2% |
| CPU2000 → CPU95 | 16 / 13 | 11 / 9 | 7 / 5 | 0.091298 (0.085992–0.097668) / 0.095775 (0.091992–0.10036) | 19.5% / 12.5% |
| CPU2006 → CPU2000 | 90 / 52 | 40 / 21 | 34 / 20 | 155.99 (150.82–160.98) / 146.50 (141.16–152.37) | 19.3% / 13.7% |
| CPU2017 → CPU2006 | 659 / 454 | 114 / 107 | 54 / 51 | 8.5726 (8.4971–8.6726) / 8.6617 (8.5922–8.7515) | 7.3% / 7.0% |
| CPU2026 → CPU2017 | 32 / 22 | 19 / 15 | 18 / 13 | 2.7110 (2.2987–3.2674) / 2.7248 (2.3550–3.2100) | 58.6% / 44.8% |

Speed-VAXen per reported speed point, with the rate chain's VAXen per rate point
(same OS) for comparison:

| Suite | Speed base (CI95) | Speed peak (CI95) | Rate base / peak |
| --- | --- | --- | --- |
| CPU92 | 1 (defined) | 1 (defined) | 0.04216 / 0.04216 |
| CPU95 | 37.885 (35.852–39.924) | 41.665 (40.018–43.287) | 4.1283 / 4.6535 |
| CPU2000 | 3.4588 (3.1825–3.7733) | 3.9904 (3.7673–4.2446) | 292.08 / 345.43 |
| CPU2006 | 539.55 (493.82–592.19) | 584.61 (545.05–628.36) | 583.98 / 645.16 |
| CPU2017 | 4,625.3 (4,229.1–5,075.1) | 5,063.7 (4,716.8–5,448.2) | 5,522.2 / 6,064.5 |
| CPU2026 | 12,539 (10,400–15,451) | 13,798 (11,751–16,551) | 12,874 / 14,869 |

Raw per-point scales differ by suite definition, so rate points are not speed
points. Where a suite's speed and rate share benchmarks and reference machine
(CPU2006), a one-copy rate point should be near one speed point; the rate factor
is 8% (base) and 10% (peak) above the speed factor. In CPU2017, whose speed and
rate are different benchmark sets, it is 19% / 20% above.

All 45 CPU92/CPU95 pairs were listed (2026-10-03): the same system name and clock
in both suites; per-pair peak ratios range 29–47. Four systems have two CPU95
submissions with different scores (for example HP 712/60: 1.62 and 2.08); both
are kept and system medians limit their weight. The chain reproduces each
edge's statistic exactly (the fit refuses otherwise).

Limitations: CPU2017 speed allows several OpenMP threads, so speed is "one job",
not "one thread". CPU2026 speed has sparse overlap (59% / 45% P95). Transfer
beyond the overlap hardware is unvalidated, and CI95 covers mean scale factors,
not individual prediction error.

## Prior work on chaining SPEC generations

- [Danowitz et al., *CPU DB* (2012)](https://web.engr.oregonstate.edu/~mjb/cs475/CPU-DB.pdf),
  PDF page 3: geometric means of score ratios from systems with results in two
  SPEC versions. No reproducible fuzzy-name acceptance rule is given.
- [Leiserson et al., *There's Plenty of Room at the Top* (2020)](https://www.microsoft.com/en-us/research/wp-content/uploads/2020/11/Leiserson-et-al-Theres-plenty-of-room-at-the-top.pdf),
  Figure 2 methods, PDF page 6: best score per processor, consecutive versions
  scaled by geometric-mean ratios of processors evaluated in both suites.
- [Furman, *iLORE* (2021)](https://vtechworks.lib.vt.edu/items/be77705e-b48e-40dd-8245-c88c694d3855),
  §§3.4–3.5: canonical processor records, manually reviewed alias resolution
  (an ML matcher was abandoned as inaccurate), same processor in consecutive
  suites, base integer speed and shuffled validation. Its practice of assigning
  a month or quarter to its first day is not copied into this project's dates.
- [*Progress of Computing*, §2.2 and Appendix B](https://api.repository.cam.ac.uk/server/api/core/bitstreams/ed2977b5-677d-4002-b7c8-eab877125aad/content):
  collapses submissions by processor, date, clock, chips and cores for a
  chip-date trend, and notes that SPEC scores belong to full systems.

These support processor identity as a candidate-generation layer; they do not
establish that every same-processor result is a same-configuration bridge. SPEC's
retirement rules for [CPU95→CPU2000](https://www.spec.org/cpu95/cpu95retirement),
[CPU2000→CPU2006](https://www.spec.org/cpu2000/) and
[CPU2017→CPU2026](https://www.spec.org/cpu2017/) deliberately produced
same-configuration dual submissions. SPEC's
[CPU95 Q&A](https://spec.org/cpu95/qanda) states there is no universal
CPU92↔CPU95 conversion.

## History

- 2026-09-26: first CPU92–CPU2026 rate fits on normalized names; the earlier
  speed-era annual figure and CPU92/95 speed overlap study were retired.
- 2026-09-27: held-out P95 switched to the shared relative error; factors and
  CI95 unchanged.
- 2026-10-02: fitters read the schema database and pair over resolved identity.
  Against the name-matched fit, same-OS CPU92 base moved +2.10% (11 → 14
  configurations) and CPU2000→2006 peak −4.80% (22 → 50); the added CPU92 pairs
  are P5 Pentium systems and R4400 `clock_variants_only` pairs. The CPU92 pair
  review then moved the hardware-near factor by −0.26% base / −0.02% peak and
  left the same-OS factor, the chain and every annual leader unchanged.
- 2026-10-03: the integer-speed chain replaced the former speed, rate-matched
  and joint speed/rate predictors (in Git history).
- 2026-10-03: the annual rate view (`plot annual-rate`, `plot annual-rate-ci`,
  its leader, statistics and confidence tables and figures) was removed; the
  [timeline](../docs/timeline.md) shows every rate result by year. The fitting
  commands no longer draw PNG/SVG figures. Both are in Git history.
