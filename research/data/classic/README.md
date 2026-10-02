# Classic collection and overlap snapshots

`acquisition.csv` inventories downloaded sources and hashes, not measurements.

`mix-study/source-hunt.csv` records the expanded Gibson/ADP source search;
`source-hunt-acquisition.csv` records downloaded PDF hashes and locations.
`additional-observations.csv` contains ten page-verified vendor table cells
(six absolute ratings and four relative cells), independently of the generated
Longbottom inventory. It is not yet consumed by fitting. Preserve reported
units, variant names, processor counts and reference identities; blank dates
and processor counts mean unknown. `fit_eligible=false` means equivalence has
not been approved. See the [mix study](../../instruction-mix-bridge.md).

`mix-study/sc3-observations.csv` records twelve page-verified scores from the
1991 SC-3 paper. Gibson operations/s, Dhrystones/s and millions of Whetstones/s
remain distinct reported units; `reported_per_mhz` preserves the source ratio
column (Whetstone uses MWIPS/MHz * 1000). Empty fields mean unspecified.
`dinkiac-mix-weights.csv` and `dinkiac-simulation-results.csv` preserve the
1971 reconstruction model, seven weight/timing groups and all 33 result cells
(31 durations and two source dashes). These simulations are not measurements.
`ocr-review-checks.json` records arithmetic and OCR/transcription cross-checks.
These curated files remain separate from model inputs pending integration and
variant/configuration review; no fitted coefficients were changed.

`overlap-coverage.csv` and `overlap-audit.json` are compact outputs of
`cpushowspeed classic overlap-spec` (copies of `source-coverage.csv` and
`audit.json`). Full records remain in the ignored derived output directory and
are loaded by `data extract`. Pairing is by resolved system in the fitters; the
former name-based `overlap-summary.csv`/`overlap-models.csv` are archived in
[`../archive/name-pairing/`](../archive/name-pairing/README.md).
See the [overlap report](../../classic-spec-overlap.md) for coverage limits.

## Primary direct rate composite experiment

`rate-composite-summary.csv`, `rate-composite-target-coverage.csv` and
`rate-composite-audit.json` preserve the direct SPEC92 integer-rate experiment.
Factors produce VAXen; base/peak and pair/triple variants remain separate.
See [method and validation](../../classic-rate-composite-fitting.md).

## SPEC89 to rate bridge experiment

`spec89-rate-bridge-evidence.csv`, `spec89-rate-bridge-summary.csv`,
`spec89-rate-summary.csv`, `spec89-rate-estimates.csv` and `spec89-rate-audit.json`
retain the two-edge bridge and joint-model experiment. Estimate intervals cover
coefficient uncertainty only; these rows are not historical rate measurements.
The compact estimate table omits bulk raw provenance, retaining stable source
record IDs and URLs. See [interpretation and reproduction](../../spec89-rate-bridge.md).

## Sparse per-benchmark network

`network-coefficients.csv`, `network-summary.csv`, `network-frequency-checks.csv`
and `network-audit.json` preserve the missing-data network experiment. Each
coefficient applies to its named metric/version/unit. Estimated hardware values
are not measured rate scores; intervals describe conditional calibration only.
See [method and validation](../../classic-network-fitting.md).

## Instruction-mix bridge preparation

`mix-candidate-aliases.csv` is the frozen input of the step-4 review import,
which turned it into open `system_link` reviews; it does not approve hardware
identity and no fitter reads it. `mix-study/weights.csv` and `audit.json`
snapshot `classic mix-inventory`. Full source listings including missing scores
remain in the generated `mix-records.csv`. See
[the preparation report](../../instruction-mix-bridge.md).

`mix-study/bridge-classical-fit-summary.csv` records exploratory `y=kx` factors
in classical-score units per mix KIPS, never VAXen, for the `resolved_system`
and `plus_pending_links` scenarios, each with its own group counts, bootstrap
CI95 and shared relative-error policy. `bridge-classical-coverage.csv` counts
pairs, mix rows, classical results and systems per metric.
`bridge-spec89-target-coverage.csv` and `bridge-spec92-target-coverage.csv`
record direct-bridge feasibility (currently zero pairs), and the hand-written
`bridge-spec89-family-leads.csv` keeps a rejected-for-fitting CPU-family lead.
`bridge-audit.json` preserves the database input digest, seed and
interpretation boundaries.
