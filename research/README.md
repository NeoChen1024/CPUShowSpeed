# Research index

Start with the [overview](overview.md), then follow the four research tracks.
The [machine-readable registry](model-registry.json) and [generated catalog](catalog.md)
record metric identities, datasets, model dependencies and every document's role.
Reports distinguish measured evidence, derived estimates and proposed work.

## Four primary tracks

| Track | Reading guide | Principal result owner |
| --- | --- | --- |
| VAXen reference | [Unit and value types](tracks/vaxen.md) | [Methods](../docs/methods.md#vax-throughput-convention) |
| SPEC92–2026 integer rate | [Modern chain](tracks/spec-rate.md) | [Rate calibration](spec95-spec2026-rate-fitting.md), [annual results](annual-rate-vaxen.md) |
| SPEC89 scavenging | [Recovery and bridge](tracks/spec89.md) | [Two-edge bridge and joint fits](spec89-rate-bridge.md) |
| Classical benchmarks | [Pre-SPEC extension](tracks/classical.md) | [Direct rate composites](classic-rate-composite-fitting.md), [indirect/joint experiment](spec89-rate-bridge.md) |

## Shared inputs and fitting update

[Input migration and fitting review](input-unification-fitting-review.md) records source parity, execution-count exclusions and before/after coefficients.

## Source resource audit

[Field and runtime-resource audit](spec-resource-field-audit.md) records full integer disclosure coverage, resource anomalies and the count-aware refit, with the initial audit retained as history.

## Source evidence

- SPEC: [early archives](spec-early-archives.md), [CPU92 rate expansion](spec92-archive-expansion.md),
  [SPEC89 snapshot](spec89-curated-snapshot.md), [Helman supplement](spec89-helman-worksheet.md),
  [hardware dates](spec89-hardware-years.md), [89/92 paired-score review](spec89-cpu92-scatter.md).
- Classical: [source acquisition](classic-benchmark-collection.md),
  [prior work](classic-spec-literature.md), [DEC/SSCL/Tomari tables](classic-pdf-extraction.md),
  [initial hardware overlaps](classic-spec-overlap.md).
- Chronology: [CPU SKU release catalog](cpu-sku-chronology.md) (built, not yet used by the timeline).
- Earlier reconstruction: [mix/timing observations](early-benchmark-evidence.md),
  [OCR sample checks](chandra-timesharing-sample.md), [historical data contract](data/historical/README.md).

## New sparse calibration experiment

[Per-benchmark network fitting](classic-network-fitting.md) jointly estimates
individual coefficients from incomplete observations, with explicit clock
scaling and single/two-family/full-availability holdouts.

## Historical analyses and storage

[Archive index](archive/README.md) identifies retired speed-era analyses and
commands. Their files stay at stable paths. SPEC89 source evidence is actively
reused by the historical bridge; the original modern speed pipeline remains retired.

[Classic snapshots](data/classic/README.md) and [historical observations](data/historical/README.md)
are machine-readable evidence/results. Large raw documents, DocIR, derived tuples
and figures remain outside Git. Original values, citations and qualifications
must survive every conversion; Markdown is not the sole numerical data store.

## Maintenance

[Cleanup inventory](cleanup-inventory.md) records duplicated code, command/data
dependencies and provisional generated-artifact dispositions. It is an audit,
not authorization to remove historical evidence.

[Calibration cleanup implementation](calibration-cleanup.md) records the current
shared statistics policy, preparation-only commands and parity checks.

[Schema cleanup inventory](schema-cleanup-inventory.md) maps designs made obsolete
by the [data schema](../docs/data-schema.md) to migration steps; nothing is removed by it.

- [Gibson / ADP bridge preparation](instruction-mix-bridge.md): source definitions and classical-overlap review queue; no fitting yet.

The [SPEC95/CPU2000 overlap audit](spec95-spec2000-overlap-audit.md) explains
cross-generation cohort losses using field-level blockers and original disclosures.

- [Unified historical and SPEC rate timeline](unified-vaxen-timeline.md) describes the last working
  timeline; it is not reproducible after the 2026-10-02 removal of diagnostic experiments.
