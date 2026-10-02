# Legacy date tables

Moved unchanged on 2026-10-02 (schema step 5d). Steps 1–4 converted them into
curated tables; no code reads them. They remain the record of how those rows
were reviewed. Current dates live in `data/curated/date_event.jsonl` and
`review.jsonl` and are selected by the built `result_chronology` view (see the
[data schema](../../../../docs/data-schema.md)).

| File | Converted into |
| --- | --- |
| `historical/cpu-release-proxies.csv` | `processor_sku`/`alias` + `date_event` (`release`) |
| `historical/cpu-sku-chronology.csv`, `cpu-sku-sources.json`, `cpu-sku-audit.json` | `processor_sku`, `date_event`, `source` (former `research cpu-chronology` output) |
| `historical/hardware-date-evidence.csv` | `date_event` |
| `historical/timeline-year-overrides.csv` | `date_event` and `review` |
| `historical/submission-date-reviews.csv` | `review` (`result_date`); it was empty |
| `historical/year-document-reviews.csv` | `source` status (former `documents year-evidence` ledger) |
| `spec/hardware-date-exclusions.csv` | `review` (`result_date`, rejected) |
| `spec89/hardware-introductions.csv` | `date_event` |
| `research/cpu92-cpu95-reviewed.csv` | `review` (`result_pair`) |

The field descriptions below are the former contract of these files, kept for
reading them; paths in it refer to their former locations.

### Timeline year review

`timeline-year-overrides.csv` contains source-cited regex rules for conflicting
years and explicitly qualified family-year proxies. It is separate from the
manual timing observations above. `fallback=true` applies only without matching
model-year evidence. A blank year deliberately preserves an unresolved conflict.
See [the combined timeline](../../../historical-vaxen-timeline.md) for precedence and
the generated full date-evidence table.

`hardware-date-evidence.csv` stores reviewed date events separately from regex
conflict overrides. Announcement and delivery are distinct; quarter precision
uses a year-valued `date` plus `quarter`, and prospective events cannot establish
actual shipment. See [hardware-year evidence](../../../hardware-year-evidence.md).

The completed date-pass logs described below (`year-review-batch1*`,
`year-expansion-*`, `year-wikipedia-*`, `year-cpu-*`) moved to
[../archive/date-passes/](../date-passes/README.md) on 2026-10-02; no code reads them.
`year-document-reviews.csv` stays here because `documents year-evidence` reads it.

`year-review-batch1.csv` distinguishes completed OCR from source-checked date
events across all 80 PDFs. `year-review-batch1-changes.csv` records the resulting
point-year and evidence-span changes; benchmark scores and CIs are unchanged.

`year-document-reviews.csv` is the canonical document-level date-review ledger:
source path/BLAKE3, total and text-screened page counts, semicolon-separated
one-based original pages checked, prior pages reused, disposition, review date,
event IDs and notes. `date_scope_review_complete` means the chronology review is
complete, not every claim/page visually verified. Negative findings are scoped
to that review. Index regeneration accepts completed status only for a matching
source hash and page coverage. `year-review-batch1-changes.csv` compares the full
80-document pass against the immediately preceding partial-review timeline.

Date events additionally retain `date_raw` for qualifiers, `source_page_date`
for page-local issue dates and `review_batch` for curation provenance. These may
be blank in older entries. A blank printed-page label leaves the one-based
physical PDF locator authoritative. PDF dates are not inferred from filenames.

### Expanded date-source catalog

Date events may also cite external HTML or PDF sources:

- `source_locator`: human-readable table/section/page locator; used in generated
  date evidence in preference to the PDF-only fallback.
- `source_kind`: contemporary report, vendor history/fact sheet/disclosure,
  museum or secondary catalog. This describes provenance, not certainty.
- `snapshot_sha256`: hash of the cached external source or identified SPEC bulk
  file. For SPEC-derived entries, the locator identifies the row and the URL
  identifies its disclosure. Snapshot failures are explicit in the web manifest.
- `source_path`/`source_blake3` remain mirror-relative PDF identity fields; blank
  for external sources. External PDF page checks retain `pdf_page` and their URL.
- `verification=web_text_checked` is distinct from original-page visual checks.

`year-expansion-documents.csv` records the 545 additional files searched, source
hashes, OCR publication, hit counts and original pages checked. It does not
promote text searches to completed visual review. `year-expansion-targets.csv`
tracks all 754 initially unresolved source names; absence of an adopted event
is not an exhaustive negative search result. The web-source JSON retains URLs,
snapshot identities and failures. Changes and audit JSON record date-only output
parity against the preceding timeline; discovery transcripts remain ignored.

`year-wikipedia-*` records the following secondary-source pass separately from
`year-expansion-*`. Its source manifest retains Wikipedia revision IDs and HTML
hashes, accepted event IDs, failed requests and unadopted candidates. Revision
IDs can be resolved as `https://en.wikipedia.org/w/index.php?oldid=<id>`.
The changes CSV compares against the 1,087/624 timeline; the target CSV and open
leads distinguish unresolved records from verified dates. Prior pass audit files
are historical snapshots, not current counters. The canonical date CSV and the
latest generated `undated.csv` remain the current data and queue respectively.

### Configuration-specific CPU chronology

`cpu-release-proxies.csv` is a separate CPU-year fallback table: configuration ID,
original system/CPU/clock identity, interpreted CPU, release date, source URL and
locator, optional revision/snapshot hash, review date and qualifications. The initial `year-cpu-*` audit used it only for unknown dates. The current
[shared chronology](../../../../docs/timeline.md) gives reviewed CPU dates priority
over hardware dates and preserves both candidates. Identity mismatches raise an error rather than silently reusing a stale
mapping. Generic family/earliest-model assumptions are stated in notes. This table
does not assert complete-system release, nor amend raw benchmark identity.
`year-cpu-changes.csv` and `year-cpu-audit.json` record the resulting date-only
changes. The generated date-evidence export includes applied CPU mappings.

### CPU SKU chronology catalog

`cpu-sku-chronology.csv` is generated by `cpushowspeed research cpu-chronology`
from cached Wikipedia table revisions. Fields: normalized `sku_key`, source
`model_text`, `base_clock_mhz` (blank when the table gives none), `release_date`
at its stated precision with the original `release_date_raw`, page title/URL,
`source_locator` (wikitable and expanded row number), `source_section` (verbatim
heading path), `source_revision`,
`snapshot_sha256` of the cached HTML and `reviewed_on` (retrieval date). One SKU
may have several rows, for example revisions sold under one model number.
`cpu-sku-sources.json` lists every page revision, hash and row count;
`cpu-sku-audit.json` records catalog conflicts; SPEC coverage now comes from
`data build` ([processor identity](../../../processor-identity.md)). The cached HTML
stays under ignored `data/derived/documents/cpu-chronology/`. Rows are parsed
secondary evidence, not individually reviewed claims; see
[the catalog report](../../../cpu-sku-chronology.md) for its checks.

`submission-date-reviews.csv` contains evidence-backed acceptance/rejection of
submission dates as chronology proxies, not benchmark exclusions. It starts
empty. The [shared timeline contract](../../../../docs/timeline.md#submission-era-compatibility-reviews)
defines the fields and precedence; no fixed maximum age gap is assumed.
