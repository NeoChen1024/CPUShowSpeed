# Calibration cleanup and unified validation policy

Implemented and checked: 2026-09-27. Baseline: `d2e4329` plus the subsequent
[static inventory](cleanup-inventory.md). This report owns implementation/parity
results; [methods](../docs/methods.md#unified-weighting-and-error-policy) owns the
selected statistical definitions.

## What is now shared

| Module | Responsibility |
| --- | --- |
| `research_io.py` | CSV dialect policies and transitive local-code provenance hashes |
| `calibration.py` | CPU92 unit constant, geometric grouped estimator, quantiles, relative errors and equal-model error summaries |
| `calibration_edges.py` | Shared model resampling across one or several dependent bridge edges |
| `classic_values.py` | Source numeric parsing, LINPACK column interpretation and clock compatibility |
| `classic_vectors.py` | Exact-component pair/triple assembly |
| `classic_pair_data.py` | Classical pair eligibility and values |
| `classic_source_data.py` | Reviewed source vectors, OS identity and staged pairing |
| `classic_bridge_data.py` | Archived SPEC89/92 paired integer evidence |
| `research_plot.py` | Consistent figure export without changing scientific labels |

The original experimental modules remain callable for historical reproduction,
with compatibility imports where needed. Main rate and SPEC89 computations no
longer obtain reusable algorithms from the auxiliary pooled-native experiment.
The original source-fit wrapper's redundant 100-draw bootstrap followed by a
second bootstrap has been replaced with one shared implementation. CSV field
ordering, BOM support and CRLF/LF policies remain explicit; no raw-source newline
normalization was performed.

## Preparation is separate from experiments

```sh
uv run --no-sync cpushowspeed classic prepare-pairs
uv run --no-sync cpushowspeed classic prepare-sources
uv run --no-sync cpushowspeed classic rate-composite-fit
uv run --no-sync cpushowspeed classic spec89-rate-fit
```

Preparation commands use the existing default dataset paths, emit their own
`prepare-audit.json`, and run no regressions or plots. Their modules import
neutral data-building functions instead of fitting commands. The historical
`pair-fit` and `source-pair-fit` commands still provide their complete experiments.
The CLI retains those command names; no diagnostic command was silently removed.

New audits include `shared_code_sha256`, hashing the local static import closure.
This captures extracted helpers rather than only the top-level command file.
Old audit snapshots are historical records; their hashes are not edited to
pretend they were produced by the refactored implementation.

## Statistical unification and changes

The primary error is now consistently relative to the observed target:
`100 * abs(predicted / observed - 1)`. Every independent model/configuration
contributes one median log-residual center, and P95 uses linear interpolation
across those centers. Model-level fitting weight remains equal; the modern
system-to-processor-configuration grouping is retained as its independent-unit
contract. Classical models retain one normalized hardware model per group.

Modern SPEC previously used symmetric multiplicative error
`100 * (exp(abs(log(predicted / observed))) - 1)`. That disagreed with classical
relative error for underprediction. Both modern rate edges and the CPU92 anchor
now use the shared relative-error definition. New `model_center_p95_percent`
columns are in percent. Existing `heldout_p95_absolute_pct_error` columns retain
their legacy **fraction** storage convention for compatibility, but now contain
the relative-error statistic. They must be multiplied by 100 for display.

The environment diagnostic's pooled coefficient now uses the same per-model
median log-ratio centers as the primary estimator. Within a model, environments
receive their observed row share rather than an additional equal-environment
weight. Grouped/shrinkage methods retain their explicit environment offsets;
they are diagnostics, not corrections applied to primary historical estimates.

Every environment result now includes the same `model_center_p95_percent`.
Observation-level summaries use equal model weight and equal rows within a
model; they remain secondary statistics. Their inverse weighted-CDF quantile
is intentionally labelled separately from the primary center P95. Reporting
these different populations is useful, but they no longer serve as competing
unlabelled definitions of the primary P95.

Bootstrap CI95 continues to quantify coefficient uncertainty. Shared-edge
resampling remains joint; it is not replaced with independent errors merely to
make the APIs uniform. Versions and selected grouping keys remain explicit.

## Recomputed checks

[Machine-readable parity checks](data/maintenance/cleanup-parity.csv) show:

- `pair-fit/pairs.csv`, `source-pair-fit/pairs.csv` and `vectors.jsonl` rebuilt
  through the preparation-only path **byte-identically**.
- All **154** direct-rate comparison rows preserve existing factors, coefficient
  CI95 and core P95 values to tolerance 1e-11.
- All **171** SPEC89 joint/single-source comparison rows preserve those core
  numerical values to tolerance 1e-11. New dependency structure does not add
  observations or erase inferred-target qualifications.
- All **12** modern edge/scenario/mode factors and CI95 endpoints are unchanged
  to tolerance 1e-12. The complete chain's numeric fields are also unchanged.
- Modern P95 values intentionally change; the full before/after table is
  [error-policy-comparison.csv](data/maintenance/error-policy-comparison.csv).

Examples of the definition change, with fixed data and coefficients:

| Edge / scenario | Mode | Old symmetric P95 | New relative P95 |
| --- | --- | ---: | ---: |
| CPU92 → CPU95, same OS | base | 19.44% | 16.90% |
| CPU92 → CPU95, same OS | peak | 13.11% | 11.86% |
| CPU95 → CPU2000, strict | base | 21.98% | 20.27% |
| CPU2000 → CPU2006, strict | peak | 24.90% | 19.94% |

These reductions do not indicate better prediction; only the statistic changed.

For extended Whetstone DP + LINPACK, the v2 environment pooled model now matches
the primary direct fit's **21.0126% model-center P95**. Grouped and shrinkage
center P95 are 14.0528% and 12.3693%. Their equal-model observation P95 values
are 37.6589%, 22.6272% and 21.3451%, respectively. Do not compare the center P95
to the old environment-balanced observation P95 as though they were the same
quantity. The environment snapshots and command were removed on 2026-10-02 with the other
diagnostic experiments; they remain in Git history.

## Cleanup of artifacts

After successful reconstruction and parity checks, the temporary
`data/derived/cleanup-v2/` validation tree was removed: **33 files, 35,464,890
logical bytes**. The exact paths/hashes are in
[removed-validation-files.csv](data/maintenance/removed-validation-files.csv).
Latest primary artifacts were regenerated at their established paths. Source
PDFs, inventories, original measured records, reviewed tables and historical
research snapshots were preserved. Other optional diagnostic outputs have not
been declared disposable solely because backups exist.

## Validation

The full suite passes **103 tests**. New tests independently establish asymmetric
relative-error behavior, equal-model weighting under unequal observation counts,
pooled environment/main-factor agreement and CSV dialect/BOM behavior. Modern
P95 tests now use independent relative-error calculations; bootstrap and
coefficient expectations remain unchanged. Existing shared-edge covariance and
held-out-exclusion tests remain in the suite.
