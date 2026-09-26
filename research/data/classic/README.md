# Classic collection and overlap snapshots

`acquisition.csv` inventories downloaded sources and hashes, not measurements.

`overlap-summary.csv`, `overlap-models.csv`, `overlap-coverage.csv` and
`overlap-audit.json` are compact outputs of `cpushowspeed classic overlap-spec`.
Full records and pairs remain in the ignored derived output directory. After
a reviewed rerun, copy `summary.csv`, `model-summary.csv`, `source-coverage.csv`
and `audit.json` to these four snapshot filenames respectively.

All model matches remain candidates. Keep conflicting/missing-clock pairs
and repeated source rows; they are not automatically independent experiments.
See the [overlap audit](../../classic-spec-overlap.md) for coverage limits.

`fitting-summary.csv` and `fitting-audit.json` snapshot `classic fit-spec92`
outputs on 2026-09-26. They describe unverified candidate cohorts, including
insufficient-group cases, not approved conversion factors. Full source-linked
pair rows (including exclusions) and plots are reproducible derived artifacts.
See [fitting findings](../../classic-spec92-fitting.md) for interpretation.

`composite-summary.csv` and `composite-audit.json` snapshot the three-benchmark
intersection audit, including its clock-normalization sensitivity scenario.
They contain coverage statistics, not fitted weights or conversion factors.

`composite-fit-summary.csv`, `composite-fit-folds.csv`, and
`composite-fit-audit.json` snapshot the equal-weight matched-cohort comparison.
Coefficients and confidence intervals are conditional exploratory statistics.
Tuple predictions and plots remain in the reproducible derived directory.

`pair-fit-summary.csv`, `pair-fit-audit.json` and
`dhrystone-version-summary.json` snapshot two-family fitting and the descriptive
same-row version comparison. Versions and pair formulas are not pooled.

`source-fit-*.csv/json` snapshot the source-column pair experiment, including
unit-scale and matching reviews. DEC/legacy DP summaries use the corrected MWIPS interpretation. The former
literal-KWIPS experiment is superseded; these remain exploratory factors. All fitting results remain conditional on unverified configurations.

`source-diagnostic-*` snapshots cover common-model comparisons, directed transfers,
OSF controls, paired OS factors and the original-record review of 15 outlier
pair observations. Review classifications do not remove source observations.
The construction cohorts may share underlying measurements; these are not
three independent laboratories.

`environment-*` snapshots close the present pooled/grouped/shrinkage comparison.
Observation-level weighted P95 is distinct from prior model-center P95. Full-data
coefficients do not establish an environmental correction for unseen early
platforms or SIMH/assembly reconstructions.

## Pooled native integer experiment

`pooled-summary.csv`, `pooled-bridge-evidence.csv`, `pooled-target-coverage.csv`
and `pooled-audit.json` snapshot the SPECint89/92 experiment. The target is
SPECint92-equivalent native integer score, not rate-VAXen. Original targets
and excluded metric coverage remain explicit. See [methods and results](../../classic-pooled-fitting.md).

## Primary direct rate composite experiment

`rate-composite-summary.csv`, `rate-composite-target-coverage.csv` and
`rate-composite-audit.json` preserve the direct SPEC92 integer-rate experiment.
Factors produce VAXen; base/peak and pair/triple variants remain separate.
See [method and validation](../../classic-rate-composite-fitting.md).

## SPEC89 to rate bridge experiment

`spec89-rate-bridge-evidence.csv`, `spec89-rate-bridge-summary.csv`,
`spec89-rate-summary.csv`, `spec89-rate-estimates.csv` and `spec89-rate-audit.json`
retain the two-edge bridge and joint-model experiment. Estimate intervals cover
coefficient uncertainty only; these rows are not historical rate measurements.
The compact estimate table omits bulk raw provenance, retaining stable source
record IDs and URLs. See [interpretation and reproduction](../../spec89-rate-bridge.md).
