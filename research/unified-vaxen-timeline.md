# Unified historical and SPEC rate timeline

Reviewed: 2026-10-03. Status: rebuilt on the schema database (step 5d,
`vaxen-timeline-v3`), with mix, speed and joint estimate rows restored on
2026-10-02 and the page reworked for them on 2026-10-03. Sections from
"Checked population (2026-09-28)" on describe earlier exports.

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
[speed/rate predictors](spec-speed-rate-predictors.md) on the database:

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
  [predictor report](spec-speed-rate-predictors.md#changes-from-the-name-matched-experiment).
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
[timeline contract](../docs/timeline.md#estimate-rows-and-removed-views-2026-10-02)). Earlier counts above describe the
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
