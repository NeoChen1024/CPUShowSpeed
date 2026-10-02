# Research methods

This document owns shared scientific rules for the [four research tracks](../research/overview.md).
The modern SPEC rate and speed chains, classical speed composites and the
one-edge SPEC89 → SPECint92 bridge are implemented conditional estimates. Manual instruction-mix/SIMH
reconstruction and a universal historical converter remain unimplemented.
The [registry](../research/model-registry.json) records exact model directions,
dependencies and artifact owners.

## Primary multiplicative assumption

Primary cross-benchmark calibrations assume `y = k × x`, passing through the
origin with no additive intercept. Estimate k through grouped log score ratios,
not ordinary least squares; each report defines its model/configuration groups.
The fixed log-log slope is one. Any freely fitted slope is a diagnostic and
must not silently replace the selected multiplicative estimator. For modern
adjacent suites, x is the newer score and y the older score. For classical
models, x is a declared score/composite and y the documented target. Figures
and data must retain this direction.

## Adjacent benchmark generations

Match published rate submissions from adjacent SPEC suites using system and
processor identity, chip count, clock, memory and any available core and
thread fields. Preserve both original submissions and disclosure URLs. A
processor alias alone generates a review candidate; it does not establish
identical hardware, OS, compiler or tuning. Exact run conditions must be
checked in detailed disclosures before promoting an automatic pair to a
reviewed configuration match.

The current fit takes the median of log score ratios within each system and
processor configuration, then the mean across configurations. Exponentiating
that mean yields the geometric old/new score factor. This keeps repeated
submissions visible while preventing them from multiplying independent fit
weight. Fit base and peak separately. Use leave-one-configuration-out errors
for prediction checks, and identify bootstrap intervals as conditional on the
selected cohort. All five edges use 10,000 configuration bootstrap resamples
with fixed seed and percentile intervals; the [combined interval table](../research/data/spec/fitting/integer-rate-edge-intervals.csv)
also records held-out p95 errors. Do not treat one edge's interval as the uncertainty of the
full chain. Look for independent nonadjacent or three-suite overlaps to test
the chained estimate.

## VAX throughput convention

The [SPEC CPU92 capacity method](https://www.spec.org/cpu92/specrate.txt)
sets the VAX-11/780's one-copy reference rate to `604800 / 25500`, about
23.71765. Thus one CPU92 integer-rate score point represents
`25500 / 604800` VAX-reference throughput units. Call a normalized value of
1 `1 VAX` and a value of N `N VAXen`, always labeling the benchmark mode as
**rate**. This is a workload-relative comparison, not an instruction-per-second
unit. Decimal SI labels such as `1k VAXen` and `26m VAX` are display formatting
only; stored values remain unprefixed numbers.

The [rate audit](../research/spec95-spec2026-rate-fitting.md) gives both the
CPU95-relative internal chain and the exploratory CPU92-anchored VAXen chain.
Keep its original scores, per-edge factors and source hashes with every
normalized estimate. Architecture-dependent overlap and limited CPU2026
coverage currently prevent treating a single factor as universal.

## Manual and archival evidence

To reconstruct early-machine throughput, select a named instruction mix with
weights `w_i`; map each operation to documented instructions or routines with
times `t_i`; account for addressing, memory, branch, precision and emulation
conditions. A simple mix has `T = sum(w_i * t_i)` and rate `1 / T` after unit
conversion. Reproduce published examples on several machines before using
the method for previously unmeasured hardware. Missing operations or timing
conditions remain missing evidence.

Original documents and archived observations can generate candidate machine
histories, but their score fields must not be silently substituted for SPEC
integer-rate submissions. The [source guide](sources.md) records collection
caveats and the [data contract](data-contract.md) records value, date and
provenance requirements.

The implemented `bridge bootstrap-rate-chain` command audits cross-edge
configuration/source overlap, then propagates 10,000 complete multiplier
vectors under a disjoint-cohort independence assumption. The
[rate audit](../research/spec95-spec2026-rate-fitting.md#conditional-whole-chain-confidence-intervals)
defines its pointwise CI scope and the stored replicate arrays. These quantify
conditional calibration sampling variation, not individual-machine prediction
error or shared systematic bias. `plot annual-rate-ci` propagates those shared vectors to yearly quartiles and
representative scores; its pale box envelopes and fixed-leader intervals
retain that conditional, pointwise interpretation.

## Classical model-median ratio estimator

Classical fits pair an original classical score or composite `x` with a target
`y` (for the primary route, `SPECrate_int92 × 25500 / 604800` or its base
counterpart). Dhrystone versions, Whetstone native/SP/DP columns and LINPACK
problem sizes stay separate; Whetstone's main MWIPS column must not be labelled
universally single precision. All source rows and pair exclusions are retained;
no score/residual threshold selects measurements. Repeated submissions remain
observations.

Within each normalized model group, take the median of `ln(y/x)`. The overall
factor is `exp(mean(model medians))`, so each model has equal total weight. This
is a unit-slope log-space ratio fit, not a freely estimated power-law conversion.

Resample model medians with replacement 10,000 times (default seed 20260926) and
report the 2.5/97.5 percentiles of the factor as conditional CI95. At least two
model groups are required; small-cohort intervals are fragile. The CI excludes
mismatching configurations, source bias, unknown concurrency and workload
transfer uncertainty; it is not a prediction interval.

For leave-one-model-out validation, remove every tuple of the held-out model,
refit on the other model centers and measure `100 × abs(predicted/observed - 1)`
on the held-out center. Cartesian candidate pairs are not independent
experiments; clustering mitigates repeated-model weighting but cannot establish
independence among related models or shared source compilations.

## Selected classical bridge method

Decision date: 2026-09-26. The user selects **pooled, fixed equal-weight
geometric composites with one fitted multiplier per benchmark combination and
SPEC target** as the primary classical bridge research method. No environment
correction is applied to the primary estimates.

For a declared set B of two or three distinct benchmark families, calculate
`C_B = exp(mean(log(score_b / unit_b)))` and fit `y = k_B,target × C_B` using
the existing model-balanced log-ratio estimator. Keep Dhrystone versions,
Whetstone precision variants and LINPACK matrix sizes explicit. Pair and triple
formulas have different coefficients; do not silently change the input set of
a single composite when measurements are missing.

Retain environments and submissions regardless of residual magnitude. Use the
same observation/provenance rules and declared unit interpretations; mixing
environments does not authorize arbitrary cross-environment score splicing.
Verified extraction/unit/identity problems may be corrected with an audit trail.
Clock scaling, where previously authorized, remains a labelled sensitivity
scenario rather than an inferred OS/compiler correction.

On 2026-09-27, the user selects **direct SPEC92 integer rate** as the primary
classical target, with base and peak separate. Normalize the reported rate by
`25500 / 604800` once, then fit the classical composite directly in VAXen.
The implemented [rate composite experiment](../research/classic-composite-fitting.md)
provides pair/triple coefficients, model-bootstrap CI95 and matched single-score
baselines. The subsequent [SPEC89 rate bridge experiment](../research/spec89-bridge.md)
adds explicitly estimated SPEC89 targets through two observed edges, native
SPECint89→SPECint92 and same-column SPECint92→integer-rate VAXen. It propagates
shared bridge uncertainty and separates holdout errors on observed rate from
agreement with inferred targets. These estimates are not observed rate scores.
The direct experiment shares the modern chain's rate unit; promoting its
classical coefficients into a general historical converter remains separate.

Report both factor uncertainty and held-out observation spread. Architecture,
software and workload sensitivity remain part of the observed discrepancy;
they are not claimed to be removed by geometric averaging. No low-residual
subset or environmental adjustment is chosen to make the history look smoother.

### Evaluating broader historical coverage

Decision date: 2026-09-27. The classical bridge research aims to represent a
broader historical hardware and source population. A higher held-out error or
wider factor interval after adding eligible evidence is not by itself a failed
experiment or a reason to reject the expanded cohort. Report coverage gains,
source/configuration diversity, factor changes and validation errors together;
do not select a historical model solely by its lowest error on the narrower
observed-rate cohort. Keep the direct-rate fit as a diagnostic control.

A higher error on the same observed-rate holdout models describes how the
expanded calibration changes predictions for that population. It does not
measure variability on the newly added old machines. Increased source diversity
and architecture/software differences are plausible contributors, but an
age-dependent increase in variance is not established by this comparison.
Systematic bias, matching errors and bridge assumptions also remain possible
and should be investigated without residual-based removal of valid evidence.

Keep coefficient CI95, held-out P95 error and individual prediction uncertainty
distinct. Historical breadth is an explicit research objective; predictive
limitations remain part of the reported result rather than an automatic veto
on including more diverse observations.

## Unified weighting and error policy

Selected 2026-09-27; implementation/parity evidence is in the
[calibration cleanup](../research/calibration-cleanup.md). Each independent
model/configuration has equal total fitting weight, using its median log ratio.
Modern system/configuration grouping and classical normalized model identity
remain declared grouping contracts, not extra submission-count weights.
No environment adjustment enters the primary historical estimates.

Primary P95 is the linearly interpolated 95th percentile of absolute relative
errors at independent model/configuration centers: `100 * abs(predicted/observed - 1)`.
The new canonical field is `model_center_p95_percent`. Historical classical
`loo_model_p95_percent` is the same statistic. Observed/inferred target groups in
the SPEC89 joint experiment remain separately evaluated using this definition.
Modern legacy `heldout_p95_absolute_pct_error` stores a fraction; the canonical
new field stores percent. Previous symmetric multiplicative errors are superseded.

Secondary observation P95 gives each model equal weight, then each observation
in that model equal weight; its weighted-CDF quantile is labelled explicitly.
It describes a different population from the primary center statistic and is
not substituted for it. Factor CI95 uses bootstrap quantiles and remains distinct
from both. One/multiple-edge bootstrap implementations share an engine while
retaining shared-model dependence.

## Sparse benchmark network experiment

The [network experiment](../research/classic-network-fitting.md) jointly fits
per-benchmark log coefficients and latent unanchored configuration values.
Targets fix observed rate-VAXen or qualified SPEC89-derived values. Unanchored
co-observations constrain relative coefficients; disconnected metrics remain
unidentified. This new experimental log-weighted-least-squares estimator is
distinct from the ordinary model-median ratio fit above. Weight is equal per
informative model, then per node, family and variant; repeated observations
contribute to the within-node/metric log median.

Dhrystone/Whetstone clock proportionality is an explicit scenario, restricted
to existing model matches with recognized compatible CPU identities. Unknown
clocks remain unscaled; unresolved/conflicting processor identities do not
authorize frequency-conflict conversion. LINPACK stays unscaled. Estimates use
the actual reported clock unless explicitly normalizing to a paired target.
Whole-model holdouts remove all accepted aliases and shared bridge evidence;
coefficient bootstrap samples retain shared calibration dependence.

