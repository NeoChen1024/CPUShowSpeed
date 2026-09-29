# SPEC source fields and execution-resource audit

Reviewed: 2026-09-29. The full integer disclosure refresh below supersedes the
acquisition coverage of the earlier bounded audit retained later in this report.

## Full disclosure refresh

All **54,014 indexed integer speed/rate results** across CPU95–CPU2026 now have
cached detail files. One additional positive bulk result absent from the integer
index was collected separately: [CPU2017-20170828-00068](https://www.spec.org/cpu2017/results/res2017q3/cpu2017-20170828-00068.html),
whose base and peak rate tables both declare 88 copies. Original bulk score
snapshots and source bytes remain unchanged. Acquisition metadata and hashes are
retained beside each cached document.

The full audit examined **54,015 integer disclosures** and made **164,062 hardware
crosschecks with zero contradictions**. The existing 261 resource review flags
remain; disabled cores and historical CPU-count semantics are not automatically
classified as errors.

Coverage of the **98,072 positive modern score observations**, counting base and
peak separately:

| Track / declaration status | Observations |
| --- | ---: |
| Integer rate: reported copies | 58,340 |
| Integer speed: reported threads | 17,757 |
| Integer speed: earlier tables without explicit thread counts | 21,971 |
| Integer speed: unparsed non-integer thread declarations | 4 |
| Missing disclosure for a positive modern score | 0 |

The four unparsed observations are base/peak for two HPE submissions. Their
selected result tables literally report `64i` and `88i`, and the recorded runcpu
commands contain the same suffix. These are retained as source strings, not
converted into 64/88 threads or inferred from enabled hardware. See the
[source-linked exceptions](data/resource-refresh/unparsed-thread-values.csv).
The parser now distinguishes unparsed declarations from absent fields and stops
CSV result-table interpretation before aggregate/metadata/compiler sections.

## Count-aware recalibration

The unified snapshot still contains **103,456 observations**. A full record
comparison found every non-execution field identical, including scores, units,
hardware, software, original source identity and raw score fields. All modern
execution records were enriched/reparsed; no benchmark score was rescaled.

Independent speed/rate fits, rate-chain intervals, all three joint matching
policies, the CPU95/2000 sensitivity experiment, classical and mix networks,
historical target controls and the timeline were rerun from the refreshed
snapshot. The existing rule excludes confirmed constant-count conflicts within
the same track; nonuniform or unresolved declarations remain provisional.

| Joint policy | Previous complete mode tuples | Updated |
| --- | ---: | ---: |
| Strict | 317 | 309 |
| RAM + aliases | 536 | 528 |
| CPU + clock | 422,268 | 421,988 |

These are combinations of source submissions, not independent CPU models.
Repeated submissions remain included; no residual-based filtering was added.

For the default RAM + aliases full-rate backbone, CPU95 coefficients are unchanged.
CPU2000 base changes by **−0.7984%**; CPU2006–2026 base by **−0.6876%**. CPU2000 peak
is unchanged; CPU2006–2026 peak changes by **−0.02459%**. Joint and speed-only
predictors have their own coefficients and coherent bootstrap intervals; these
percentages must not be substituted into those models.

### Reproducible records

- [Acquisition inventory](data/resource-refresh/acquisition-summary.json)
- [Audit totals and full evidence hash](data/resource-refresh/resource-audit-summary.json)
- [Positive-score runtime coverage](data/resource-refresh/positive-score-runtime-coverage.csv)
- [Unchanged score/identity verification](data/resource-refresh/observation-parity.json)
- [Joint cohort changes](data/resource-refresh/joint-cohort-changes.csv)
- [Default full-rate coefficients](data/resource-refresh/default-rate-factor-changes.csv)
- [All coefficient comparisons](data/resource-refresh/factor-changes.csv)
- [Per-model review](data/resource-refresh/model-review.csv)

Full per-result audit tables remain in `data/derived/resource-refresh/field-audit/`;
source snapshots are in `data/raw/spec/`. Before-state coefficient tables and the
input catalog are preserved in `data/derived/resource-refresh/before/`. The
[collection commands](../docs/spec-collection.md) and
[input/fitting workflow](input-unification-fitting-review.md#reproduction-and-validation)
own the reproducible commands. The comparison command accepts `--before` and
`--output` to keep this refresh separate from the earlier migration.

### Final output validation

The refreshed timeline contains **121,365 display records**, including the
unchanged **61,070 baseline/historical records**. Modern displayed results have
**zero `not_collected` runtime entries**; four speed estimates retain the
source's non-integer thread strings. See the
[export verification](data/resource-refresh/timeline-verification.json).

The coefficient comparison contains 2,739 table entries, of which 96 changed;
mirrored tables and chain prefixes mean these are not independent models. The
registry review marks six models updated, 30 numerically unchanged, two unchanged
definitions, two without a direct coefficient comparison, and one planned model.

Validation passed 32 SPEC tests, 25 timeline/storage tests, three input-contract
tests and the full generated-page JavaScript integration check. Browser loading
through darkhttpd rendered the graph and 200-row first page successfully. The
JavaScript predictor was compared with independent NumPy/CLI expectations for
255 historical input combinations and 86 SPEC cases. Registry validation and
render checks passed (41 models, 74 documents).

## Earlier bounded audit

The following sections and their `data/spec/field-audit/` tables describe the
initial, pre-guard sample audit. Their acquisition counts are historical; use
the refresh records above for current coverage and coefficients.

## Scope and reproducible outputs

All **105,973 bulk rows** and all bulk columns across CPU95–2026 are inventoried,
along with the project’s SPEC89 tables, DEC SPEC92 table, Netlib CPU92 rate tables
and Netlib CPU92 speed adapter. Resource checks and detailed extraction target
integer speed/rate, the tracks used by this project. Floating-point bulk columns
are inventoried; their detailed run configurations have not been reviewed.

- [Field inventory and current consumers](data/spec/field-audit/field-inventory.csv)
- [Generation coverage](data/spec/field-audit/generation-summary.csv)
- [Resource review flags](data/spec/field-audit/resource-anomalies.csv)
- [Bulk/detail and CSV/HTML crosschecks](data/spec/field-audit/detail-crosschecks.csv)
- [Execution-count coverage by mode](data/spec/field-audit/execution-coverage.csv)
- [Sampled fitting tuple resource vectors](data/spec/field-audit/matching-resource-samples.csv)
- [Resource completeness of fitting tuples](data/spec/field-audit/matching-resource-coverage.csv)
- [Netlib speed parsing and source identities](data/spec/field-audit/cpu92-speed-coverage.csv)
- [Reviewed sample manifest](data/spec/field-audit/sample-manifest.json)
- [Source-checked numerical findings](data/spec/field-audit/verified-findings.csv)
- [Source hashes and audit totals](data/spec/field-audit/audit.json)

Full parsed per-benchmark resources are generated in
data/derived/spec/field-audit/disclosures.jsonl. Reproduce with:

    uv run cpushowspeed spec audit-fields

Add --fetch-samples to restore reviewed sample documents. The sample selects
first/last URLs within suite/track, specific resource anomalies, and the first
admitted RAM-aliases triple for each generation edge. It is bounded,
not random, and does not establish that every full submission has been reviewed.

## Resource quantities must stay separate

| Quantity | Meaning / current use |
| --- | --- |
| Enabled chips | Hardware enabled for the run; matching guard |
| Enabled cores | Enabled resources, possibly below installed capacity; matching guard when known |
| Cores/chip | Chip capacity; cannot be multiplied into an assumed enabled-core count |
| Hardware threads/core | Hardware/SMT configuration; not benchmark worker count |
| Rate copies | Concurrent benchmark processes; retain benchmark and base/peak separately |
| Speed benchmark threads | For CPU2017, allowed OpenMP threads; not measured active cores or OS thread count |
| CPUs orderable | Product sales options, not tested processor count |
| CPU92 Number of CPUs | Legacy count used in the matcher's chips slot; chip equivalence remains unverified |

The official [CPU2017 glossary](https://www.spec.org/cpu2017/Docs/result-fields.html#Copies)
defines copies and threads separately. Allowed threads do not establish that
every benchmark actually uses them all. CPU95/2000/2006 speed details inspected
here lack the corresponding structured benchmark-threads column. Absence, or
single-copy speed semantics, does not justify imputing one thread.

CPU92 rate already retains per-benchmark copies and mode ranges. Its speed parser
reads legacy CPU count and leaves cores/SMT unknown. Recovered SPEC89 speed scores
generally lack full runtime disclosures. The archived throughput89 table is not
silently pooled into the speed bridge.

## Checked findings

1. **Unknown copies are mainly an acquisition/integration gap.** Bulk CSVs lack
   runtime copies/threads. Previously the timeline requested these nonexistent
   fields from bulk rows. The new adapter reads cached CSV selected-result tables
   or legacy CPU95/2000 HTML, retaining benchmark, mode, count, locator and hash.

2. **Low enabled counts can be deliberate.**
   [Bull POWER5+ CPU2006](https://www.spec.org/cpu2006/results/res2007q1/cpu2006-20070215-00481.html)
   reports one core, one chip, two cores/chip. Its OS notes describe removal of
   15 cores and disabling SMT. Replacing enabled cores with chip capacity would
   corrupt the tested configuration. Across integer bulk rows, 256 positive-score
   records have enabled cores below chips × cores/chip. Only sampled cases have
   been individually explained; the remainder are review candidates.

3. **One positive-score source has an internal topology inconsistency.**
   [HP ProLiant ML150 G3 / Xeon 5050](https://www.spec.org/cpu2000/results/res2006q3/cpu2000-20060901-07172.html)
   says four cores, one chip, two cores/chip, with Hyper-Threading enabled.
   Bulk and HTML agree; the benchmark table reports four copies. This may confuse
   logical threads with cores: an interpretation, not a verified correction.
   Preserve the numbers and flag topology. This ID appears in neither current
   joint triples nor rate-backbone pair exports for any of the three policies.

4. **Zero counts belong to redacted non-compliant sources.** CPU2017
   20200119-20586 (rate) and 20200119-20589 (speed) have zero cores and hardware
   threads/core. Both lack a positive aggregate and are excluded by current
   ingestion. Four field flags do not mean four zero-core timeline systems.
   [Original rate report](https://www.spec.org/cpu2017/results/res2020q1/cpu2017-20200119-20586.html).

5. **Speed threads can vary within a submission.**
   [CPU2026 20260810-00424](https://www.spec.org/cpu2026/results/res2026q3/cpu2026-20260810-00424.html)
   reports 192 cores, one chip, two threads/core. Selected CSV rows report base
   threads 384 and peak threads from 1 to 384. Preserve the benchmark-level
   vector; hardware threads/core = 2 does not describe this concurrency.

6. **An admitted fitting tuple mixes rate concurrency.** The RAM-aliases base
   CPU2006 → CPU2017 tuple uses
   [CPU2006 20070331-00717](https://www.spec.org/cpu2006/results/res2007q2/cpu2006-20070331-00717.html)
   with 8 copies, versus
   [CPU2017 20161026-00003](https://www.spec.org/cpu2017/results/res2017q2/cpu2017-20161026-00003.html)
   with 1 copy. Its speed input 20161026-00004 reports 1 thread. Hardware admission
   therefore does not establish equivalent execution concurrency. This tuple is
   retained and flagged; no score is multiplied/divided by copies, and no
   residual-based removal has been performed. It is direct evidence that fitted
   scale factors can confound suite changes with execution configuration.

The audit currently contains **224 cached integer disclosures**, **442 hardware
field crosschecks**, and **zero crosscheck mismatches**. That shows faithful
extraction for the checked subset, not absence of errors in published sources.
There are **261 flags**: 257 capacity/enablement differences and four nonpositive
fields from two redacted reports. Flags are not independent submissions.

## Important information not controlled by current fits

| Dimension | Current use / gap |
| --- | --- |
| Cache size, sharing, external cache | Preserved raw and exposed as context; not a pairing guard |
| Memory capacity | Strict matching uses parsed capacity; RAM + aliases deliberately relaxes it |
| Channels, DIMM population/ranks/speed, interleave/NUMA | Raw memory/notes; not modeled by capacity parsing |
| Nominal versus max/turbo frequency | Matching uses nominal or text fallback; no frequency score scaling; max/power policy unmatched |
| Disabled cores, partitions, affinity, SMT | Bulk enabled fields give partial information; detailed notes require review |
| Compiler, flags, PGO, libraries, pointer size | Compiler retained in pair provenance; no general equality guard |
| OS, firmware, huge pages, power settings | Same-OS constraint at CPU92/95 backbone only |
| Auto Parallelization / Parallel | Source flag, not actual thread or copy count; not a pairing guard |
| Benchmark copies / threads | Extracted where cached; not yet a pairing guard |

RAM + aliases and CPU + clock do not establish equivalent software, memory
subsystems or runtime configurations. Unknown resource fields do not currently
reject a match. Bootstrap CI95 does not cover all these systematic differences.

The RAM-aliases cohort contains 537 tuples: 180 have at least one unknown core
count and 272 have at least one unknown hardware-threads/core field. Only two
tuples currently have all three declared runtime quantities collected. This is
coverage, not equivalence: even collected counts can disagree, and old speed
reports may not contain a structured thread count at all.

## Changes landed and remaining limits

- Added resumable spec fetch-resources for speed and rate disclosures.
- Added spec audit-fields, field inventory, execution extraction and review flags.
- Timeline labels enabled hardware separately from benchmark copies/threads;
  uncollected details and absent parsed fields have explicit labels.
- Joint points show speed-input and rate-input resources separately.
- Cache, memory, compiler, pointers and parallel flags appear in expandable context.
- Legacy CPU92 counts and disputed topology are labeled without rewriting values.
- Scores, fitting cohorts and coefficients are unchanged by this audit.

A complete runtime-configuration audit still needs the uncollected disclosures.
After acquisition, compare per-benchmark vectors on actual matched pairs and
evaluate explicitly defined resource policies. Do not discard points by residual
size or fill copies from cores/SMT.
