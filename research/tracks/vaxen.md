# Track 1 — VAXen reference and numeric types

VAXen has two parallel quantities, both setting the VAX-11/780 to 1 (user
decision 2026-10-03): **rate-VAXen**, its reference throughput under SPEC92
integer rate (`SPECrate_int92 × 25500 / 604800`), and **speed-VAXen**, one
SPECint92 speed point (the VAX-11/780 is the SPEC92 reference machine). They are
never converted into each other; classical, SPEC89 and mix estimates are
speed-VAXen.
The [README](../../README.md#the-unit-1-vax) gives the public formula;
[methods](../../docs/methods.md#vax-throughput-convention) owns the full convention.

| Numeric type | Meaning | Interpretation |
| --- | --- | --- |
| Reported suite score | Literal measurement under named suite/version/mode | Preserve original source and run configuration |
| Normalized observed rate | Reported SPEC92 rate multiplied by the defined constant | Same underlying rate observation in rate-VAXen |
| Observed SPECint92 speed | Reported SPECint92 / SPECbase_int92 | Equal to speed-VAXen by definition |
| Cross-suite estimate | Rate or speed inferred using its own chain's fitted coefficients | Conditional on matching and calibration population |
| Classical composite | Geometric index of declared benchmark scores and units | Not a measured VAX reference score |
| Manual reconstruction | Workload timing derived from instructions and hardware assumptions | Separate evidence, not an executed SPEC result |

The metric registry identifies benchmark versions, precision, matrix size and
base/peak distinctions. VAXen is a unit; the evidence class belongs to each
value. Two values carrying VAXen need not have equal evidential support.

Read [data provenance](../../docs/data-contract.md),
[scope](../../docs/scope-and-metrics.md), and
[whole-chain intervals](../spec95-spec2026-rate-fitting.md#conditional-whole-chain-confidence-intervals).
Factor CI95, held-out P95 and individual prediction intervals are different.
