# Source-column classical pair experiments

Review date: 2026-09-26. Implements the requested sequence: source vectors and
unit audit, pair availability, equal-weight/matched single-score fits, then
legacy and cross-source/clock sensitivity. The production VAXen chain is not
updated. These are conditional research fits, not approved configurations.

## Aggregation and stages

DEC's 88 machine/OS columns become individual vectors with observation IDs.
Dhrystone uses the declared omitted-K policy and DMIPS divisor 1757. Whetstone
uses the corrected MWIPS interpretation of printed KWIPS values, preserving explicit SP/DP.
LINPACK uses the n=100 DP row. Same columns can still contain benchmark-specific
compiler/copies/active-CPU differences. These remain unknown; the source-column
experiment deliberately does not claim a verified single-CPU rate cohort.

| Stage | Observations across all targets/pairs |
| --- | ---: |
| Source columns only | 1,826 |
| Add prior unscaled cross-source pairs | 2,718 |
| Also add DEC classical pairs to archive SPEC targets | 2,964 |
| Prior clock-sensitivity pairs + source/extended pairs | 3,134 |

These counts repeat observations across pair variants and targets; they are
not independent sample sizes. Duplicate source columns/submissions remain.
Model grouping controls their total fit weight. Common upstream lineage is
flagged but not asserted independent or automatically deduplicated.

The new cross-source matching review has 142 model-key candidates, of which
29 pass the selected target/OS/CPU rules. Explicit VMS/OSF/ULTRIX families
must agree; unknown/conflicting OS rejects the candidate. Archive SPEC92 rate
requires one reported CPU, unlike the qualified within-DEC experiment. Model
suffixes are preserved. DEC column clocks remain unknown; its values are not
silently frequency-scaled. The last stage uses the prior collector's scaling
scenario only where its existing rules permit it. Native Whetstone is never
silently equated with DEC's explicit SP column.

## Within-DEC integer-rate peak results

Each row compares the same observations and held-out models for its composite
and both baselines. Errors are interpolated P95 of absolute held-out model-center
percentage errors. All weights are fixed at one half; only the multiplier is fit.

| Pair | Models / column observations | Composite P95 | First-only P95 | Second-only P95 |
| --- | ---: | ---: | ---: | ---: |
| Dhrystone 1.1 + LINPACK100 | 24 / 48 | 16.59% | 39.87% | 16.56% |
| Dhrystone 2.1 + LINPACK100 | 24 / 48 | 15.77% | 27.83% | 16.56% |
| Dhrystone 1.1 + Whetstone SP | 18 / 34 | 15.83% | 21.93% | 27.19% |
| Dhrystone 2.1 + Whetstone SP | 18 / 34 | 17.33% | 26.49% | 27.19% |
| Dhrystone 1.1 + Whetstone DP | 18 / 34 | 30.24% | 21.93% | 37.54% |
| Dhrystone 2.1 + Whetstone DP | 18 / 34 | 29.84% | 26.49% | 37.54% |
| Whetstone DP + LINPACK100 | 18 / 34 | **11.12%** | 37.54% | 23.02% |
| Whetstone SP + LINPACK100 | 18 / 34 | 13.33% | 27.19% | 23.02% |

For DP Whetstone + LINPACK, the coefficient is 1.43035 for the square root of
inputs normalized to 1 MWIPS and 1 MFLOPS, targeting rate-VAXen. Conditional
factor CI95 is 1.38322–1.47246; maximum of held-out within-model tuple P95 errors
is 39.84%. The 11.12% model-center statistic is not a per-machine prediction
interval. A constant source-wide unit rescaling is absorbed by the multiplier
and leaves within-source prediction errors unchanged: a good fit cannot verify
the original unit label.

## Cross-source result after the MWIPS interpretation correction

On 2026-09-26 the user corrected the DEC Whetstone interpretation from literal
KWIPS to MWIPS. Raw source labels/cells are unchanged; the superseded rule is
retained in `interpretation-policy.json` revision history. All affected source
vectors, fits, plots and tracked snapshots have been regenerated.

| DP Whetstone + LINPACK stage | Models / observations | Composite P95 |
| --- | ---: | ---: |
| DEC only | 18 / 34 | 11.12% |
| Add legacy, unscaled | 19 / 51 | 17.24% |
| Add new cross-source targets, unscaled | 20 / 66 | 21.01% |
| Clock-sensitivity extension | 20 / 66 | 21.01% |

The 24 model-only DP comparisons now have median legacy/DEC ratio **1.0**
(range 0.1–1.10035). For example, DEC 2000/300 OSF's printed 108.9 is interpreted
as 108.9 MWIPS, versus 109 MWIPS in the legacy record. Remaining mismatches
are not silently corrected: these are model-only checks, not verified identical
configurations. The former thousandfold aggregate discrepancy is resolved by
the explicit interpretation change. Results remain configuration-unverified,
and pooling still increases held-out error relative to DEC alone.

Dhrystone 2.1 + LINPACK moves from 15.77%
to 27.97% in the final extension (25 models / 77 observations). Increasing loose
matching coverage did not improve predictive accuracy in this experiment.

## SSCL and Tomari disposition

SSCL Table 2 contributes twelve audited candidate rows, excluded from named
Dhrystone-version/n=100 pair fits because those identities remain unresolved.
The n=300 measurements are preserved separately, not relabelled n=100.

Tomari has only one of the three classical families, so it cannot independently
satisfy two-of-three. A separate 28-model Dhrystone2.1→reported CINT2006
multiplicative diagnostic gives held-out model P95 **52.45%**, despite the
previously reproduced high correlation. Its coefficient is 0.00183581 raw
CINT2006 points per DMIPS. This target is not rate or VAXen. Correlation and
multiplicative prediction accuracy answer different questions.

## Reproduction and evidence

```sh
uv run cpushowspeed classic source-pair-fit
```

Defaults: 10,000 model bootstrap resamples and seed 20260926. The same model
is withheld across all origins in a fold; equal-weight and component baselines
share observations. The bootstrap computes means with floating-point summation;
a regression check confirms agreement with the prior estimator to 12 decimal
places on a nonconstant example.

`data/derived/classic/source-pair-fit/` contains vectors, unit review, model-only
unit-scale comparisons, pair availability, matching review, all stage pairs,
summary, held-out folds/predictions, the Tomari diagnostic, comparison PNG/SVG,
and input/code/output hashes. Every pair retains original observation/target IDs
and source provenance. Full records join back to the PDF table or archive data.

Tracked snapshots: [summary](data/classic/source-fit-summary.csv),
[unit-scale review](data/classic/source-fit-unit-scale.csv),
[matching review](data/classic/source-fit-matching.csv),
[Tomari diagnostic](data/classic/source-fit-tomari.json),
[audit](data/classic/source-fit-audit.json).
No optimized weights or new source collection was introduced. The explicit
Whetstone unit interpretation was revised as recorded above.
