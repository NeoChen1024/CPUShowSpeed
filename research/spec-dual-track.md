# Independent SPEC speed and rate calibration

Computed and reviewed: 2026-09-29.

## Decision and scope

Retain two targets: task completion speed and reported-system throughput.
Base/peak is a separate dimension. The existing rate prediction CLI and timeline
continue to use rate-VAXen. This experiment exports **SPECint92-equivalent speed
points** separately; it does not rename them as rate-VAXen or publish a new
single-core series. A formal speed-VAXen unit and timeline integration remain
follow-up work.

Speed does not imply one core. CPU2017 permits threading in speed workloads;
CPU2026 adds language threading and uses all available cores on its speed
reference system. Rate and speed can also differ in workloads and rules.
See the official [CPU2017 overview](https://www.spec.org/cpu2017/Docs/overview.html#Q14)
and [CPU2026 overview](https://www.spec.org/cpu2026/docs/overview.html#Q23).
These facts motivate further resource checks; they do not establish the cause
of any fitted residual.

## Reproduce

```sh
uv run --no-sync cpushowspeed bridge compare-tracks
uv run --no-sync cpushowspeed classic compare-targets
```

The first command uses cached CPU95–2026 bulk files, CPU92 Netlib speed details
and the existing parsed rate archive. The second uses the same classical
observations, source-column vectors, reviewed candidate joins and Gibson/ADP
attachments as the existing sparse network. No new download is required.

Small results are versioned under `research/data/spec/dual-track/` and
`research/data/classic/dual-track/`. Full records, paired observations,
bootstrap arrays, provenance and PNG/SVG figures are generated under matching
`data/derived/spec/dual-track/` and `data/derived/classic/dual-track/` directories.

## Collection and validation

CPU92 has 305 cached integer-speed disclosures, including three base-only
results. All 305 parse successfully. Each input is SHA-256 checked; the six
benchmark ratios reproduce its aggregate within rounding tolerance, and
available cached issue-summary scores agree with the detail scores. Every
record has at least one independently stored summary check. The parser handles
reference-time columns, later base/peak layouts, and explicit missing peaks.
It never fills a missing peak with base.

Modern bulk rows are selected by exact integer speed/rate metric name. Positive
scores and usable processor/chip identity are required by the existing matcher;
raw and usable counts are exported so omitted records remain visible. All
repeat submissions are retained.

| Generation | Usable speed disclosures | Usable rate disclosures |
| --- | ---: | ---: |
| CPU92 | 305 | 274 |
| CPU95 | 548 | 773 |
| CPU2000 | 1,374 | 2,481 |
| CPU2006 | 9,287 | 15,039 |
| CPU2017 | 10,270 | 13,359 |
| CPU2026 | 75 | 176 |

Bulk exports do not expose a consistent runtime-thread or copy-count field.
Enabled threads per core describes configuration, not measured worker count.
Parallel/auto-parallelization flags are inventoried without interpreting them as
thread counts. CPU92 parsed rate details do retain per-benchmark copies, but
these new cross-track diagnostics do not yet control for them.

## Independent speed chain

The estimator is shared with the rate fitter: median log ratios within system
and processor-configuration groups, then equal-weight mean across configurations.
It estimates `older = k * newer`, without an intercept. Eligibility uses the
existing normalized system/CPU/chip key, clocks within 1%, equal parsed memory,
and no disclosed core/thread-per-core contradiction. It does not establish
compiler, OS, or runtime-thread equivalence. RAM relaxation and reviewed alias
expansion are not silently introduced by this experiment.

The table reports leave-one-processor-configuration-out **model-center P95**,
in percent; submission pair counts are not independent sample sizes.

| Edge (older / newer) | Base configs | Base k | Base P95 | Peak configs | Peak k | Peak P95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cpu92 / cpu95 | 18 | 37.6043 | 19.91% | 18 | 41.3256 | 16.68% |
| cpu95 / cpu2000 | 11 | 0.0912979 | 19.55% | 9 | 0.0957746 | 12.46% |
| cpu2000 / cpu2006 | 15 | 156.324 | 20.29% | 12 | 155.424 | 12.44% |
| cpu2006 / cpu2017 | 114 | 8.57257 | 7.32% | 107 | 8.66168 | 6.97% |
| cpu2017 / cpu2026 | 23 | 2.79696 | 56.01% | 16 | 2.7822 | 45.68% |

All five edges connect for base and peak. CPU2017–2026 is the least stable edge
in this dataset and needs disclosure-level threading review. It remains in the
results. No residual threshold removes observations. The nonadjacent-generation
audit finds no candidate pairs under this matcher, so no alternate chain closure
can currently be tested.

`speed-chain.csv` contains cumulative SPECint92-equivalent coefficients and
conditional CI95. Full-chain sampling uses 10,000 multinomial bootstrap draws
over the union of processor-configuration keys: each shared key gets the same
weight on every edge. Medians within configurations are fixed as in the existing
rate statistics. Bootstrap vectors are saved, and interval endpoints are never
multiplied. These are fitted-coefficient intervals, not individual prediction
intervals or bounds on cross-architecture systematic bias.

## Same-hardware speed/rate diagnostics

`speed-rate-pairs.csv` keeps all candidate pairings; `speed-rate-diagnostics.csv`
fits hardware-near cohorts separately by generation, chip count and base/peak.
Its `factor_old_per_new` is explicitly **native rate points / native speed
points**, not VAXen, a core count, or a universal speed-to-rate conversion.

For CPU92 one-chip peak pairs, the native ratio is approximately 23.70, close
to the reference rate score 23.717647. Later generations show strong dispersion
even within chip-count strata. Chips alone do not control for cores, copies,
threading or software. This supports keeping both measurement targets, while
retaining the historical DEC bridge as a conditional empirical relationship.

## Classical and instruction-mix comparison

Both targets use the same sparse log-WLS implementation, equal model weight,
node/family/variant balancing, unknown-target nodes, and whole-model holdouts.
Runs cover reported clocks and the existing conditional Dhrystone/Whetstone
linear-clock assumption; LINPACK and instruction mixes are never clock-scaled.
Each scenario runs with and without SPEC89, and with and without mix attachments.
The existing six classical variants and two mix variants remain distinct.

Speed anchors are actual SPECint92 observations, including DEC source columns
and newly parsed Netlib details. The speed historical route uses only
`SPECint89 -> SPECint92`. Rate uses the existing two-edge historical bridge.
The bridge is refitted inside joint bootstrap and model holdouts. Derived
SPEC89 labels remain separate from observed targets.

On **32 common observed hardware model groups**, with linear-clock handling and
SPEC89 enabled, all-available-input network holdouts yield:

| Model | Speed target P95 | Rate target P95 |
| --- | ---: | ---: |
| classical | 55.28% | 56.21% |
| classical_mix | 55.05% | 55.97% |

The similar errors support retaining both calibrations; they do not establish a
statistically significant winner or target equivalence. Common model groups
can still contain different configurations, source observations and available
benchmark subsets. The CSV reports node counts and group identities. Increasing
coverage with valid observations is not a failure when dispersion grows.

## Remaining checks before public speed prediction

- Inspect actual threading/copies in matched disclosures, especially CPU2026;
  distinguish requested workers from available hardware resources.
- Establish the formal speed reference/unit contract and add a target selector
  to prediction and timeline consumers only after that review.
- Expand CPU92 sources and matching review without selecting by fitted residual.
- Assess historical transport bias; calibration CI95 alone cannot validate
  machines without direct target measurements.

Existing rate outputs are not overwritten. The old archived speed pipeline
remains a historical implementation; this experiment reuses current statistics
and retains explicit target identities.

## Follow-up: joint predictors

The [joint speed/rate experiment](spec-joint-tracks.md) now compares speed-only,
rate-only and equal-geometric predictors against distinct older-rate disclosures.
It reports common-case input masks and explicit local-to-rate-prefix routes.
