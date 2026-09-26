# Research methods

This document owns shared scientific rules for the [four research tracks](../research/overview.md).
The modern SPEC rate chain, classical rate composites and SPEC89 two-edge
bridge are implemented conditional estimates. Manual instruction-mix/SIMH
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

## Classical workload association diagnostics

`classic fit-spec92` implements exploratory candidate-cohort associations with
SPEC92 integer rate. These are not validated historical conversion factors.
It separates Dhrystone versions, Whetstone Fortran native-precision and DP
columns, LINPACK n=100, and SPEC base/peak. Whetstone's main MWIPS column must
not be labelled universally single precision. FP-heavy workloads versus
integer rate are cross-workload diagnostics.

Both scenarios require SPEC's reported CPU count to be one and reject known
classical processor counts other than one. This does not prove classical
concurrency, copies, OS/compiler or full configuration equivalence. The first
scenario requires known clocks compatible within 1%; the second additionally
allows missing clocks. Both reject known clock conflicts. RAM is not a filter.
All source rows and pair exclusions are retained; no score/residual threshold
selects measurements. Repeated submissions remain observations.

For each included pair, let `x` be the original classical score and
`y = SPECrate_int92 × 25500 / 604800` (or its base counterpart). Within each
normalized model group, take the median of `ln(y/x)`. The overall factor is
`exp(mean(model medians))`, so each model has equal total weight. This is a
unit-slope log-space ratio fit, not a freely estimated power-law conversion.
A separate free log-log slope diagnostic uses model median log x/y values
when at least three groups with x variation exist.

Resample model medians with replacement 10,000 times (default seed 20260926).
Report the 2.5/97.5 percentiles of the factor as conditional CI95. At least two
model groups are required; even then small-cohort intervals are fragile. The
CI excludes mismatching configurations, source bias, unknown concurrency and
workload transfer uncertainty; it is not a prediction interval.

For leave-one-model-out validation, refit using all other model centers and
measure `100 × abs(predicted/observed - 1)` on the held-out center. Report the
P95 across held-out models. Also calculate each held-out model's pair-level
P95 and report the maximum of these, retaining visibility of compiler and
submission spread. This latter statistic is **not** an overall pair P95.
Cartesian candidate pairs are not independent experiments; clustering mitigates
repeated-model weighting but cannot establish independence among related
models or shared source compilations.

### Fixed equal-weight composite validation

`classic composite-fit` consumes the complete-vector audit and fixes
`C = ((D / 1 DMIPS) × (W / 1 MWIPS) × (L / 1 MFLOPS))^(1/3)`.
Native and DP Whetstone are separate experiments. Only the multiplicative
coefficient `k` in `y = k C` is fitted. Each single-benchmark baseline fits its
own coefficient on **exactly the same tuple multiset and model groups**.
SPEC92 targets use rate-VAXen; SPEC89 targets remain separate native metrics.
The unit normalizers define an index, not a measured VAX reference machine.

Reuse the model-median log-ratio estimator and conditional model bootstrap
above. For each validation fold, remove every tuple of the held-out model
before fitting k. Keep fold coefficients, signed model-center errors, and
individual held-out tuple predictions. Repeated source measurements remain;
Cartesian combinations do not increase the number of independent model groups.
The fitted weights never change from one third each. Full-cohort coefficient
CI95 is not a held-out prediction interval or a significance test between
predictors. Comparisons across clock scenarios also change the model cohort,
so their error differences cannot isolate the causal effect of scaling.

## Selected classical bridge method

Decision date: 2026-09-26. Following the environment-model experiments, the
user selects **pooled, fixed equal-weight geometric composites with one fitted
multiplier per benchmark combination and SPEC target** as the primary classical
bridge research method. Environment grouping and shrinkage remain diagnostic
experiments, not corrections applied to the primary estimates.

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
The implemented [rate composite experiment](../research/classic-rate-composite-fitting.md)
provides pair/triple coefficients, model-bootstrap CI95 and matched single-score
baselines. The subsequent [SPEC89 rate bridge experiment](../research/spec89-rate-bridge.md)
adds explicitly estimated SPEC89 targets through two observed edges, native
SPECint89→SPECint92 and same-column SPECint92→integer-rate VAXen. It propagates
shared bridge uncertainty and separates holdout errors on observed rate from
agreement with inferred targets. These estimates are not observed rate scores.
The [pooled native integer experiment](../research/classic-pooled-fitting.md)
remains auxiliary; its target is a different scale.
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
