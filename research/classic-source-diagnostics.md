# Diagnosing classical/SPEC92 source differences

Review date: 2026-09-26. All four requested checks are implemented for the
SPEC92 integer-rate peak experiments: fixed common models, signed residuals,
reciprocal source prediction, and raw-record review of the largest deviations.
Input: final clock-sensitivity stage of the source-pair experiment, 617 pair
observations across benchmark variants. No observations were deleted or scores
changed in this diagnostic run.

`within_DEC`, `legacy_cross_source`, and `DEC_to_archive` are **construction
cohorts**, not three independent experimental sources. The legacy cohort mixes
classical compilations; DEC_to_archive reuses DEC predictor values with archive
targets. Shared upstream measurements may occur. Transfer tests therefore assess
cohort compatibility, not independent replication.

## 1. Fix common machine models

For Whetstone DP + LINPACK100, DEC and legacy share seven normalized models.
Using precisely these groups, their fitted coefficients are 1.46398 and 1.70085.
Within-cohort leave-one-model-out P95 errors are 12.28% and 10.86%, respectively.
The discrepancy survives fixing models, so merely adding different machines
cannot explain it. OS/compilers and other configuration details are not yet fixed.

## 2. Signed residuals and OS-associated offsets

Among sixteen DEC model groups with both OSF and VMS columns, all VMS/OSF
calibration-factor ratios are below one: median 0.74306, range 0.66223–0.84814.
The quantities compare `SPEC rate / sqrt(Whetstone DP × LINPACK100)` across
reported OS columns. They do not isolate a pure OS effect: compiler, libraries,
run settings, active CPUs/copies and other conditions may differ.

A controlled comparison fixes the **same six model groups** available in both
cohorts' OSF results, then changes only whether non-OSF observations are included:

| Cohort | All OS observations on those six models | OSF observations only |
| --- | ---: | ---: |
| DEC multiplier | 1.49018 | 1.69148 |
| Legacy multiplier | 1.70654 | 1.70654 |
| Legacy / DEC minus 1 | 14.52% | 0.89% |

This is evidence that the mix of OS/software conditions is an important
contributor to the aggregate source offset. It is not evidence that all remaining
configuration differences are resolved. DEC SP is not pooled with legacy native
precision, and no residual threshold selects the OSF subset.

## 3. Train one cohort, predict the other

For each common test model, exclude that entire model from the training cohort.
Fit on the remaining common models, then predict the held-out model's ratio
center in the other cohort. Single-input baselines use the same folds.
A separate same-common-model fit is also saved as descriptive transfer, with
explicitly weaker protection against hardware overlap.

| Fixed six-model comparison | Signed median error | Absolute P95 |
| --- | ---: | ---: |
| DEC → legacy, mixed OS | -15.11% | 16.58% |
| Legacy → DEC, mixed OS | +11.77% | 25.66% |
| DEC → legacy, OSF only | -3.36% | 11.90% |
| Legacy → DEC, OSF only | -0.11% | 15.44% |

Positive means overprediction: `100 × (predicted / observed - 1)`.
The signed plots show direction, rather than folding all variation into absolute
error. Small cohorts, source dependence and relative-error asymmetry mean these
P95 values are diagnostics, not population-level confidence bounds.

## 4. Inspect largest deviations against original records

Review selection is the ten largest absolute individual-pair errors across all
pair variants, plus the five largest for Whetstone DP + LINPACK100 (deduplicated).
The machine-readable [review](data/classic/source-diagnostic-outlier-review.jsonl)
contains every selected tuple, rank, raw-source location, classification and action.
Full rankings remain in the generated CSV. Reviewed findings:

- **DEC 3000/300LX and 3000/300X, VMS:** the PDF really prints the extracted
  SPEC rates and Whetstone values. For the LX, SP=91 and DP=125; this ordering
  is not sufficient evidence of a typo. Missing Dhrystone K interpretation stays
  explicit. No new extraction error was found in these checked cells.
- **AlphaStation 200 4/233, VMS:** rate 2685 and Whetstone SP 330.0 are confirmed
  in physical page 26. The earlier 333.0→330.0 OCR correction was already applied.
  The remaining deviation is not explained by that corrected OCR error.
- **HP 735/99:** the Dhrystone source row reports HP-UX 9.01; the SPEC disclosure
  reports HP-UX B.10.01 and compiler C HP92453-01 A.10.11. SPEC's peak subtests
  use 1–3 copies despite one reported CPU. This is a confirmed configuration
  mismatch for the paired observations, not an incorrectly transcribed score.
- **DEC 7000/610:** the 1992 OpenVMS PDF confirms rate 2188.6; its own LINPACK100
  result is 38.6, while the cross-source LINPACK predictor uses 44. The later
  1994 VMS table reports rate 2392. These distinguish reports/configurations;
  they do not justify overwriting any measured value.

DEC pages 26–27 and the 1992 OpenVMS PDF page 3 were re-rendered/visually
inspected. HP disclosure and Dhrystone cells were checked in the preserved
original HTML, not just normalized CSV. Other source records were traced via
original IDs and provenance. The review does not claim every ranked record
has been visually checked.

## Interpretation and next modeling decision

The evidence favors **heterogeneous software/run conditions and loose pair
construction** as important contributors. It does not support rejecting the
whole dataset as inaccurate. The one-CPU filter is insufficient to establish
single-copy execution; rate versus classical concurrency remains a limitation.
Source/OS-stratified calibration was subsequently tested in the
[environment comparison](classic-environment-models.md). The user then selected
the pooled geometric-composite method for primary historical bridge research;
stratification remains diagnostic. No production calibration or automatic
exclusion policy is changed by this report.

## Reproduction and artifacts

```sh
uv run cpushowspeed classic source-diagnostics
```

Outputs under `data/derived/classic/source-diagnostics/`: cohort comparisons,
signed residuals, reciprocal transfers, paired OS ratios, OSF-only counterparts,
same-six-model mixed-OS controls, full outlier ranking, PNG/SVG plots and a hash
audit. Model sets/folds are explicit in residual CSVs; one-common-model cases
have no leave-model-out fit. Tests check known directional offsets, exact common
sets and insufficient training cohorts.

Tracked summaries: [transfers](data/classic/source-diagnostic-transfers.csv),
[OSF transfers](data/classic/source-diagnostic-osf-transfers.csv),
[cohorts](data/classic/source-diagnostic-cohorts.csv),
[OSF cohorts](data/classic/source-diagnostic-osf-cohorts.csv),
[paired OS factors](data/classic/source-diagnostic-os-pairs.csv),
[audit](data/classic/source-diagnostic-audit.json).
