# Unified historical and SPEC rate timeline

Reviewed: 2026-09-28. Status: implemented data adapters and offline interactive
view; browser visual interaction not verified due to local-file navigation policy.

The [shared contract and commands](../docs/timeline.md) combine existing historical
estimates with the current eligible SPEC92–SPEC2026 integer-rate population.
No fitting, score scaling by processor count, or residual-based source selection
was performed.

## Checked population

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

Artifacts are under `data/derived/figures/timeline/`; the compact
[checked audit snapshot](data/timeline/unified-audit.json) records the population
and provenance. The full JSONL/CSV and offline HTML remain ignored generated files.

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
