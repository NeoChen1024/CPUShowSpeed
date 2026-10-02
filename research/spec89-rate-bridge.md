# SPECint89 bridge to SPEC92 rate and joint classical fitting

Computed and reviewed: 2026-09-27. Recomputed on resolved systems: 2026-10-02
(method `spec89-two-edge-rate-joint-v2-resolved-systems`).

## Evidence path

No resolved system has both a SPECint89 result and a SPEC92 integer-rate result
in the built database, including the DEC source-column rate observations and
before restricting processor counts. The audit
records this result; it is not a claim about all surviving historical sources.

The implemented path therefore uses two separately observed edges:

`SPECint89 → SPECint92 → SPECrate_int92 × 25500 / 604800`.

1. The [archived integer bridge](data/spec89/v2.0.0/csv/bridges89_92.csv) supplies
   17 paired source rows on 15 resolved systems, including republications and
   development-level systems with their existing qualifications. They are
   extracted into scope `historical-spec:spec89-bridge`.
2. The [reviewed DEC tables](classic-pdf-extraction.md) supply 48 columns on 24
   resolved systems with both SPECint92 and SPECrate_int92. These are the two explicitly
   distinct rows in each machine/OS column. Rate is normalized once to VAXen.
   Compiler, active CPU and copy-count equivalence remain unverified; the fit
   is an empirical source-column relationship, not a speed/rate identity.

This is a new explicitly labelled empirical bridge, not a reclassification of
ordinary SPECint92 source values as rate observations. No simulated score or
assumed processor-count multiplier creates a direct 89/rate pair.

| Edge | Systems / source rows | Multiplier | Factor CI95 | LOMO model-center P95 |
| --- | ---: | ---: | --- | ---: |
| SPECint89 → SPECint92 | 15 / 17 | 0.9603866 | 0.942655–0.979452 | 8.61% |
| SPECint92 → rate-VAXen | 24 / 48 | 0.9965475 | 0.992201–1.000572 | 1.86% |
| Chained SPECint89 → rate-VAXen | No direct pairs | **0.9570709** | **0.938679–0.976961** | Not directly measurable |

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
two-edge bridge. It uses the `same_system` cohort (resolved system, no clock
scaling) of the direct experiment, fixed equal-weight
geometric composites and the same model-balanced log-ratio estimator as the
[direct rate experiment](classic-rate-composite-fitting.md). Dhrystone versions,
Whetstone precision and LINPACK n=100 remain distinct. All repeat observations
remain; no residual threshold removes a source or machine.

For each pattern, compare rate-only, 89-only and joint cohorts, plus all
single-component baselines on identical tuples/folds. Triangles require three
compatible component-pair edges, as in the direct experiment. Every derived
row labels its target as either `observed_rate_target` or `estimated_89_target`.
A converted SPEC89 target is never presented as a rate measurement.

For bootstrap CI95, jointly resample resolved systems from the union of
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

| Composite | Rate-only → joint systems | Rate-only P95 | Joint P95 on the same observed-rate systems |
| --- | ---: | ---: | ---: |
| Dhrystone 1.1 + LINPACK | 25 → 42 | 28.19% | 40.34% |
| Dhrystone 2.1 + LINPACK | 25 → 36 | 29.87% | 38.37% |
| Whetstone native + LINPACK | 8 → 9 | 12.16% | 19.87% |
| Whetstone DP + LINPACK | 20 → 32 | 13.06% | 23.13% |
| Whetstone SP + LINPACK | 19 → 30 | 14.45% | 18.49% |
| Dhrystone 1.1 + Whetstone DP | 20 → 31 | 30.55% | 27.38% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 20 → 31 | 12.84% | 17.53% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 20 → 25 | 15.87% | 14.71% |
| Dhrystone 1.1 + Whetstone SP + LINPACK | 19 → 30 | 11.27% | 13.63% |

Thirteen of the seventeen patterns now gain SPEC89 systems, including every
three-family combination with DP or SP Whetstone; the four patterns combining
Dhrystone with native Whetstone gain none. Full results and baseline comparisons are in
[the machine-readable summary](data/classic/spec89-rate-summary.csv).

The 17 added Dhrystone 1.1/LINPACK systems are DEC VAX 4000/300 and 4000/400,
VAXstation 3100/38, 3100/76, 4000 VLC and 4000/60, DECstation 3100 and
5000/20, /25, /125, /133 and /240, HP 9000/720, /730 and /750, and Sun
SPARCstation 1+ and 2. They contribute 41 SPEC89 target tuples; repeated
SPECint89 results of one system are separate tuples, not separate machines.

For Dhrystone 1.1 + LINPACK, the joint classical factor is 1.499819
(CI95 1.404085–1.603175), compared with the direct factor 1.367455. Its P95
agreement error on the inferred SPEC89 targets is 37.45%, separate from the
40.34% error on measured rate targets. Version 2.1's joint factor is 1.476001
(CI95 1.378734–1.581611), with inferred-target P95 37.76%.

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

### Changes from the name-matched run (2026-10-02)

The bridge edges are unchanged (17 rows / 15 systems and 48 columns / 24
systems; point factors identical; CI endpoints move in the fourth decimal
because the bootstrap now resamples resolved systems). The 89-only and joint
cohorts grew: Dhrystone 1.1 + LINPACK went from 7 to 17 SPEC89 systems, and
three-family patterns went from none to 5–11. The earlier matching used
normalized names and required an OS match between DEC columns and archive rows,
which SPEC89 rows do not carry; resolved-system pairing treats OS as a run
condition. The added pairs are automatic and not yet individually reviewed, so
their configuration equivalence is unverified.

## SPEC89-only hardware estimates

The bridge also produces **179 source-record estimates on 90 resolved
systems**, independently of whether two classical benchmark families are available.
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
MPLCONFIGDIR=/tmp/cpushowspeed-mpl .venv/bin/cpushowspeed classic spec89-rate-fit
```

Input: the built database (`data build`). Options `--database`, `--output`,
`--research-dir`, `--bootstrap` and `--seed` are documented by CLI help.

Outputs under `data/derived/classic/spec89-rate-fit/`:

- `bridge-evidence.csv`, `bridge-summary.csv`: source-linked edge observations,
  individual fits and chained factor uncertainty.
- `observations.csv`: all classical components, original target and assigned
  VAXen target with measured/estimated labels.
- `summary.csv`, `predictions.csv`: separate observed/inferred-target validation
  and all matched single-score baselines.
- `joint-scatter.png/.svg`: measured points and inferred triangles, direct/joint
  lines and conditional factor CI95.

Compact bridge evidence/summary, cohort summary, estimate table and audit
(database input digest, direct-overlap check, route and settings) are retained
under `research/data/classic/spec89-rate-*`.

Validation: both edges reproduce the earlier point factors and estimate count.
Synthetic tests (`tests/test_classical_fit.py`) check chained-factor
multiplication, removal of held-out systems from both edges, shared-system
covariance and preservation of shared uncertainty when inferred observations repeat.
