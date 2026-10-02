# Schema-driven cleanup inventory

Inventory date: 2026-10-02. Baseline commit: `20bdf68`. Static inspection only;
nothing has been moved, deleted or refactored. This inventory classifies designs
made obsolete by the [data schema](../docs/data-schema.md) and schedules their
retirement against its migration steps. The earlier
[code/artifact inventory](cleanup-inventory.md) (2026-09-27) remains the record
for duplicated statistics code and derived-artifact disposal.

## Method and scope

- All 274 Git-tracked files under `research/data/` and `docs/data/` (9.0 MiB)
  were checked for references from Python code and from Markdown/registry text.
- All 86 modules and 60 decorated CLI commands in `python-src/cpushowspeed/`
  were searched for identity, matching, date-lookup and I/O helper definitions.
- Model and document roles were read from the [registry](model-registry.json).

Reference search is textual: a missing reference is a lead, not proof of disuse,
and directory-level reads count as references.

## Findings

### No orphaned data

Every tracked data file is referenced by code or documentation except the 36
saved Usenet/source texts and the merge manifest inside the
[SPEC89 v2.0.0 package](data/spec89/v2.0.0/README.md). Those are source
evidence for that package, not orphans. Cleanup is therefore about duplicated
**designs**, not dead files.

### 1. Source registries (retire in migration step 1)

Six layouts describe acquired or candidate documents: `classic/acquisition.csv`,
`classic/pdf-acquisition.jsonl`, `classic/literature-sources.jsonl`,
`docs/data/early-benchmark-sources.csv`, `historical/year-*-sources.json`
(two passes) and `historical/cpu-sku-sources.json`; `year-document-reviews.csv`
and `year-expansion-documents.csv` add per-document review status. All map to
`source` rows (review status to `source.status` plus `review`). Producers must
write the new table before the old files are frozen.

### 2. Private identity and matching code (retire in step 2)

Thirteen functions decide identity or matching in different modules. They are
not all the same kind of logic:

| Kind | Functions | Disposition |
| --- | --- | --- |
| Entity identity (which processor/system/configuration) | `timeline_dates.cpu_key`, `spec_overlap._processor_key`/`_normalized`, `spec95_overlap_audit.candidate_system_key`/`candidate_processor_key`, `spec_rate_chain.config_key`, `classic_overlap.model_key`/`relaxed_key`, `classic_network_data.cpu_identity`, `classic_timeline.date_key`, `cpu_chronology.sku_key` | Become versioned `alias` rules read through `resolution`; delete private copies after parity |
| Pairing policy (which observations a fitter compares) | `spec_joint_tracks.match` (strict / ram-aliases / cpu-clock), `rate_convert._matching` | Stay in fitters as declared policies, re-expressed over `hw:` IDs and resolution fields |
| Run-condition or text normalization | `classic_source_data.os_key`, `spec_disclosure.canonical` | Stay; feed the observation `run` object |

Step 5b (2026-10-02) took the SPEC rate fitters off `spec_overlap._processor_key`
and `_normalized` system matching; `spec_rate_chain.config_key` now groups resolved
processor keys. `spec_inputs` still uses the private key for the speed overlap
audit and timeline estimates until steps 5c–5d.

Alias tables with their own formats (`classic/mix-candidate-aliases.csv`, SPEC89
`aliases.csv`, `system_regex` in `timeline-year-overrides.csv` and
`hardware-date-evidence.csv`) migrate to `alias`. The SPEC89 package keeps its
own file as a versioned external snapshot; only an adapter reads it.

### 3. Date lookups (retire in steps 3–4)

Five date tables (`cpu-release-proxies.csv`, `cpu-sku-chronology.csv`,
`hardware-date-evidence.csv`, `timeline-year-overrides.csv`,
`submission-date-reviews.csv`) are read by four modules with separate selection
code: `classic_timeline`, `mix_timeline`, `unified_timeline` and
`historical_candidates`. All become `date_event`/`review` rows and one
`chronology_selected` view. `apply_cpu_release_proxy` and `CPUChronology` are
removed once the timeline reads that view with year parity.

Status 2026-10-02: steps 3–4 converted all five, plus `spec/hardware-date-exclusions.csv`,
`cpu92-cpu95-reviewed.csv` and `classic/mix-candidate-aliases.csv`, into curated
`date_event` and `review` rows; the built view is `result_chronology`. The legacy
files are frozen (the curated tables are canonical) and are deleted with their
readers when step 5 rebuilds the timeline and fitters; `mix-candidate-aliases.csv`
is still read by `classic_mix`.

### 4. Date-pass logs (archive any time; no code consumer)

Fifteen former `research/data/historical/year-*` files (about 0.6 MiB), now in
[`data/archive/date-passes/`](data/archive/date-passes/README.md), are records of
completed review passes: `year-cpu-*`, `year-expansion-*`, `year-review-batch1*`
and `year-wikipedia-*`. No code reads them; only
[hardware-year-evidence](hardware-year-evidence.md) and the
[historical data README](data/historical/README.md) cite them. Moved on 2026-10-02 to
`research/data/archive/date-passes/<pass>/`; both documents were updated.
`year-document-reviews.csv` is excluded: `historical_candidates` reads it.

### 5. Observation formats (retire in step 5)

Benchmark values currently live in the input catalog
(`benchmark-observation-v1`, derived), `historical/observations.jsonl` (curated),
`classic/mix-study/mix-records.csv`, the SPEC89 CSV package and the derived
historical-timeline `configurations.csv`/`observations.csv` aggregation. Step 5
emits `benchmark-observation-v2` for all of them; the aggregation becomes a view.

The input catalog is documented as the shared interchange, but most consumers
still read derived intermediate files directly:

| Intermediate file | Modules reading it directly |
| --- | ---: |
| `classic/overlap-spec/spec-records.jsonl` | 14 |
| `spec/cpu92-rate/cpu92-rate-records.csv` | 13 |
| `classic/overlap-spec/classical-records.jsonl` | 11 |
| `classic/overlap-spec/candidate-pairs.csv` | 11 |
| `classic/mix-study/mix-records.csv` | 5 |

`candidate-pairs.csv` is a name-based pairing product; under the schema it is
replaced by `resolution` plus accepted `alias` rows. Step 5 must switch these
readers to the built database, not only the modules that already accept
`--input-catalog`. This is the largest single porting cost in the migration.

### 6. Already obsolete regardless of the schema

- **I/O helpers** (checked 2026-10-02): `classic_overlap.read_csv`/`write_csv`
  already delegate to `research_io` with explicit encoding/newline policies.
  `spec89_build` keeps its own writer because it emits UTF-8 with BOM for the
  versioned SPEC89 package; replacing it would change tracked bytes. Both are
  left for the pipeline rewrite rather than changed now.
- **Legacy timeline text exports**: `plot timeline --text-exports` writes the
  pre-Parquet JSONL/CSV; no current reader was found.
- **Ad hoc coverage audit**: `cpu_chronology.spec_coverage` reimplements record
  loading to test matches; it becomes a `resolution` query in step 2.

### 7. Diagnostic experiments (removed 2026-10-02)

The user chose neither porting nor freezing: all 20 registered diagnostic
models were removed so that a better-suited set can be designed on the new
schema. Removed together:

- Commands and modules: `classic fit-spec92`, `pair-fit`, `composite-overlap`,
  `composite-fit`, `source-pair-fit`, `source-diagnostics`, `environment-fit`,
  `pooled-fit`, `mix-network-fit`, `compare-targets`; `bridge compare-tracks`,
  `fit-joint-tracks`, `refit-95-2000` (13 modules).
- Their 74 tracked output files, 11 reports, registry models/datasets and
  speed-only metrics.

`classic source-diagnostics` was not a registered model but belonged to the same
diagnostic group and was removed with it. Preparation (`prepare-pairs`,
`prepare-sources`) and the primary rate, SPEC89 bridge and network fits are
unchanged. `plot timeline` is knowingly left broken: it consumed the joint,
relaxed and mix-network outputs and will be rebuilt on the schema. Everything
removed remains recoverable from Git history. Their 12 test modules (and one
environment-model test in `test_calibration_policy.py`) were missed in that commit
and removed on the same day; the test suite imports cleanly again.

## Retirement procedure

For every item:

1. The replacement exists and passes `data validate`.
2. Parity: fitted coefficients, intervals, timeline record IDs, VAXen values and
   selected years are unchanged, or each difference is listed as intended.
3. Consumers switch; the old reader is deleted; documentation links and the
   registry are updated in the same change.
4. Superseded curated files move to `research/data/archive/` with their pass name
   rather than being deleted. Raw sources and source snapshots are never removed.

## Proposed order

| When | Item |
| --- | --- |
| Done 2026-10-02 | Date-pass logs archived to `research/data/archive/date-passes/` |
| Step 1 | Source registries |
| Step 2 | Identity functions and alias tables; `spec_coverage` |
| Steps 3–4 | Date tables and the four date-selection paths |
| Step 5 | Observation formats, historical aggregation, `--text-exports` |
