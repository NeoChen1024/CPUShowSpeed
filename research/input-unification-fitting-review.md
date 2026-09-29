# Shared input migration and fitting review

**Full-disclosure update (2026-09-29):** [Resource refresh](spec-resource-field-audit.md#full-disclosure-refresh)
records current runtime coverage and the count-aware refit. Numerical tables in
this report's original narrative describe the preceding experiment; linked
coefficient files now contain the refreshed results.

Reviewed: 2026-09-29.

## Source and interface changes

The [input catalog](../docs/input-catalog.md) is the shared JSONL contract.
SPEC95–2026 bulk, CPU92 rate and CPU92 speed adapters now live in one module.
Fitting, resource inspection and timeline readers reuse normalized identities,
scores, enabled hardware and declared execution evidence. Historical adapters
share classical metric/unit extraction; PDF vectors, recovered SPEC89/92 and
Gibson/ADP retain their own source context in the common envelope.

The snapshot has 103,456 positive observations. Source views retain non-score rows
and source-specific context, including all 3,794 classical, 724 historical SPEC
and 88 reviewed-vector records. Before the execution policy changed, 53,961 SPEC
records and all classical normalized score maps matched the previous implementation
exactly. Live versus snapshot reads also preserve execution metadata and source
views. [Parity record](data/input-unification/normalization-parity.json).

The snapshot does not replace reviewed pairing/alias tables. It does not make
multiple publications independent, merge Dhrystone versions, merge Whetstone
precisions, or infer worker counts from CPU topology.

## Execution-policy change

The [resource audit](spec-resource-field-audit.md) found an admitted CPU2006/2017
base tuple with 8 versus 1 rate copies. Shared pair generation now excludes only
a mode with a confirmed conflict between two reported *constant* counts for the
same track/quantity. Raw scores and unfiltered ratios remain exported. Unknown
counts and nonuniform benchmark vectors stay provisionally admitted and labeled.
Copies and threads are never treated as interchangeable units.

The guard applies to independent speed/rate pairs and to the older/newer rate
inputs of each joint tuple. All joint predictor methods retain a common cohort.
No score is divided by copies or scaled by frequency. The one confirmed joint
tuple is excluded in each policy: strict 318 → 317, RAM + aliases 537 → 536,
CPU + clock 422,269 → 422,268. Original submission observations remain present.

The acquisition fingerprint and optional input-snapshot identity are saved with
joint models. Adding or changing disclosures invalidates the old model snapshot.
This is still a partial execution audit, not confirmation that all remaining pairs
use equivalent runtime or software configurations.

## Which coefficients changed?

[Complete coefficient comparison](data/input-unification/factor-changes.csv)
contains 1,482 table entries, including mirrored unit/chain exports and legacy
tables. 43 entries changed; these are not 43 independent fitted models.
[Per-model decisions](data/input-unification/model-review.csv) cover all 41
registered models.

| Family | Result |
| --- | --- |
| Defined VAX unit | Unchanged |
| CPU92→95, CPU95→2000, CPU2000→2006 rate edges | Recomputed; unchanged |
| CPU2006→2017 rate edge | Base changed; peak unchanged |
| CPU2017→2026 direct rate edge | Unchanged; full base VAXen chain changes through its prefix |
| Independent speed edges and chain | Recomputed; unchanged |
| SPEC89→SPEC92→rate-VAXen bridge | Source/definition unchanged; existing coefficients retained |
| Classical sparse network | 24 coefficients recomputed; unchanged |
| Mix+classical network | 32 coefficients recomputed; unchanged |
| Classical/mix speed-versus-rate target comparison | 112 coefficients recomputed; unchanged |
| Modern speed-only / matched-rate / joint predictors | Affected base factors and coherent intervals recomputed |
| CPU95/2000 matching sensitivity | Recomputed; unchanged |
| Earlier classical diagnostics | Source numeric parity established; legacy coefficient tables retained |

Three registered outputs do not have a direct coefficient-table comparison:
the annual derived view, classical-source diagnostic output, and Tomari diagnostic.
The current unified timeline is regenerated from updated factors; the other two
remain legacy snapshots with unchanged source inputs, not newly validated fits.
Planned timing reconstruction has no coefficient to update.

### Current default: RAM + aliases

These coefficients multiply the native predictor to obtain VAXen. The joint
predictor is sqrt(speed × rate); its matched-cohort rate-only control differs
from the full rate backbone.

| Input / method (base) | Previous k | Updated k | Change |
| --- | ---: | ---: | ---: |
| SPEC2017 speed-only | 84354.669560 | 86252.188569 | +2.2495% |
| SPEC2017 matched-cohort rate-only | 5587.728370 | 5275.012841 | −5.5965% |
| SPEC2017 joint | 21709.697379 | 21329.360892 | −1.7519% |
| SPEC2017 full rate backbone | 5285.344428 | 5219.648188 | −1.2430% |
| SPEC2026 joint | 102171.432403 | 100901.452943 | −1.2430% |
| SPEC2026 full rate backbone | 12324.359256 | 12171.168851 | −1.2430% |

All SPEC2026 base predictor routes inherit this changed prefix. Peak coefficients
remain unchanged in this migration. Strict and CPU + clock have their own
before/after rows; the default figures above must not be substituted into them.

## Reproduction and validation

Before-state CSV snapshots were preserved in data/derived/input-unification/before.
The versioned comparison preserves old/new scalar values and full row identities.

    uv run cpushowspeed inputs build
    uv run cpushowspeed --input-catalog data/derived/inputs bridge fit-joint-tracks --matching-policy ram-aliases
    uv run cpushowspeed --input-catalog data/derived/inputs classic network-fit
    uv run cpushowspeed --input-catalog data/derived/inputs classic mix-network-fit
    uv run cpushowspeed inputs compare-factors
    uv run cpushowspeed --input-catalog data/derived/inputs plot timeline

Independent rate generation/anchor/chain and speed comparison commands were also
rerun, along with all three joint policies and the classical target comparison.
The current page/calculator consumes the updated bundle, not old central values
with new uncertainty bounds. Source records are not deleted for large residuals.

Remaining work is source acquisition and configuration review: the common schema
makes missing or incompatible inputs visible, but cannot establish unreported
thread counts, compiler equivalence, NUMA placement or memory behavior.
