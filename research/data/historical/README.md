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

## Former date tables

The reviewed date tables that used to live here (`cpu-release-proxies.csv`,
`hardware-date-evidence.csv`, `timeline-year-overrides.csv`,
`submission-date-reviews.csv`, `year-document-reviews.csv` and the CPU SKU
catalogue `cpu-sku-*`) were converted into the curated `date_event`, `review`,
`processor_sku` and `source` tables in schema steps 1–4 and moved unchanged to
[`../archive/legacy-dates/`](../archive/legacy-dates/README.md) in step 5d
(2026-10-02). Dates are now edited in `data/curated/` and selected by the built
`result_chronology` view; see the [data schema](../../../docs/data-schema.md).
