# SPECint89 bridge to SPEC92 rate and joint classical fitting

Computed and reviewed: 2026-09-27.

## Evidence path

The normalized hardware-key intersection between the current SPECint89 records
and the available SPEC92 integer-rate records is **empty**. This remains true
with the existing clock-supported name relaxation, including DEC source-column
rate observations and even before restricting processor counts. The audit
records this result; it is not a claim about all surviving historical sources.

The implemented path therefore uses two separately observed edges:

`SPECint89 → SPECint92 → SPECrate_int92 × 25500 / 604800`.

1. The [archived integer bridge](data/spec89/v2.0.0/csv/bridges89_92.csv) supplies
   17 paired source rows on 15 normalized models, including republications and
   development-level systems with their existing qualifications.
2. The [reviewed DEC tables](classic-pdf-extraction.md) supply 48 columns on 24
   models with both SPECint92 and SPECrate_int92. These are the two explicitly
   distinct rows in each machine/OS column. Rate is normalized once to VAXen.
   Compiler, active CPU and copy-count equivalence remain unverified; the fit
   is an empirical source-column relationship, not a speed/rate identity.

This is a new explicitly labelled empirical bridge, not a reclassification of
ordinary SPECint92 source values as rate observations. No simulated score or
assumed processor-count multiplier creates a direct 89/rate pair.

| Edge | Models / source rows | Multiplier | Factor CI95 | LOMO model-center P95 |
| --- | ---: | ---: | --- | ---: |
| SPECint89 → SPECint92 | 15 / 17 | 0.9603866 | 0.942979–0.978902 | 8.61% |
| SPECint92 → rate-VAXen | 24 / 48 | 0.9965475 | 0.992226–1.000729 | 1.86% |
| Chained SPECint89 → rate-VAXen | No direct pairs | **0.9570709** | **0.939392–0.976940** | Not directly measurable |

Thus `estimated peak rate-VAXen = 0.9570709 × SPECint89` under the observed
bridge populations. The final interval is a joint bootstrap result, not the
product of the two marginal interval endpoints. It quantifies fitted-factor
uncertainty, not a 95% prediction interval for an individual old machine.
Transporting the DEC relationship to earlier architectures remains an assumption.
There is no supported same-column **base-rate** edge in these inputs, so this
experiment is peak-only; base estimates are not fabricated.

## Joint model experiment

The primary direct-rate model is retained as the comparison. The joint model
adds the SPECint89 classical pairs after translating their targets through the
two-edge bridge. It uses the unscaled source-pair stage, fixed equal-weight
geometric composites and the same model-balanced log-ratio estimator as the
[direct rate experiment](classic-rate-composite-fitting.md). Dhrystone versions,
Whetstone precision and LINPACK n=100 remain distinct. All repeat observations
remain; no residual threshold removes a source or machine.

For each pattern, compare rate-only, 89-only and joint cohorts, plus all
single-component baselines on identical tuples/folds. Triangles require three
compatible component-pair edges, as in the direct experiment. Every derived
row labels its target as either `observed_rate_target` or `estimated_89_target`.
A converted SPEC89 target is never presented as a rate measurement.

For bootstrap CI95, jointly resample normalized model keys from the union of
both bridge edges and the classical cohort, using 10,000 draws and seed
20260926. A model present in several places receives the same resampling weight.
Each draw refits both edge factors and the classical factor, applying one shared
bridge multiplier to every SPEC89 target. Empty-edge/cohort draws are rejected.
This retains shared calibration uncertainty rather than averaging it away as
though each converted observation had an independent conversion error.

Leave-one-model-out removes the test model from **both bridge edges and the
classical fit**. Errors against actual rate measurements are reported separately
from agreement with converted SPEC89 targets. Only the former provides observed
rate validation; the latter is a consistency diagnostic against estimated
labels. There are no direct rate measurements for the newly added old machines,
so this experiment does not validate their inferred throughput end to end.

The joint bootstrap uses the union of bridge and fitting keys. Consequently its
rate-only confidence endpoints can differ slightly from the earlier bootstrap
that resampled only fitting models. Point factors and held-out errors are
unchanged. Unknown shared publication lineage and configuration effects remain
outside the conditional interval.

## Coverage and observed-rate holdouts

| Composite | Rate-only → joint models | Rate-only P95 | Joint P95 on the same observed-rate models |
| --- | ---: | ---: | ---: |
| Dhrystone 1.1 + LINPACK | 25 → 32 | 24.78% | 29.59% |
| Dhrystone 2.1 + LINPACK | 25 → 32 | 27.45% | 33.44% |
| Dhrystone 1.1 + Whetstone native | 5 → 6 | 44.69% | 43.57% |
| Dhrystone 2.1 + Whetstone native | 6 → 7 | 41.57% | 40.68% |
| Whetstone native + LINPACK | 8 → 9 | 9.07% | 17.02% |
| Whetstone DP + LINPACK | 20 → 21 | 21.01% | 25.91% |

These are all six patterns that gain SPEC89 observations. The remaining patterns,
including every three-family combination, currently gain none. Full results and
baseline comparisons are in [the machine-readable summary](data/classic/spec89-rate-summary.csv).

The seven extra Dhrystone/LINPACK models are DECstation 3100, DECstation
5000/200, HP 9000/720, HP 9000/730, HP 9000/750, Sun SPARCstation 1+ and
Sun SPARCstation 2. They contribute 86 additional tuples with Dhrystone 1.1
and 89 with version 2.1; these are multiple observations/combinations, not that
many independent machines.

For Dhrystone 1.1 + LINPACK, the joint classical factor is 1.380390
(CI95 1.284257–1.489006), compared with the direct factor 1.326444. Its P95
agreement error on the seven inferred SPEC89 model targets is 40.40%, separate
from the 29.59% error on measured rate targets. Version 2.1's joint factor is
1.415281 (CI95 1.318737–1.523830), with inferred-target P95 41.49%.

The joint path achieves the intended expansion of historical coverage. Its
higher observed-rate holdout error for most affected combinations is a tradeoff
to report, not a failed experiment or grounds for rejecting the added evidence.
The direct-rate model remains a diagnostic control; the lowest error on that
narrower population is not the sole selection criterion for a historical model.
Neither coefficients nor observations are selected by residual magnitude.

Greater source and hardware diversity is a plausible explanation for the change.
However, these errors are evaluated on the same measured-rate machines: they
show the effect of the shifted calibration on that population, not a direct
measurement of variance among the added older systems. An age-dependent
variance increase is not yet established, and source/configuration effects,
bridge assumptions or matching problems could also contribute. The [selected
research criteria](../docs/methods.md#evaluating-broader-historical-coverage)
require coverage and error diagnostics to be interpreted together. Numerical
fits and uncertainty definitions are unchanged by this interpretation update.

## SPEC89-only hardware estimates

The bridge also produces **179 source-record estimates on 93 normalized model
keys**, independently of whether two classical benchmark families are available.
Reference-definition rows are excluded. Each record preserves its reported
SPECint89, record ID and source URL and labels its result as a two-edge estimate.
Original source qualifications remain in full derived provenance, including any
uncertainty already attached to the historical result.

The compact [estimate table](data/classic/spec89-rate-estimates.csv) retains the
source record ID for lookup in the immutable SPEC89 evidence and the normalized
source-record dataset. Its interval columns are named `factor_ci95_target_low`
and `factor_ci95_target_high`: these are the reported score multiplied by the
factor interval, not individual prediction bounds. Estimates for much older
architectures outside the calibration cohorts require additional validation.

## Reproduce and validation

```sh
UV_CACHE_DIR=/tmp/uv-cache MPLCONFIGDIR=/tmp/cpushowspeed-mpl \
  uv run --no-sync cpushowspeed classic spec89-rate-fit
```

Inputs: source-pair `pairs.csv` and `vectors.jsonl`, normalized SPEC records and
the archived native integer bridge. Options `--input-root`, `--spec-records`,
`--native-bridge`, `--output`, `--bootstrap` and `--seed` are documented by CLI help.

Outputs under `data/derived/classic/spec89-rate-fit/`:

- `bridge-evidence.csv`, `bridge-summary.csv`: source-linked edge observations,
  individual fits and chained factor uncertainty.
- `observations.csv`: all classical components, source evidence, original target
  and assigned VAXen target with measured/estimated labels.
- `summary.csv`, `predictions.csv`: separate observed/inferred-target validation
  and all matched single-score baselines.
- `spec89-estimates.csv`: full source provenance and all eligible score conversions.
- `joint-scatter.png/.svg`: all six affected patterns, separate measured points
  and inferred triangles, direct/joint lines and conditional factor CI95.
- `audit.json`: source/code checksums, direct-overlap audit, route and settings.

Compact bridge evidence/summary, model summary, estimate table and audit are
retained under `research/data/classic/spec89-rate-*`. Bulk observations and
predictions remain derived.

Validation: **57 rate-only factors and observed-rate held-out P95 values** match
the preceding direct experiment to relative tolerance 1e-10. New synthetic tests
check chained-factor multiplication, removal of held-out models from both edges,
shared-model covariance and preservation of shared uncertainty when inferred
observations repeat. The full suite passes **95 tests**.
