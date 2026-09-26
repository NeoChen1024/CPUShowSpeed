# Research methods

The active quantitative method is the [SPEC CPU92–CPU2026 integer-rate
fit](../research/spec95-spec2026-rate-fitting.md). This document states the
rules for extending and reviewing it. No manual instruction-mix reconstruction
or general conversion from unrelated historical benchmarks has been
implemented.

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
selected cohort. Do not treat one edge's interval as the uncertainty of the
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
