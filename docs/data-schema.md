# Data schema design

Status: **design, 2026-10-02; not implemented.** This document owns the target
data model and its migration plan. Until each step lands, the current formats in
the [data contract](data-contract.md), [input catalog](input-catalog.md),
[timeline contract](timeline.md#shared-record-contract) and
[historical observation contract](../research/data/historical/README.md) remain
authoritative. Interpretation rules (evidence classes, date meanings, parallelism
quantities) stay in the data contract; this document defines where they are stored.

## Why redesign

The project grew one file format per research pass. Three problems now block
further work:

1. **No shared identity.** "Which machine / which processor" is decided
   separately in every table: `configuration_id` (`classic-<hash>`,
   `spec:<gen>:<id>:<mode>`), exact CPU text plus clock (`cpu-release-proxies.csv`),
   `system_regex` (`timeline-year-overrides.csv`, `hardware-date-evidence.csv`),
   free-text `machine`, heuristic `processor_key`/`system_key` in the input
   catalog, mix regex aliases, SPEC89 `aliases.csv` and the new `sku_key`.
   Every new evidence type adds another matching rule inside code.
2. **Dates are scattered.** CPU proxies, the SKU catalog, hardware date events,
   regex year overrides and submission reviews all state "subject S had event E
   on date D according to source X", in five different layouts. Pass logs
   (`year-*-changes.csv`, `*-targets.csv`, audits) sit beside canonical data.
3. **Provenance is redefined per table.** At least six source registries exist
   (`classic/acquisition.csv`, `pdf-acquisition.jsonl`, `literature-sources.jsonl`,
   `early-benchmark-sources.csv`, `year-*-sources.json`, `cpu-sku-sources.json`),
   with different names for the same fields (`source_path`/`relative_pdf`,
   `source_blake3`/`pdf_blake3`/`snapshot_sha256`, `reviewed_on`/`review_date`).

The input catalog (`benchmark-observation-v1`) and the timeline Parquet export are
comparatively sound; the redesign extends them rather than replacing them.

## Principles

- **Separate subjects, evidence and judgements.** Entities (processors, systems,
  configurations) are things. Observations and date events are evidence about
  things. Aliases and reviews are judgements linking or qualifying evidence.
- **One table per concept.** A new pass adds rows, not a new file layout.
- **Every claim carries one provenance block** that points to a `source` row.
- **Identity resolution is data.** Matching rules are versioned and their
  outputs are materialized and auditable, never re-implemented per consumer.
- **Raw is immutable; canonical is reviewable; derived is reproducible.**
- **Unknown stays unknown.** Missing values keep their missing-status reason.

## Layers and storage

| Layer | Contents | Location | In Git |
| --- | --- | --- | --- |
| Raw | Downloaded PDFs, SPEC caches, web snapshots | Existing raw stores and mirror | No |
| Curated | Hand-reviewed or small parsed tables: sources, entities, aliases, date events, reviews, curated observations | `research/data/schema/` | Yes |
| Extracted | Deterministic adapter output from raw (for example ~100k SPEC observations) | `data/derived/schema/` | No |
| Built | SQLite database joining curated + extracted, plus resolution and selection views | `data/derived/schema/cpushowspeed.sqlite` | No |
| Products | Fits, estimates, timeline projection | Existing derived paths | Small audits only |

Curated tables are CSV when flat and JSONL when a row needs nested conditions.
Each table has a declared schema (`research/data/schema/schema.json`: columns,
types, enums, required fields, foreign keys). Extracted tables use the same
schemas and record their adapter code hash and raw input hash.

Commands (planned): `cpushowspeed data validate` checks every curated and
extracted table; `cpushowspeed data build` writes the SQLite database and
materialized views; both are read-only with respect to curated data.

## Shared conventions

### Identifiers

`<kind>:<slug>` with a stable, human-readable slug, never reused after deletion:
`src:wikipedia-xeon-skylake`, `sku:intel-xeon-gold-6130`, `fam:intel-itanium-2`,
`sys:dec-vax-11-780`, `evt:00412`. Extracted rows use deterministic IDs derived
from their source identity (for example `obs:spec-cpu95-res99q3-03712-base`).
Existing IDs are kept as `legacy_ids` during migration.

### Dates

Every date is two columns: `date` (ISO text at stated precision) and
`date_precision` ∈ {`year`, `quarter`, `month`, `day`}. Quarter dates are written
`YYYY-Qn`. `date_raw` retains the source text. No component is invented.

### Provenance block

Every evidence or judgement row has: `source_id`, `locator` (page/table/row/result
id as text), `verification` ∈ {`original_page_visual_check`, `web_text_checked`,
`parsed_unreviewed`, `search_excerpt_only`, `citation_only`} and `reviewed_on`.
`verification` describes what was checked, not certainty.

### Missing values

Empty means "not stated by the source". Where the reason matters, a sibling
`*_status` column uses the existing vocabulary (`not_reported`, `not_collected`,
`unparsed_reported_value`, `partially_parsed`).

## Tables

### `source`

One row per identified document, page revision or dataset snapshot.

| Column | Meaning |
| --- | --- |
| `source_id` | Primary key |
| `kind` | `pdf`, `web_page`, `wiki_revision`, `spec_result`, `bulk_archive`, `usenet_post`, `book`, `dataset` |
| `title`, `url`, `final_url` | Identity and retrieval address |
| `local_path`, `hash_algo`, `hash` | Immutable local copy (BLAKE3 for mirror PDFs, SHA-256 for snapshots) |
| `revision` | Wiki revision or document version |
| `retrieved_on` | Retrieval date |
| `date`, `date_precision` | Publication date of the source itself |
| `provenance_class` | `primary_original`, `vendor`, `contemporary_secondary`, `modern_secondary`, `benchmark_org` |
| `work_id` | Groups copies/reprints of one work, so they are not counted as independent |
| `status` | `lead`, `acquired`, `partially_reviewed`, `reviewed` |

The pre-SPEC lead catalog becomes `source` rows with `status = lead`; its
`next_step` moves to a `note` column.

### Entities

| Table | Key | Main columns |
| --- | --- | --- |
| `processor_family` | `fam:` | vendor, family, generation/codename |
| `processor_sku` | `sku:` | family_id, vendor, model, variant suffix, base_clock_mhz |
| `system_model` | `sys:` | vendor, family, model |
| `configuration` | `cfg:` | system_id, processor ref (sku or family), chips, cores, threads/core, clock, memory, with `*_status` |

A processor reference may stop at the family when the source names only a family
("Intel Itanium 2", "SPARC64 V"). Family-level date events are family launches
and are never presented as SKU releases. Configurations are extracted per source
record; two configurations are not merged by name similarity.

### `alias`

Maps source text to an entity.

| Column | Meaning |
| --- | --- |
| `alias_id` | Primary key |
| `entity_kind`, `entity_id` | Target |
| `match_kind` | `exact_text` or `rule` |
| `text` / `rule_id` | Exact normalized text, or a versioned rule (for example `sku-key-v1`) |
| `scope` | Field and source family it applies to (for example `spec.processor`) |
| `constraints` | Extra checks, for example `clock_within: 0.02` |
| `status` | `accepted`, `candidate`, `rejected` |
| provenance | `source_id` of the evidence and review fields |

Rules live in code with a version; `data build` materializes a `resolution`
view (raw text → entity, alias, rule version, status, failed constraint). Every
consumer reads `resolution`; none re-implements matching. Ambiguous text
(several SKUs, family-only) resolves to the family or to nothing, explicitly.

### `observation`

`benchmark-observation-v2` = the current v1 envelope plus `source_id`,
`configuration_id`, `metric_id` and `verification`. Values, units, raw records,
execution vectors and software context are unchanged. SPEC observations are
extracted; curated historical observations (`observations.jsonl`) and future
KIPS/Auerbach/VUP values are curated rows of the same schema. A `metric` table
merges registry metrics with the input-catalog metric strings
(`cpu95:integer:rate:base`).

### `date_event`

| Column | Meaning |
| --- | --- |
| `event_id` | Primary key |
| `subject_kind`, `subject_id` | `processor_sku`, `processor_family`, `system_model`, `configuration` or `observation` |
| `event_type` | `announcement`, `release`, `first_delivery`, `availability`, `hardware_availability`, `software_availability`, `test`, `publication`, `withdrawal` |
| `date`, `date_precision`, `date_raw` | As above |
| `claim_status` | `reported`, `announced_future`, `inferred_proxy` |
| provenance | Source block |

This single table replaces `cpu-release-proxies.csv`, `cpu-sku-chronology.csv`,
`hardware-date-evidence.csv` and the year rules in `timeline-year-overrides.csv`.
SPEC's HW Avail, Test Date and Published fields become extracted events on the
observation's configuration. Announced future dates (for example a
"Q4 2026" SKU in a 2026-10 page revision) are `announced_future`, not releases.

### `review`

| Column | Meaning |
| --- | --- |
| `review_id` | Primary key |
| `target_kind`, `target_id` | `alias`, `date_event`, `observation`, `pair` |
| `decision` | `accept`, `reject`, `needs_review` |
| `reason`, provenance | Why, and on what evidence |

Replaces `submission-date-reviews.csv`, pair approvals and rejected-date notes.
A rejection never deletes evidence; selection views read decisions.

## Built views and consistency checks

`data build` produces, in SQLite:

- `resolution` — identity results described above.
- `chronology_candidates` — every date event reachable from an observation
  (observation → configuration → SKU/family/system) with its kind.
- `chronology_selected` — the CPU → hardware → submission-era selection owned by
  the [timeline contract](timeline.md#cpu-first-date-selection), as a query.
- `consistency_findings` — reported, not auto-corrected: a SKU release later than
  a configuration's hardware availability; one SKU with release years more than
  one year apart; alias collisions; events outside the subject's plausible era.

The timeline and fitters then read these views instead of private lookups.

## Mapping from current files

| Current | Target |
| --- | --- |
| `classic/acquisition.csv`, `pdf-acquisition.jsonl`, `literature-sources.jsonl`, `early-benchmark-sources.csv`, `year-*-sources.json`, `cpu-sku-sources.json`, document inventory | `source` |
| `cpu-release-proxies.csv` | `processor_sku` + `alias` (exact text) + `date_event` (`release`) |
| `cpu-sku-chronology.csv` | `processor_sku` + `alias` (`sku-key-v1`) + `date_event` (`release`, `parsed_unreviewed`) |
| `hardware-date-evidence.csv` | `system_model` + `alias` + `date_event` |
| `timeline-year-overrides.csv` | `alias` (regex rule) + `date_event` (`inferred_proxy`) + `review` (rejected table years) |
| `submission-date-reviews.csv` | `review` |
| `mix-candidate-aliases.csv`, SPEC89 `aliases.csv` | `alias` (`candidate` / `accepted`) |
| Input catalog `observations.jsonl` / `sources.jsonl` | Extracted `observation` v2 + `configuration` + SPEC date events |
| `historical/observations.jsonl` | Curated `observation` v2 |
| `year-*-changes.csv`, `*-targets.csv`, `*-open-leads.csv`, pass audits | Move to `research/data/archive/<pass>/` as historical pass logs |
| Fit outputs, timeline Parquet | Unchanged products, gaining input-table hashes |

The SPEC89 v2.0.0 snapshot remains a versioned external package; it is adapted
into `observation`/`alias` rows rather than restructured.

## Migration plan

Each step ships separately and must pass a parity check before the old format
is removed. Parity means: identical fitted coefficients and intervals, identical
timeline record IDs, VAXen values and selected years, unless a documented change
is intended and listed in that step's report.

1. **Sources and provenance.** Create `source`, convert all registries, add
   `source_id` to existing curated rows. Parity: every old URL/hash maps to one
   source; no product changes.
2. **Identity.** Create entity tables, `alias`, rule `sku-key-v1` and the
   `resolution` view. Port `cpu_key`, `_processor_key`/`_system_key`, regex
   overrides and mix aliases. Parity: current matches reproduced exactly; new
   matches reported separately.
3. **Dates.** Create `date_event`; convert proxies, hardware evidence, overrides
   and SPEC date fields; implement `chronology_selected`. Parity: current timeline
   years reproduced. Enabling the SKU catalog is a separate, reported change.
4. **Reviews.** Convert submission/date/pair decisions into `review`.
5. **Observations.** Emit `benchmark-observation-v2` with entity references; switch
   fitters and timeline to the built database; regenerate the input catalog from it.

`data validate` and `data build` are implemented in step 1 and extended per step.

## Open decisions

- Curated location: `research/data/schema/` (proposed) versus a new top-level
  `data/curated/`.
- Database: SQLite (standard library, proposed) versus DuckDB (faster analytical
  queries, new dependency).
- Whether to keep per-table JSON Schema files or one combined `schema.json`.
- How strictly to normalize `configuration` for classical sources whose rows
  mix system, board and compiler identity.
