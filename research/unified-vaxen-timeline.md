# Unified historical and SPEC timeline

Reviewed: 2026-10-03. Status: rebuilt on the schema database
(`vaxen-timeline-v4`): rate-VAXen and speed-VAXen are parallel quantities
([quantities section](#parallel-rate-and-speed-quantities--2026-10-03); [latest change](#mips-performance-brief-35-rows--2026-10-03)). Earlier
sections record the v3 exports; the speed predictor and joint rows they describe
were removed. Sections from "Checked population (2026-09-28)" on describe
earlier exports.

The [shared contract and commands](../docs/timeline.md) combine saved calibration
with the database results. No fitting, score scaling by processor count, or
residual-based source selection is performed.

## Database rebuild — 2026-10-02

| Population | Records |
| --- | ---: |
| SPEC92–2026 rate, base | 32,027 |
| SPEC92–2026 rate, peak | 26,786 |
| Classical results (one processor or unknown count) | 1,641 |
| SPEC89 bridge estimates | 179 |
| **Total** | **60,633** |

Dates come from `result_chronology`: 44,899 CPU, 14,964 hardware, 17 reviewed
fallback and 753 unknown. The [compact audit](data/timeline/unified-audit.json)
records the counts and input/code hashes.

Checked against the 2026-09-29 export (121,365 records):

- All 60,633 record IDs are unique; every VAXen value is positive and finite
  and lies within its CI95.
- The 58,813 SPEC rate record IDs and reported scores are identical. CPU92 VAXen
  are identical; later generations change by one constant factor per generation
  and mode (CPU95 +1.3%/+2.2%, CPU2000 +5.4%/+7.6%, CPU2006–2026 +2.0% to +6.5%,
  peak/base), because the timeline now applies the saved
  [integer rate chain](data/spec/fitting/integer-rate-chain-intervals.csv) instead
  of the removed RAM + aliases joint-track backbone. 50,294 keep their year; the
  moves are the CPU-first dating described in [chronology](chronology.md).
- The 179 SPEC89 VAXen values are identical; 117 rows stay dated, 31 lose their
  year and 31 remain undated. The losses are Longbottom catalogue spellings and
  processor-family proxies that the step-3 chronology no longer matches
  ([known gaps](chronology.md#known-gaps)).
- Classical rows are now one per database result (1,641) instead of 1,532
  configurations merged by source and name, so values are not compared row by
  row; each is the saved network prediction for that result's scores.

Step 5d first removed the instruction-mix views, speed-derived and joint
estimates and the three matching policies; the next section restores the
estimates without the policies.

## Estimate rows — 2026-10-02

Rebuilt from the [mix network](instruction-mix-network.md) and the
speed/rate predictors (removed 2026-10-03; in Git history) on the database:

| Estimate rows | Records | Dated (CPU / hardware) | Unknown | Former export |
| --- | ---: | ---: | ---: | ---: |
| Gibson / ADP mix | 360 | 0 / 293 | 67 | 360 |
| Combined mixes | 186 | 0 / 151 | 35 | 186 |
| Speed only | 37,117 | 28,854 / 8,263 | 0 | 39,732 |
| Speed + rate (joint) | 17,039 | 14,008 / 3,031 | 0 | 20,563 |

The export now has 115,335 records, all with unique IDs and positive finite
VAXen inside their CI95.

- **Mix:** every former mix record has a counterpart. Values change by one
  factor per mix (Gibson +9.5%, ADP +7.1% at the step-5 refit; +1.1% and +0.4% after
the spelling merges below), from the refitted coefficients.
  283 keep their year, 6 change, 4 gain one and 67 stay undated.
- **Speed:** every former CPU95, CPU2006, CPU2017 and CPU2026 speed record
  remains. Values change by one factor per suite and mode, listed in the
  former predictor report (in Git history).
  The 2,615 CPU2000 speed records are gone: that boundary has one processor model.
- **Joint:** one row per hardware-near speed/rate pair and mode. The former rows
  were the union of three policies' calibration pairs, so the rows are not
  compared one to one.

The page was reworked for these rows on 2026-10-03 (next sections but one).

## Spelling merges, pair reviews and EPYC review — 2026-10-02

Same 115,335 records. Dates: hardware 26,702 → 26,826 and unknown 855 → 731
records, from the [catalogue spelling aliases](chronology.md#catalogue-spelling-aliases-2026-10-02);
no dated record changed year. The added EPYC 7313 rate-date review leaves its year
at 2021.

Values: classical rows follow the refitted network (`linear_clock / with_spec89`:
Dhrystone −4.1% to −4.2%, Whetstone −4.2% to −5.6%, LINPACK −19.6%; see
[classical network](classic-network-fitting.md#pair-review-and-spelling-merges-2026-10-02)),
and mix rows the refitted mix coefficients (Gibson −7.7%, ADP −6.3% against the
step-5 refit). SPEC89 values are unchanged; 2 of their rows carry a merged
system ID. SPEC rate, speed and joint rows are unchanged.

## Page rework — 2026-10-03

Same 115,335 records and values; only the page, lineage and calculator payloads
changed ([contract](../docs/timeline.md#estimate-filters-and-related-rows)).

- **Default view.** Baseline plus combined mixes (60,819 points); the former
  page's default likewise hid single Gibson/ADP ratings. Single mixes, speed
  and joint rows are now selected by estimate kind instead of route.
- **Removed.** The matching selector and per-policy variants; the joint tooltip's
  "rate-only — matched cohort" value, which belonged to a removed experiment.
- **Related rows** come from shared source result IDs and the resolved
  `system_id`, replacing name-derived comparison keys.
- **Lineage.** Gibson/ADP → classical + mix model → VAXen, and speed predictor
  nodes for CPU95, 2006, 2017 and 2026 into the older rate. The fit panel plots
  the 420 hardware-near tuples with the saved local factors.
- **Calculator.** Mix inputs use the mix network's timeline run; SPEC rate alone
  uses the `same_os` chain the timeline uses (formerly the RAM + aliases
  backbone); speed and speed + rate use the hardware-near predictors.

Checked: the full-population Node test reproduces a CPU2017 rate row, a CPU2026
joint row, a Gibson row and a two-rating combined mix through the calculator
(relative error below 1e-6), and each scatterplot draws exactly the boundary's
tuple count, which equals the saved summary's. In Chromium (2026-10-03) the page
loaded with no console errors; the lineage graph, the all-kinds scatterplot and a
pinned CPU2006 tooltip were inspected.

## Parallel rate and speed quantities — 2026-10-03

By user decision, speed and rate are two parallel chains, never merged; historical
routes are anchored to SPECint92 speed ([scope](../docs/scope-and-metrics.md#two-parallel-quantities-rate-vaxen-and-speed-vaxen)).
The export is `vaxen-timeline-v4`; every row carries `quantity`.

| Rows | Quantity | Records | Change |
| --- | --- | ---: | --- |
| SPEC92–2026 rate | rate | 58,813 | Unchanged |
| SPEC92–2026 speed | speed | 40,248 | Through the [integer-speed chain](spec-speed-chain.md) instead of the speed-only predictor |
| Classical | speed | 1,641 | Network re-anchored to SPECint92 |
| SPEC89 | speed | 179 | One-edge bridge to SPECint92 |
| Gibson / ADP mix, combined | speed | 360 / 186 | Mix network re-anchored |
| Speed + rate (joint) | — | 0 | Removed (was 17,039) |

101,427 records (formerly 115,335): 58,813 rate and 42,614 speed. All have
unique IDs and positive finite values inside their CI95 (checked 2026-10-03).
Dates: 74,475 CPU, 26,204 hardware, 17 fallback, 731 unknown.

- **SPEC speed.** CPU95, CPU2006, CPU2017 and CPU2026 keep their 37,117 speed
  records; CPU2000 regains its 2,615 (the chain needs no per-boundary predictor),
  and CPU92 adds 516 SPECint92 / SPECbase_int92 rows equal to their score. Values
  are now speed-VAXen, not predicted rate-VAXen, so they are not compared one to
  one with the former rows; the per-point factors are in the
  [speed chain](spec-speed-chain.md#results).
- **Classical.** `linear_clock / with_spec89` coefficients rose about 2%
  (Dhrystone 1.1 0.63251 → 0.64637, LINPACK 3.01985 → 3.06007, Whetstone DP
  0.92958 → 0.94877); see the [network report](classic-network-fitting.md).
- **SPEC89.** The bridge factor moved 0.9570709 (two edges, to rate-VAXen) →
  0.9603866 (one edge, to SPECint92); see the [bridge](spec89-bridge.md).
- **Mix.** Gibson 0.00037246 → 0.00037966, ADP 0.00018340 → 0.00018706
  speed-VAXen per KIPS ([mix network](instruction-mix-network.md)).
- **Page.** A Quantity filter (throughput · rate-VAXen ●, single job ·
  speed-VAXen ▲); values are labelled with their quantity. The lineage has
  parallel rate and speed rows, with a dotted diagnostic-only SPECint92 →
  rate-VAXen edge; its fit panel plots the speed-chain edges and SPEC89 pairs.
  The calculator returns separate speed and rate results and shows rate ÷ speed
  as a diagnostic only.

Checked: the full-population Node test (2026-10-03) reproduces CPU2017 rate,
CPU92/CPU95/CPU2006/CPU2026 speed, SPEC89, a multi-score classical row, a Gibson
row and a two-rating combined mix through the calculator, and checks that a speed
trace lights no rate node. In Chromium (2026-10-03) the page loaded with no
console errors.

## 1990 DEC report rows — 2026-10-03

The [1990 DEC RISC summary](vendor-performance-reports.md) adds nine classical
results (one per report column): 101,427 → 101,436 records (classical 1,641 →
1,650; speed 42,614 → 42,623). Seven are dated by hardware; SPARCstation 330 and
HP 9000/835 have no year evidence (hardware 26,204 → 26,211, unknown 731 → 733).
The new rows estimate 4.43 (Sun-4/260) to 12.72 (DECstation 5000/200)
speed-VAXen. The refit moved the other classical and mix rows by the coefficient
changes in the [network report](classic-network-fitting.md#changes-from-the-1990-dec-report-rows-2026-10-03);
SPEC rows and SPEC89 bridge estimates are unchanged. The full-population Node
test passed (2026-10-03).

## N3909 curated records and system merges — 2026-10-03

The [N3909 curated records and spelling merges](classic-network-fitting.md#changes-from-the-n3909-curated-records-and-system-merges-2026-10-03)
keep 102,034 records. Hardware-dated records rise 26,386 → 26,389 and unknown
1,156 → 1,153, matching the three merged-spelling records now resolving to dated
systems (not checked record by record). Classical and mix
rows move by the network coefficient changes; SPEC rows are unchanged. The
full-population Node test passed.

## Printed SPEC89 means — 2026-10-03

The [printed SPECint89 values](usenet-result-lists.md#printed-spec89-means-19901991)
add nine SPEC89 records: 102,025 → 102,034 records (SPEC89 179 → 188; speed
43,212 → 43,221; hardware-dated 26,381 → 26,386, unknown 1,152 → 1,156). The
Data General AV/6200, Motorola 8612 and both Motorola 8864SP rows have no curated
year. Each is its SPECint89 times the int89_to_int92 bridge factor, 10.85
(Data General AV/410) to 43.99 (CDC 4680 and MIPS RC6280) speed-VAXen. The
refit moved the classical and mix rows by the coefficient changes in the
[network report](classic-network-fitting.md#changes-from-the-printed-spec89-means-2026-10-03).
SPEC rows are unchanged. The full-population Node test passed.

## Smaller Usenet result posts — 2026-10-03

The [SSBA and Nefzger LINPACK posts](usenet-result-lists.md#smaller-result-posts-19901991)
add five classical results: 102,020 → 102,025 records (classical 2,234 → 2,239;
speed 43,207 → 43,212; hardware-dated 26,377 → 26,381, unknown 1,151 → 1,152;
the Sun 4/490 has no curated year). They estimate 5.02 (SPARCstation 1+, LINPACK
only) to 30.21 (HP 9000/720, SSBA) speed-VAXen; the SPARCstation 2 gets 10.34
from LINPACK alone and 15.89 from its SSBA vector. LINPACK-only estimates of
these Sun systems fall below their SPEC results (SPARCstation 2 SPECint92 21.8),
as LINPACK n=100 on Sun's 1990 Fortran was low relative to integer speed. The
Livermore rows are context and give no records. The refit moved the other
classical and mix rows by the coefficient changes in the
[network report](classic-network-fitting.md#changes-from-the-smaller-usenet-result-posts-2026-10-03).
SPEC rows are unchanged. The full-population Node test passed.

## Richardson's Dhrystone lists — 2026-10-03

[Richardson's lists](usenet-result-lists.md) add 570 classical results:
101,450 → 102,020 records (classical 1,664 → 2,234; speed 42,637 → 43,207;
hardware-dated 26,219 → 26,377, unknown 739 → 1,151). Most of the 412 undated
rows are microcomputers and minicomputers with no curated year; the
submission dates in the lists are upper bounds on the test date and are not
used as hardware dates. The refit moved the other classical and mix rows by the
coefficient changes in the [network report](classic-network-fitting.md#changes-from-richardsons-dhrystone-lists-2026-10-03).
SPEC rows are unchanged. The full-population Node test passed.

## MIPS Performance Brief 3.5 rows — 2026-10-03

[Brief 3.5](vendor-performance-reports.md#mips-performance-brief-35-1988) adds 14
classical results: 101,436 → 101,450 records (classical 1,650 → 1,664; speed
42,623 → 42,637; hardware-dated 26,211 → 26,219, unknown 733 → 739). Six are undated: no
year evidence is curated for MIPS M/500, M/800, M/1000 and M/120-5, Sun-3/160M
or Sun-4/200. The three VAX 11/780 results estimate 0.34–0.67 speed-VAXen, not
the reference machine's defined 1. This is a property of the calibration, not
of these rows: a Dhrystone 1.1 coefficient of 0.648 gives the VAX/VMS reference
of 1 DMIPS only 0.65 speed-VAXen, so classical routes calibrated on 1987–92
hardware understate the oldest machines. The full-population Node test passed.

## Family power law through the VAX-11/780 — 2026-10-03

The classical and mix routes now use
[family power laws](classic-network-fitting.md#family-power-law-through-the-vax-11780-2026-10-03).
Record counts are unchanged (102,034). The offline calculator and the
timeline rows evaluate `intercept + exponent × ln(score)` with the same joint
draws, and the lineage table shows family exponents.

- **VAX-11/780.** Its 17 classical rows now estimate 0.57–1.16 speed-VAXen
  (median 1.0), not 0.34–0.67. The spread is that of the 780's own source runs,
  for example Whetstone native 0.494 against 1.02 MWIPS.
- **Classical.** Slow machines rise and fast ones fall: a Dhrystone 1.1 row gains
  74% at 1 DMIPS and 27% at 10 DMIPS, and loses 7% at 100 DMIPS.
- **Mix.** Every mix row rises, by 46–180% (Gibson) and 83% or more (ADP); see the
  [mix network](instruction-mix-network.md#changes).

## Checked population (2026-09-28)

| Population | Records |
| --- | ---: |
| Historical classical configurations | 1,532 |
| SPEC89 bridge records | 179 |
| SPEC92–2026 base | 32,027 |
| SPEC92–2026 peak | 26,786 |
| CCTA Gibson mix estimates | 177 |
| CCTA ADP mix estimates | 183 |
| Combined available-mix views | 186 |
| Total exported views | 61,070 |

Base/peak records of the same submission remain separate. Historical repeated
measurements retain the earlier source/configuration aggregation and contributor
IDs. Historical eligibility is unchanged, including the prior exclusion of
explicit multi-processor observations outside that calibration.

Date selection follows CPU → hardware → submission-era → unknown. Current
selected kinds are **99 CPU**, **60,439 hardware**, **4 result-publication proxies**
and **528 unknown**. The limited CPU mapping explains why most modern records
still use hardware dates; CPU priority is implemented but the CPU chronology
catalog is not yet complete. All alternate candidate dates are retained.

## Numerical and implementation checks

- All 61,070 record IDs are unique and all VAXen values positive and finite.
- All 1,711 historical VAXen/CI95 values match the preceding saved population.
- Each modern value was compared against `collect_annual_records` using the
  validated current `same_os` factor chain. The CI factor table's chain hash and
  central factor were checked through the existing rate converter.
- No source modes or route-specific calibration intervals were pooled.
- The complete offline page was exercised in a minimal DOM model for mode
  populations, 200-row pagination, time zoom/reset, sorting and search. This is
  JavaScript state validation, not a substitute for browser rendering verification.

Artifacts were under `data/derived/figures/timeline/`; the audit snapshot of this
export was replaced on 2026-10-02. The full JSONL/CSV and offline HTML remain ignored generated files.

Existing annual hardware-year statistics remain historical snapshots. Their
cohorts should not be compared as if they already used the new CPU-first policy.
The shared timeline provides the combined chronological exploration.


## Instruction-mix integration

The 2026-09-28 extension reads the separate joint mix calibration experiment;
it does not recalibrate the original timeline routes. All 360 positive CCTA
mix cells appear exactly once from `linear_clock/with_spec89`, alongside the
original 60,524 records. The model has no directly observed SPEC anchor on a
mix-bearing node. Thus `instruction_mix_estimate_calibrated_to_rate` and the
conditional CI95 label remain visible in the shared data and page details.
Source approximate years remain qualified; existing reviewed date rules correct
PDP-8/E to 1970 while preserving the rejected source date. All 71 undated mix
records stay in the sortable table. Integration validation checks source-score
identity, numerical agreement with coefficients and joint bootstrap intervals,
original historical score parity, route filtering, modes and list pagination.


The same saved model now also supplies 186 combined available-mix views (174
Gibson+ADP, 12 single-mix fallbacks). Individual mix views are disabled by default
and remain selectable for comparison. Combined CI95 uses aligned joint draws;
these extra display records are not additional independent evidence. Default
All modes shows 60,710 records; all route alternatives exported together total
61,070. An anti-correlated-draw test verifies that covariance is preserved.

## Selectable estimation update — 2026-09-29

The current export contains **101,148 records**: the prior 61,070 baseline views,
39,732 speed-derived rate estimates and 346 unique paired speed/rate estimates.
The default view still shows the same 60,710 points (individual mix comparisons
remain off). Estimates and matching are selectable without duplicating a record
for each policy. Joint pairs are deduplicated by their two input submissions and
mode, not by machine name or equal score; repeated source submissions remain.

Complete-page offline JavaScript tests cover policy and estimate toggles,
unsupported strict CPU2000 estimates, related-point comparisons, shape selection,
correct upstream lineage, fit statistics and the existing sort/zoom/pagination
behavior. The fit viewer now exposes all five adjacent SPEC92–2026 joint-experiment
bridges (both modes and all three predictors), plus the 17 recovered SPEC89 → SPEC92
speed pairs. Offline checks verify plotted pair counts, finite coordinates,
generation-arrow selection and the legacy controls. Other generation cohorts remain
strict when SPEC95/CPU2000 matching is relaxed. Browser visual inspection remains unavailable: browser security policy
rejects local file URLs. No alternate browser transport was used.

These views were removed on 2026-10-02 (see the
[timeline contract](../docs/timeline.md#estimate-filters-and-related-rows)). Earlier counts above describe the
baseline population, which is still preserved.

## All-generation matching and calculator — 2026-09-29

The rebuilt export contains 121,386 records: 61,070 baseline views, 39,732
speed-derived estimates and 20,584 distinct admitted speed/rate pairs. RAM + aliases
is now the default, applied at every modern generation edge; Strict and CPU + clock
remain selectable. Historical proxy coefficients are unchanged.

The modern pathway graph now includes speed/joint predictor nodes feeding older
rate nodes. Its local input panel shows the selected speed/rate mask and both local
and full-route coefficients. Modern rate-edge details consume the same saved
shared-model backbone draws as the active timeline.

An offline prediction calculator follows the chart and precedes the list.
All 255 nonempty subsets of the eight historical metrics were checked against
the existing CLI (classical-only) or independent NumPy evaluation of saved aligned
draws (with mixes). SPEC single-input and joint calculations were checked against
saved coefficients for all three matching policies, generations and supported
modes. A reference CPU92 rate score maps to exactly 1 VAX within floating-point
precision; unsupported legacy/base and insufficient-model cases reject explicitly.
See the [calculator contract](../docs/timeline.md#offline-vaxen-calculator-2026-09-29).
