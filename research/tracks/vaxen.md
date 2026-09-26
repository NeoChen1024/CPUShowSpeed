# Track 1 — VAXen reference and numeric types

The common unit is VAX-11/780 reference throughput under SPEC92 integer rate.
The [README](../../README.md#the-unit-1-vax) gives the public formula;
[methods](../../docs/methods.md#vax-throughput-convention) owns the full convention.

| Numeric type | Meaning | Interpretation |
| --- | --- | --- |
| Reported suite score | Literal measurement under named suite/version/mode | Preserve original source and run configuration |
| Normalized observed rate | Reported SPEC92 rate multiplied by the defined constant | Same underlying rate observation in VAXen |
| Cross-suite estimate | Rate inferred using fitted coefficients | Conditional on matching and calibration population |
| Classical composite | Geometric index of declared benchmark scores and units | Not a measured VAX reference score |
| Manual reconstruction | Workload timing derived from instructions and hardware assumptions | Separate evidence, not an executed SPEC result |

The metric registry identifies benchmark versions, precision, matrix size and
base/peak distinctions. VAXen is a unit; the evidence class belongs to each
value. Two values carrying VAXen need not have equal evidential support.

Read [data provenance](../../docs/data-contract.md),
[scope](../../docs/scope-and-metrics.md), and
[whole-chain intervals](../spec95-spec2026-rate-fitting.md#conditional-whole-chain-confidence-intervals).
Factor CI95, held-out P95 and individual prediction intervals are different.
