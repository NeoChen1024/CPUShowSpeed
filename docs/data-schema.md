# Data schema design

Status: **steps 1 (sources), 2/2b (processor and system identity), 3 (dates), 4
(reviews), 5a (observations), 5b (SPEC rate fitters), 5c (classical, SPEC89
and mix fitters) and 5d (timeline) implemented 2026-10-02.**
This document owns the data model and its migration record. The
[data contract](data-contract.md), [input catalog](input-catalog.md),
[timeline contract](timeline.md#shared-record-contract) and
[historical observation contract](../research/data/historical/README.md) own
their remaining formats. Interpretation rules (evidence classes, date meanings, parallelism
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
| Curated | Hand-reviewed or small parsed tables: sources, entities, aliases, date events, reviews, curated observations | `data/curated/` | Yes |
| Extracted | Deterministic adapter output from raw (for example ~100k SPEC observations) | `data/derived/schema/` | No |
| Built | SQLite database joining curated + extracted, plus resolution and selection views | `data/derived/schema/cpushowspeed.sqlite` | No |
| Products | Fits, estimates, timeline projection | Existing derived paths | Small audits only |

Curated tables are CSV when flat and JSONL when a row needs nested conditions.
All tables are declared in one JSON Schema file, `data/curated/schema.json`
(columns, types, enums, required fields, foreign keys). Extracted tables use the same
schemas and record their adapter code hash and raw input hash.

`cpushowspeed data validate` checks every curated table against the schema, primary
keys, sort order and date precision; `--check-local` also compares stored hashes
with local stores and the document inventory. `cpushowspeed data build` validates
and writes `data/derived/schema/cpushowspeed.sqlite` with a `_meta` table of schema
and table hashes. Both are read-only with respect to curated data. Extracted
tables and materialized views join them in later steps.

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

Implemented 2026-10-02 as `data/curated/source.jsonl`. One row per identified
document, page revision or dataset snapshot; rows are sorted by `source_id`.

| Column | Meaning |
| --- | --- |
| `source_id` | Primary key, `src:<slug>` |
| `kind` | `pdf`, `postscript`, `web_page`, `wiki_revision`, `spec_result`, `text_file`, `program_source`, `archive_file`, `usenet_post`, `book`, `dataset` |
| `title`, `url`, `final_url`, `alternate_urls` | Identity and retrieval addresses; `alternate_urls` keeps other spellings found in legacy registries |
| `store`, `local_path` | Immutable local copy: `bitsavers_mirror` (relative to the document inventory root) or `repo` (relative to the repository) |
| `hash_algo`, `hash` | BLAKE3 for mirror PDFs and classic blobs, SHA-256 for web snapshots and SPEC exports |
| `revision`, `size_bytes`, `retrieved_on` | Wiki revision, byte size, retrieval date |
| `date`, `date_precision` | Publication date of the source itself |
| `provenance_class` | `primary_original`, `vendor`, `contemporary_secondary`, `modern_secondary`, `historical_museum`, `benchmark_org`, or `unclassified` when not established |
| `provider`, `work_id`, `families`, `role` | Publisher, compilation lineage (so copies are not counted as independent), benchmark families, research role |
| `acquisition_status` | `not_acquired`, `acquired`, `failed` |
| `reviews` | List of `{status, scope, reviewed_on, origin}`; legacy review vocabularies are kept, not collapsed, because their scopes differ |
| `note` | Next steps or limitations carried from legacy registries |
| `legacy_ids` | `<registry>:<key>` identities the row was migrated from; absent for sources added directly |

`cpushowspeed data migrate-sources` (removed in step 5d) performed the one-time migration from nine
registries (classic acquisition/PDF/literature lists, the pre-SPEC lead catalog,
the collect list, the CPU SKU sources, hardware date evidence, document reviews
and historical observations), using archived web manifests only to add revision
and cache paths. Claims merge on content hash or a shared legacy ID; a hashless
claim joins the single hash group with its URL. Different hashes for one URL
stay separate snapshots. Date evidence citing a SPEC bulk-export hash becomes one
`dataset` source; its per-row disclosure URLs become date-event locators in step 3.
The command refuses to overwrite an existing `source.jsonl` without `--force`.

### Entities

| Table | Key | Main columns |
| --- | --- | --- |
| `processor_family` | `fam:` | vendor, name: the most specific processor line a text can identify (Intel Xeon, IBM POWER7, Alpha 21164); optional `clock_variants_only` marks a line whose members differ only in clock or cores, so family plus clock identifies the part for pairing |
| `processor_sku` | `sku:` | family_id, vendor, model, rule match `keys`, every listed `base_clocks_mhz`, verbatim heading `sections` (generation/codename), source_ids |
| `vendor` | `org:` | name, `model_prefixes`; only spellings of one legal entity merge |
| `system_model` | `sys:` | name, vendor_ids; curated rows plus models derived by `spec-system-v1` and `name-system-v1` in one key space (key excludes the vendor, so lines that changed owner stay one model; RS/6000 530 and 530H stay separate). A curated row with a rule key's ID names that model |
| `hardware_config` | `hw:` | derived: equal tuples of system model, processor entity, nominal clock, chips, cores, threads/core, memory and hardware options (FPA, w/68882); unknown values never equal known ones |

A processor reference may stop at the family when the source names only a family
("Intel Itanium 2", "SPARC64 V"). Family-level date events are family launches
and are never presented as SKU releases.

#### Hardware identity versus run conditions

Selected 2026-10-02 (option B of three considered). Each observation links to
the most specific hardware it can be shown to describe; everything about how the
benchmark was run stays on the observation.

1. **Hardware identity** (`hardware_config`): system model, processor, clock,
   hardware options, chip/core/thread counts and memory. Observations from
   different sources share one `hw:` only through an accepted `alias`; name
   similarity alone never merges them.
2. **Run conditions** (observation `run` object): language, compiler and flags,
   OS, optimization level, scalar/vector mode, precision and copies/threads.
   Structured where parseable, always with the original text.
3. **Partial resolution**: when a source omits a hardware fact, the observation
   resolves only as far as is certain (a `system_model`, a `processor_sku` or a
   `processor_family`) and `resolution` records what is missing (for example
   `fpu: unknown`). Nothing is guessed to complete a configuration.

Source row numbers and source-internal codes (Netlib Dhrystone "reference 108",
Longbottom "P8") are locators or raw fields, never identity. Examples from the
current classical data:

| Source row | Hardware resolution | Run conditions |
| --- | --- | --- |
| Longbottom Whetstone "DEC VAX 11/780 FPA", For, No | `hw:dec-vax-11-780+fpa` | Fortran, unoptimized |
| Netlib LINPACK "VAX 11/780 FPA" | the same `hw:` after alias review | LINPACK n=100 |
| Netlib Dhrystone "VAX 11/780", UNIX 5.0.1 | `sys:dec-vax-11-780` only; FPA unknown | UNIX 5.0.1 |
| Longbottom "Cray Y-MP1" 90% Vector / P4 Scalar | one `hw:cray-y-mp1` | vector mode differs |
| Netlib Dhrystone "486DX2/66" (no vendor) | `sku:intel-486dx2-66`; system unknown | MS-DOS 6.2 |
| Netlib Dhrystone "Gateway 486DX2/66" | `sys:gateway-486dx2-66` with the same SKU | Linux 0.99 |

SPEC disclosures are complete enough to derive `hw:` deterministically from
system model, SKU, chip/core/thread counts and memory. Fitter grouping by
"system and processor configuration" then uses these IDs instead of private keys.
Software entities (OS releases, compiler versions) are not modelled: classical
sources rarely identify them beyond "For", "Opt" or a product name.

### `alias`

Maps source text to an entity.

| Column | Meaning |
| --- | --- |
| `alias_id` | Primary key |
| `entity_kind`, `entity_id` | Target |
| `match_kind` | `exact_text`, `pattern` (regex, case-insensitive unless switched off locally) or `rule` |
| `text` / `pattern` / `rule_id` | Exact text, regex, or a versioned rule (for example `sku-key-v1`); rules carry no `entity_id` |
| `scope` | `processor`, or `processor@<glob>` limiting it to mention scopes such as `spec:*` |
| `constraints` | Extra checks, for example `clock_within: 0.02` |
| `status` | `accepted`, `candidate`, `rejected` |
| provenance | `source_id` of the evidence and review fields |

Rules live in code with a version; `data build` materializes `processor_resolution`
(scope, text, clock → level, entity, alias, failure reason) from the extracted
`processor_mention` table (`data extract`, from the extracted observations).
Order: exact text, then rules with their constraints, then family patterns. A
failed SKU rule keeps its reason when a pattern resolves the family; overlapping
patterns are reported as ambiguous instead of being ordered. Every consumer reads
the resolution; none re-implements matching. The step-2 results and comparison
with the previous key are in [processor identity](../research/processor-identity.md).

### `observation`

Implemented 2026-10-02 (step 5a). `data extract` runs every source adapter into
`data/derived/schema/observations.jsonl`, `benchmark-observation-v2`: the v1
envelope (value, unit, track, mode, hardware, execution vector, evidence class,
source block, raw record, qualification) plus

| Field | Meaning |
| --- | --- |
| `result_id` | The reported result the score belongs to; one SPEC disclosure has base and peak scores. Chronology and reviews address results |
| `scope` | Origin and source or suite (`spec:cpu2006`, `classical:netlib-linpack-report`) |
| `metric_id` | Key of the curated `metric` table, which names the [registry](../research/model-registry.json) metric; adapters of one suite (`cpu92:integer:rate:peak`, `SPECrate_int92`) share it |
| `run` | How the benchmark was run, as source text: OS, compiler, language, optimization. Copies/threads stay in the execution vector |
| `verification` | As in the provenance block; every extracted row is `parsed_unreviewed` (adapter checks such as CPU92 ratio means are not reviews) |

`data build` loads them into the `observation` table with the resolved
`source_id` (by content hash, then a registry key the adapter cites such as a
SPEC89 package source ID, then an address claimed by one source, then a dataset's
`member_url_prefix`), the result's `hardware_id`, `system_id` and
`processor_entity`, and its selected chronology year. All 103,192 observations
(56,561 results, after the 2026-10-03 vendor-report rows) resolve to a source.

### `curated_observation`

Implemented 2026-10-03 as `data/curated/observation.jsonl`: values transcribed by
hand from a report table or post, one row per printed cell.

| Column | Meaning |
| --- | --- |
| `observation_id`, `result_id` | Row key (`cobs:…`); the values one source reports together for one system, configuration and run |
| `source_id`, `locator`, `system` | Source row, printed page and table or figure, and the system name as printed |
| `metric_id`, `value_printed`, `value`, `unit_printed` | Metric table key; the cell as printed and its number in the printed unit (never rescaled in the table) |
| `conditions` | Source-stated configuration and run conditions (clock, memory, OS, compiler, optimization, precision, BLAS form); absent keys are unknown |
| `measured_by`, `cited_reference` | `source_author`, `cited_third_party` (with the citation) or `unattributed` |
| `use`, `use_note` | `calibration_input` rows become observations; `context` rows stay here, with the reason |
| `duplicates` | Other sources printing the same value for the same system, probably one measurement |
| `verification`, `reviewed_on`, `note` | How the transcription was checked, and when |

`data extract` emits each `calibration_input` row as an observation in scope
`reviewed-vector:<source>`, converting the printed unit to the metric's unit by a
named rule (Dhrystones/s ÷ 1757 = DMIPS; KWIPS ÷ 1000 = MWIPS) recorded in the
observation. The first rows are the
[Digital RISC Family Performance Summary](../research/vendor-performance-reports.md)
(2026-10-03). The older `research/data/historical/observations.jsonl` rows
(Honeywell 300, DEC benchmark memo) are not yet migrated.

### `date_event`

Implemented 2026-10-02 as `data/curated/date_event.jsonl`.

| Column | Meaning |
| --- | --- |
| `event_id` | Primary key, `evt:<origin>/…` |
| `subject_kind`, `subject_id` | `processor_sku`, `processor_family` or `system_model` |
| `event_type` | `announcement`, `introduction`, `release`, `first_delivery`, `availability`, `configuration_availability`, `family_introduction`, `model_year` and the other source vocabularies |
| `date`, `date_precision`, `date_raw` | As above; quarters as `YYYY-Qn` |
| `claim_status` | `reported`, `planned`, `announced_future`, `prospective_or_not_confirmed_as_delivered`, `internally_inconsistent`, `inferred_proxy` |
| `chronology` | `primary`, `fallback` (fills gaps only) or `excluded` |
| provenance | `source_id`, `locator`, `verification`, `reviewed_on`, `note`, `legacy_ids` |

Dates a result reports itself (SPEC hardware availability, test and publication
months, Longbottom table years) and catalogue years stay extracted
(`result-records.jsonl`, `model-years.jsonl`) rather than curated. The selection
order is implemented in `data build`; see [chronology](../research/chronology.md).

### `review`

Implemented 2026-10-02 as `data/curated/review.jsonl`. Judgements that qualify
*extracted* evidence; aliases and date events carry their own `status` and
`chronology` and need no review row.

| Column | Meaning |
| --- | --- |
| `review_id` | Primary key, `rev:<origin>/…` |
| `target_kind` | `result_date` (one date a result reports), `result_pair` (two results treated as one configuration), `system_link` (two source system texts that may denote one machine) |
| `target` | A result selector — `{result_id}` or `{scope, system}` (every result with that exact system text in one scope) — or `{left, right}` selectors; system links use `{scope, system}` on both sides |
| `field` | `result_date` only: `hardware_availability`, `table_year`, `publication` or `test` |
| `decision` | `accept`, `reject`, `needs_review` |
| `reason`, provenance | Why; `source_id` and `locator` of the evidence when there is one; `reviewed_on`; `legacy_ids` for rows migrated from a legacy registry (absent for reviews made in the table) |

Selectors use source text and stable SPEC result IDs rather than derived
`sys:`/`hw:` IDs, so a rule change cannot silently retarget a decision. `data build`
resolves them into `review_result` (one row per matched result and side) and
`review_system_link` (both sides' current system models), and reports in
`review_finding` any selector that matches nothing and any unreviewed link the
identity rules already merge. A rejected result date leaves every chronology use
(own tier and model-level dates for other results) and is kept in the candidates
as `rejected_<field>`; the extracted record is unchanged. The CPU92 rate fit
reads CPU92–CPU95 `result_pair` decisions (step 5b); the classical
fitters read classical↔SPEC `result_pair` decisions (target left, classical result
right; a rejection drops a same-system pairing, an acceptance admits one unscaled
across a clock-reporting difference); `mix-bridge` reads open system links (step 5c).
The CPU92–CPU95 speed pairs have no consumer yet: the speed chain uses
automatic hardware-near pairs and does not read them.

## Built views and consistency checks

`data build` produces, in SQLite:

- `resolution` — identity results described above.
- `result_chronology` — per result, every candidate (CPU, hardware tiers,
  fallbacks, publication), the selected kind, year and range, and the result's
  own reported hardware-availability, test and publication dates after review
  rejections. The order is CPU
  release → hardware (own reported date, model events, own table year, model-level
  dates elsewhere) → reviewed fallbacks → publication.
- `consistency_finding` — reported, not auto-corrected: a CPU release later than
  the result's own hardware availability, and subjects whose primary event years
  are more than one year apart. Alias collisions and era checks remain planned.

The timeline and fitters then read these views instead of private lookups.

## Mapping from current files

| Current | Target |
| --- | --- |
| `classic/acquisition.csv`, `pdf-acquisition.jsonl`, `literature-sources.jsonl`, `early-benchmark-sources.csv`, `year-*-sources.json`, `cpu-sku-sources.json`, document inventory | `source` |
| `cpu-release-proxies.csv` | `processor_sku` + `alias` (exact text) + `date_event` (`release`) |
| `cpu-sku-chronology.csv` | `processor_sku` + `alias` (`sku-key-v1`) + `date_event` (`release`, `parsed_unreviewed`) |
| `hardware-date-evidence.csv` | `system_model` + `alias` + `date_event` |
| `timeline-year-overrides.csv` | `date_event` (`inferred_proxy`) on the matched models + `review` (rejected table years) |
| `submission-date-reviews.csv` | `review` (the file has no rows) |
| `hardware-date-exclusions.csv` | `review` (`result_date` reject) + the conflicting launch date as a `date_event` |
| `cpu92-cpu95-reviewed.csv` | `review` (`result_pair` accept) |
| SPEC89 `hardware-introductions.csv` | `date_event` |
| `year-document-reviews.csv` | `source` status |
| `mix-candidate-aliases.csv` | `review` (`system_link` needs_review, one row per matched text pair) |
| SPEC89 `aliases.csv` | `alias`, with the SPEC89 package adaptation in step 5 |
| Input catalog `observations.jsonl` / `sources.jsonl` (removed in step 5d) | Extracted `observation` v2 + `hardware_config` + SPEC date events |
| `historical/observations.jsonl` | Curated `observation` v2 |
| `year-*-changes.csv`, `*-targets.csv`, `*-open-leads.csv`, pass audits | Move to `research/data/archive/<pass>/` as historical pass logs |
| Fit outputs, timeline Parquet | Unchanged products, gaining input-table hashes |

The SPEC89 v2.0.0 snapshot remains a versioned external package; it is adapted
into `observation`/`alias` rows rather than restructured.

## Migration plan

Each step ships separately. Step 1 was held to parity (identical fitted
coefficients and intervals, timeline record IDs, VAXen values and selected
years). Steps 2–5 redesign identity and dates by user decision, so their outputs
are compared with the former ones instead, and each step's report lists what
changed.

1. **Sources and provenance** (done 2026-10-02). Create `source` and convert the
   registries. Legacy rows are linked through `legacy_ids` rather than edited,
   because later steps replace those tables. Parity checked: 925 legacy claims
   map to 276 sources, each legacy ID to exactly one source, every legacy hash and
   every cited URL is represented; 21 Wikipedia pages retrieved but never cited
   (archived pass log) are intentionally not sources. No product changed.
2. **Processor identity** (done 2026-10-02). Families, SKUs, aliases, `sku-key-v1`
   and the resolution table. By user decision the rules were designed afresh;
   the previous `_processor_key` served only as a comparison (no wrong SKU merges,
   nine prefix splits, an empty key grouping clock-only texts). 71.7% of input
   observations resolve to a SKU and 20.2% to a family.
   **2b. System identity** (done 2026-10-02): vendors, derived SPEC system models
   and hardware configurations; see [system identity](../research/system-identity.md).
   Equality-based configurations cannot link suites that omit counts (CPU92 has no
   core counts); cross-suite pairing is a fitter policy over equal-or-unknown facts.
3. **Dates** (done 2026-10-02). `date_event` from the SKU catalogue, CPU proxies,
   hardware evidence, year overrides and SPEC89 introductions; extracted result and
   catalogue dates; `result_chronology` and `consistency_finding`. Compared with
   the former timeline rather than held to parity: 50,298 of 58,813 SPEC records
   keep their year (most changes are CPU dating, one year earlier); 898 classical
   configurations are dated in both and 161 lose a year to unmatched spellings.
4. **Reviews** (done 2026-10-02). 31 migrated rows (44 rate-pair reviews followed in 5b): 6 rejected result dates (one SPEC
   hardware availability before its processor's launch; five Longbottom table
   years, two of them the CDC Cyber 73/74 rows dated with the 6400/6600), 13
   accepted CPU92–CPU95 speed pairs and 12 mix↔classical system links (11 awaiting
   review, one rejected). The EPYC 7313 launch date that justified the exclusion became a
   SKU release event, so all 26 EPYC 7313 results are CPU-dated (2021), including
   the two that reported 2019 availability. See [chronology](../research/chronology.md#reviews).
5. **Observations**, in four parts.
   - **5a** (done 2026-10-02): `benchmark-observation-v2`, the `metric` table, the
     `observation` table and dataset sources for the SPEC bulk exports, the SPEC89
     package sources and the Netlib CPU92 pages. Extraction counts are unchanged
     (103,456 observations, 58,356 results) and so is every chronology selection.
   - **5b** (done 2026-10-02): the SPEC rate fitters, chain bootstrap and annual
     rate view read the built database (`--database`) and pair over resolved
     `system_id` and processor identity instead of normalized names. The processor
     key is the SKU, the family plus an uncatalogued model number, or a family the
     curated `processor_family.clock_variants_only` flag marks as clock variants;
     other family-level matches pair only on identical system text. Factor tables
     record one `inputs_sha256` over the database's input hashes. The CPU92→CPU95
     same-OS base factor moved +2.10%, CPU2000→CPU2006 peak −4.80%, other edges
     within 1.4%; 71 of 72 annual leaders are unchanged. See the
     [rate audit](../research/spec95-spec2026-rate-fitting.md#changes-from-the-name-matched-fit).
     The CPU92 anchor then fits only reviewed-accepted pairs: 44 `result_pair`
     reviews of the automatic hardware-near CPU92/CPU95 rate pairs (42 accepted, 2
     rejected for differing cache), which left the same-OS anchor unchanged. The 13
     step-4 speed pairs have no consumer.
   - **5c** (done 2026-10-02): `rate-composite-fit`, `spec89-rate-fit`,
     `network-fit` and `mix-bridge` read the database and pair a classical result
     with a SPEC or mix result only when both resolve to the same `system_id`
     (`classical_store`); OS is a run condition, clocks must agree within 1% when
     both are known. Reviewed classical↔SPEC `result_pair` decisions (2026-10-02)
     reject or admit individual pairings. The
     duplicate `historical-spec:spec92-netlib` view of the Netlib CPU92 pages is
     dropped, and the SPEC89 integer bridge rows and DEC N3909 report columns
     become observations (`historical-spec:spec89-bridge`,
     `reviewed-vector:dec-n3909-1994`): 103,119 observations, 56,538 results, no
     chronology selection changed. `prepare-pairs`, `prepare-sources` and the
     name-based candidate pairs of `overlap-spec`/`mix-inventory` are removed; their
     tracked snapshots are archived. Same-column cohorts and both SPEC89 bridge
     edges are unchanged; cross-source composites, the network (−8% to +4%) and the
     SPEC89 joint cohorts change. See the
     [rate composites](../research/classic-composite-fitting.md#changes-from-the-name-matched-fit-2026-10-02),
     [SPEC89 bridge](../research/spec89-bridge.md#changes-from-the-name-matched-run-2026-10-02)
     and [network](../research/classic-network-fitting.md#changes-from-the-name-matched-run-2026-10-02).
   - **5d** (done 2026-10-02): `plot timeline` (`vaxen-timeline-v3`) reads the
     database and takes every year from `result_chronology`. Its population is
     SPEC92–2026 rate results through the saved rate chain, every one-processor
     classical result through the saved network and the saved SPEC89 estimates:
     60,633 records (58,813 / 1,641 / 179), of which 753 are undated. Mix rows,
     speed/joint estimates and matching policies are dropped from the timeline;
     the same day the [mix network](../research/instruction-mix-network.md) and
     speed/rate predictors (removed in 5e) are refitted
     on the database and their rows restored, without the matching policies. The
     legacy date files above and the per-pass date tables are archived in
     [`research/data/archive/legacy-dates/`](../research/data/archive/legacy-dates/README.md);
     their readers (`cpu-chronology`, `documents year-candidates`/`year-evidence`,
     `classic historical-timeline`), the one-time importers (`import-dates`,
     `import-reviews`, `import-processors`, `migrate-sources`) and the input catalog
     snapshot (`inputs build`, `--input-catalog`) are deleted. `data build` output
     is unchanged by the deletion.
   - **5e** (done 2026-10-03): speed and rate become two parallel quantities by
     user decision. `bridge fit-speed-chain` fits the
     [integer-speed chain](../research/spec-speed-chain.md) to SPECint92 speed
     (speed-VAXen); classical, SPEC89 and mix routes are re-anchored to it
     (`composite-fit`, `spec89-fit`, `predict-speed` replace the rate-named
     commands); the speed/rate predictors and their joint rows are removed; and
     `plot timeline` writes `vaxen-timeline-v4` with a `quantity` per row:
     101,427 records (58,813 rate, 42,614 speed). Adding the `curated_observation`
     rows of the [1990 DEC RISC summary](../research/vendor-performance-reports.md)
     and [MIPS Performance Brief 3.5](../research/vendor-performance-reports.md#mips-performance-brief-35-1988)
     the same day gave 103,192 observations, 56,561 results and 101,450 records.

   By user decision (2026-10-02) step 5 is compared with the former products, not
   held to parity: identity and dates were redesigned in steps 2–4, so coefficients
   change and each change is reported. The timeline page was reworked for the
   new rows on 2026-10-03.

`data validate` and `data build` were implemented in step 1 and are extended per step.

The [schema cleanup inventory](../research/schema-cleanup-inventory.md) lists what
each step retires and the order of independent cleanup.

## Decisions

Decided 2026-10-02: curated tables live in `data/curated/`; the built database
is standard-library SQLite; all table schemas are kept in one
`data/curated/schema.json`.

Also decided 2026-10-02 (step 4): review targets are selectors over source text and
result IDs, not `target_id` foreign keys, and cover only extracted evidence; the
mix candidates became `system_link` reviews rather than `candidate` aliases because
they pair two source texts, not a text and an entity.

Also decided 2026-10-02: hardware identity and run conditions are separated as
described under [hardware identity versus run conditions](#hardware-identity-versus-run-conditions).
