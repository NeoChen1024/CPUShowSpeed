# Joint speed/rate predictors of rate-VAXen

Computed and reviewed: 2026-09-29.

## Research question

Can using SPECspeed and SPECrate together improve prediction of the project's
existing **SPEC92 integer-rate VAXen** target? This experiment retains the
independent speed and rate chains and adds three fixed predictor choices:

| Method | Predictor x | Inputs required |
| --- | --- | --- |
| speed_only | S | speed |
| rate_only | R | rate |
| equal_geometric | sqrt(S * R) | both |

Each fits `older_rate = k * x`. The geometric predictor has equal fixed weights,
is homogeneous of degree one, and does not redefine the VAXen unit. Weights are
not optimized. Base and peak use separate fits. Both native scores are from the
same newer suite generation, with that generation's own numerical scales;
the fitted coefficient supplies the scale conversion.

## Independent observed targets

For each adjacent pair from CPU92/95 through CPU2017/26, the target is an
**actual older-generation rate submission**. Predictors are newer-generation
speed and rate submissions. All three disclosure URLs must be distinct.
CPU92 rate targets are normalized by `25500 / 604800` for direct VAXen checks.
Later edges validate prediction of the observed older suite's native rate;
they have **no directly observed VAXen target**. Their exported
`observed_target_vaxen` is empty. No modern rate-chain estimate is manufactured
as a measured training target.

Hardware must match on all three sides of the triangle, using the existing
hardware-near matcher: normalized system and processor keys, chip count,
clocks within 1%, equal parsed memory, and no known core/thread-per-core
contradiction. This is an automatic candidate match, not a complete audit of
software or runtime workers. Raw target/predictor scores, disclosure URLs,
source hashes, OS/compiler and configuration fields remain in the tuple export.
Repeat submissions and every eligible combination remain present. Exclusions
record structural conflicts or missing scores; no residual cutoff is used.

## Identical cohorts and missing-input tests

Within each edge and base/peak mode, all three methods use the **same complete
triples** for calibration and evaluation. The speed-only method masks rate;
the rate-only method masks speed. Each mask has its own fitted coefficient,
so dropping an input never silently reuses or renormalizes the joint coefficient.
Tests verify that a hidden input is never read by the predictor.

This is an availability experiment on common-case machines. It does not prove
transport to a machine for which rate or speed was never measurable/published.
It also sacrifices coverage: the CPU95/2000 overlap has only one processor
model with a complete triple. All its coefficients and errors remain absent;
repeating that model's submissions does not increase independent model count.
The threshold is three processor models, leaving at least two for each fold.

## Weighting, holdouts, and uncertainty

Within each system/configuration, take the median of log(target/predictor),
then the median across systems sharing the processor/chips/clock configuration,
then average across configurations. This retains the existing modern ratio
estimator. For evaluation, **all configurations of a normalized processor key**
leave together, including all evidence for that key on upstream rate edges.
This is stricter than the preceding experiment's configuration-only holdout.

Primary P95 is the linear 95th percentile across processor-model errors:
median configuration log residual within model, then `100 * abs(exp(residual)-1)`.
Secondary observation P95 and within-model spread remain separately named.
Tuple counts are not independent sample sizes. Model identity is based on the
current processor normalization, not an asserted complete architecture taxonomy.

10,000 bootstrap replicates use a common multinomial weight for each processor
model across local speed/rate predictors, base/peak and every upstream edge.
All configurations and paired observations of that model share the weight.
Within-configuration medians stay fixed. Replicates with an empty relevant
edge are invalid for that route; valid counts are exported. Complete replicate
arrays preserve cross-model/route covariance for later consumers.
CI95 measures conditional coefficient uncertainty, not an individual-machine
prediction interval or a bound on unmeasured historical transport bias.

## Current results

There are **318 mode-specific eligible triples** across five edges: 24 supported
method/mode fits and six insufficient-model rows. The tables below compare
whole-processor-model held-out P95 errors on identical tuples.

### Base

| Input generation → observed target | CPU models | Tuples | Speed-only P95 | Rate-only P95 | Equal geometric P95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| CPU95 → CPU92 rate | 7 | 31 | 19.02% | 19.14% | 19.08% |
| CPU2000 → CPU95 rate | 1 | 2 | insufficient | insufficient | insufficient |
| CPU2006 → CPU2000 rate | 6 | 31 | 98.23% | 21.92% | 48.99% |
| CPU2017 → CPU2006 rate | 27 | 90 | 162.78% | 23.95% | 74.29% |
| CPU2026 → CPU2017 rate | 21 | 41 | 321.74% | 9.06% | 105.24% |

### Peak

| Input generation → observed target | CPU models | Tuples | Speed-only P95 | Rate-only P95 | Equal geometric P95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| CPU95 → CPU92 rate | 7 | 31 | 15.20% | 15.35% | 15.27% |
| CPU2000 → CPU95 rate | 1 | 2 | insufficient | insufficient | insufficient |
| CPU2006 → CPU2000 rate | 6 | 31 | 103.59% | 20.13% | 54.48% |
| CPU2017 → CPU2006 rate | 8 | 29 | 157.17% | 13.82% | 72.93% |
| CPU2026 → CPU2017 rate | 13 | 30 | 357.14% | 10.58% | 115.78% |

The CPU95 methods are nearly indistinguishable on the direct CPU92 target.
On the supported later-generation cohorts, rate-only has smaller P95 than
speed-only or the fixed equal-weight composite. Thus this experiment does not
show a benefit from the 50/50 combination. Speed is not useless evidence:
its single-input coefficients cover an alternative input pattern, but their
errors here show the limitations of an unconditioned throughput predictor.
Do not infer that all possible joint models fail or select/delete observations
according to these errors. Runtime resource differences are a candidate cause,
not a demonstrated causal explanation. Sample sizes are especially small on
the early edges and CPU2017 peak.

## Interpreting the VAXen coefficient

For input generation g, conversion follows:

```text
newer speed/rate predictor
  -> fitted older-generation native rate
  -> upstream rate-to-rate chain
  -> SPEC92 rate * 25500 / 604800
```

`coefficient_vaxen` is the local coefficient multiplied by that upstream rate
prefix. The prefix reuses all eligible rate-only pairs (same-OS CPU92/95 anchor,
hardware-near later edges), not just the complete local triples. Its point
estimator is the established rate estimator; bootstrap/holdout clusters in this
experiment are whole processor models. The common-cohort local rate-only fit
can differ from the established production rate coefficient because its cohort
is smaller. Existing production coefficients are not overwritten.

Do **not** multiply successive joint coefficients together: a local joint
predictor produces an older *rate* score, while the next joint predictor would
require both older speed and rate. The explicit rate prefix avoids that type
mismatch. There is no imputed intermediate speed. The empty CPU2000 joint fit
does not disconnect the already-supported rate backbone used for later inputs.

## Reproduction and artifacts

```sh
uv run --no-sync cpushowspeed bridge fit-joint-tracks
```

Versioned small snapshots:

- [Summary](data/spec/joint-tracks/summary.csv): local and VAXen coefficients,
  conditional CI95, coverage, target units and held-out errors.
- [Coverage](data/spec/joint-tracks/coverage.csv): candidate edge and triple counts.
- [Audit](data/spec/joint-tracks/audit.json): source/code/output hashes, fixed
  weights, random seed and interpretation limits.

Generated files under `data/derived/spec/joint-tracks/` include original-score
triples, rejection reasons, all held-out predictions, configuration residuals,
upstream evidence, correlated coefficient draws and the PNG/SVG comparison.
`holdout-predictions.csv` explicitly names the input mask and target evidence.
No public predictor manifest or timeline data is replaced.

## Validation performed

Seventeen SPEC-focused tests pass, including known synthetic geometric mappings,
hidden-input invariance, whole-model removal from upstream evidence, correlated
bootstrap cancellation, inconsistent triangle rejection, target-URL reuse and
insufficient-model handling. Registry validation covers 40 models and 69 documents.

A direct peak triple was independently checked against the cached source fields:

| Role | Reported score | Disclosure |
| --- | ---: | --- |
| CPU92 integer rate target | 1591 | [Netlib HP 712/60](https://www.netlib.org/performance/html/spec.7126ir.crint92.12_95.notes.html) |
| CPU95 integer speed input | 2.08 | [SPEC speed disclosure](https://www.spec.org/cpu95/results/res96q4/cpu95-960904-01271.html) |
| CPU95 integer rate input | 18.7 | [SPEC rate disclosure](https://www.spec.org/cpu95/results/res96q4/cpu95-960904-01272.html) |

The CPU92 value was read from the raw detail's reported aggregate; CPU95 values
and distinct CINT95/CINT95rate labels were checked in the official cached bulk.
This verifies extraction for this example, not equivalence of its run settings.
The full tuple export retains all source identities; source bytes are unchanged.

## Next evidence needed

- Recover more complete CPU95/2000 matches; preserve the current insufficient
  result until independent processor coverage grows.
- Review runtime copies/threads and active resources before adding conditional
  resource terms or estimating a speed weight.
- Any learned weight needs nested hardware holdouts; fitting and selecting it
  on these same reported errors would bias the comparison.
- Older machines missing a benchmark need their own transport/coverage audit;
  a common-case masking test alone cannot establish that extrapolation.

## Investigated overlap shortage

The [SPEC95/CPU2000 audit](spec95-spec2000-overlap-audit.md) now separates naming
and RAM restrictions from enabled-resource conflicts, absent configurations and
an NC result. Candidate sensitivity counts do not replace the strict fit above.

## Relaxed matching follow-up

[The relaxed refit](spec95-spec2000-relaxed-fitting.md) admits RAM/name differences
and separately tests cross-platform CPU-clock matching at CPU95/2000. Both
scenarios support the previously insufficient local edge; their coefficients
and uncertainties are stored separately from this strict baseline.

## All-generation matching update — 2026-09-29

The implemented matcher now applies the selected policy at every adjacent
SPEC92–2026 boundary and to each newer suite's speed/rate pair. RAM + aliases is
the timeline default. Strict remains the comparison baseline; CPU + clock remains
a cross-platform sensitivity scenario at near-equal clock rates, without score
scaling. Known resource conflicts still exclude a pair. Existing reviewed lexical
alias rules are reused; no new fuzzy alias guesses were introduced.

All three bundles were rebuilt with 10,000 shared processor-model bootstrap
replicates. Strict contains 318 tuples and 24 supported method/mode rows;
RAM + aliases contains 537 tuples and 30 supported rows; CPU + clock contains
422,269 tuples and 30 supported rows. These are source tuple counts, not independent
CPU-model counts. Repeated submissions and all admitted tuples remain included.
The large cross-platform increase is not evidence of an equivalent increase in
independent information.

The full rate backbone keeps the CPU92/95 same-OS condition and uses each selected
hardware-matching policy. The timeline's local rate-edge CI is derived from
differences of aligned saved prefix log draws; full-route estimates use the saved
prefix or predictor draws directly. The earlier CPU95/2000-only sensitivity
snapshot in the linked report is historical; its standalone tables are not the
current all-generation coefficients.
