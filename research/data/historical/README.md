# Curated historical observations

`observations.jsonl` is the initial version-1 schema for source-checked PDF
observations. Each line is one numeric value or methodological statement.
It is a curated transcription, not a benchmark normalization or simulation.

Required fields:

- `schema_version`, stable `id` and `review_date` (`YYYY-MM-DD`).
- `source`: mirror-relative PDF path, original URL and BLAKE3 of the reviewed
  PDF. Resolve paths against the inventory's source root, not this directory.
- `pdf_page`: one-based physical page; `printed_page`: printed label or null.
- `machine`: source-specific model or null for a document-wide statement.
- `metric`, `value`, `unit`: original numeric value and unit, or a boolean
  statement with null unit. Never reinterpret a boolean as a numeric score.
- `conditions`: explicit configuration/operation constraints; null means an
  identified unknown. Unlisted details are not assertions of equivalence.
- `evidence_kind`: `vendor_reported_rating`, `manual_timing`, or
  `source_method_statement`. A vendor rating does not establish execution.
- `verification`: currently `original_page_visual_check`; verifies the
  transcription on that page, not the manufacturer's experimental method.
- `notes` and `vaxen_eligible`: retain limitations; all current rows are false.

No source publication, hardware introduction or test date is inferred from a
filename. Unknown dates remain absent. Additional date fields may be added at
their actual precision when source-checked. Derived values must be separate
records with input IDs and method identity; do not overwrite these observations.

Discovery hits belong in ignored derived storage. The first search produced
`data/derived/documents/evidence/watchlist-hits.jsonl` and a search manifest
with regex, fields searched and DocIR hashes. These hits are unreviewed OCR
excerpts, not entries in this curated dataset.

The later combined search covers the watchlist and two newly processed PDFs;
`combined-search.json` and `combined-hits.jsonl` in the same derived directory
record the expanded pattern, document hashes and unresolved table conversions.

## Timeline year review

`timeline-year-overrides.csv` contains source-cited regex rules for conflicting
years and explicitly qualified family-year proxies. It is separate from the
manual timing observations above. `fallback=true` applies only without matching
model-year evidence. A blank year deliberately preserves an unresolved conflict.
See [the combined timeline](../../historical-vaxen-timeline.md) for precedence and
the generated full date-evidence table.

`hardware-date-evidence.csv` stores reviewed date events separately from regex
conflict overrides. Announcement and delivery are distinct; quarter precision
uses a year-valued `date` plus `quarter`, and prospective events cannot establish
actual shipment. See [hardware-year evidence](../../hardware-year-evidence.md).

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

## Expanded date-source catalog

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

## Configuration-specific CPU chronology

`cpu-release-proxies.csv` is a separate CPU-year fallback table: configuration ID,
original system/CPU/clock identity, interpreted CPU, release date, source URL and
locator, optional revision/snapshot hash, review date and qualifications. It only
applies to `date_status=unknown`; existing dates and unresolved conflict decisions
win. Identity mismatches raise an error rather than silently reusing a stale
mapping. Generic family/earliest-model assumptions are stated in notes. This table
does not assert complete-system release, nor amend raw benchmark identity.
`year-cpu-changes.csv` and `year-cpu-audit.json` record the resulting date-only
changes. The generated date-evidence export includes applied CPU mappings.
