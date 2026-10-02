# Document extraction

Stage 1 OCR extraction, the PDF inventory, and HTML table parser are
implemented, together with image-only captioning and DocIR caption backfill.
OCR output is derived reading material for historical scans. Stage 1 completed the
16-document, 2,213-page [watchlist batch](../inventories/watchlist-ocr.txt)
on 2026-09-26. The additional [early-benchmark batch](../inventories/early-benchmark-ocr.txt)
completed 2 documents / 125 pages, 118 image captions and DocIR backfill on the
same date. Its [evidence audit](../research/early-benchmark-evidence.md) records
structural-table exceptions and reviewed claims. The full corpus has not been
run or throughput-tuned.

## OCR backends

`documents ocr` automatically detects the wire format from the served model name.
Without `--model` (or `VLLM_MODEL_NAME`), it discovers the endpoint's single model.
Unknown or ambiguous names require an explicit `--backend chandra|infinity`. Both backends use local model-format adapters,
a shared PDFium renderer, and one OpenAI-compatible HTTP client. Neither official
OCR client is installed; PyMuPDF, pypdf, Transformers and Torch are unnecessary.
Prompts retain their upstream attribution and Apache-2.0 licenses. See [OCR dispatch](ocr-dispatch.md) for
backend settings and execution examples.

## Implemented PDF inventory

`cpushowspeed documents inventory` inventories an existing local PDF tree.
It reads each new or changed PDF in full to calculate BLAKE3, then uses
pypdfium2/PDFium to record its page count and PDF version. It does not OCR,
extract text, assess an existing text layer, or decide which pages may skip
Chandra. A PDF's embedded OCR text is not treated as verified evidence.

Run it from the repository's uv-managed `.venv`:

```sh
uv pip install --python .venv/bin/python -e .
.venv/bin/cpushowspeed documents inventory \
  --root /path/to/bitsavers/pdf \
  --database data/derived/documents/inventory.sqlite \
  --workers 4
.venv/bin/cpushowspeed documents report \
  --database data/derived/documents/inventory.sqlite
.venv/bin/cpushowspeed documents export \
  --database data/derived/documents/inventory.sqlite \
  --output data/derived/documents/inventory.jsonl
```

The SQLite database is tied to one resolved source root. It stores one row per
relative PDF path: size and file timestamps for resume checks, BLAKE3 digest,
page count, PDF version, PDFium version, scan time, and a status/error. Repeating
the command reuses unchanged successful rows and retries failed rows. Use
`--rescan` to re-read every file. A file that disappears is marked `missing`
only after a complete directory traversal and processing run. An empty traversal
against an existing inventory fails without marking everything missing, in case
the source mount is unavailable. Symlinked files are skipped. Rich progress
goes to stderr; reports go to stdout. The JSONL export has one record per source path and includes the resolved
source root in each record. The database and export are derived data, kept
outside Git.

A source file can change while it is read; the scanner compares its filesystem
identity, size, and timestamps before and after hashing and PDF parsing and
marks such a result `changed` for a later retry. A PDF parse failure retains
the completed file hash and an explicit `pdf_error` status rather than
pretending the file has zero pages. Page counts are unknown for failed files.

The selected [historical DocIR](docir.md) defines how OCR pages and tables
are represented. Its HTML table converter and Chandra-to-DocIR writer are
implemented. [Image Pool](image-pool.md) crop storage is implemented;
batch captioning and DocIR caption backfill are also implemented.
`documents report` shows scoped OCR progress and, when a caption catalog is explicitly supplied,
Image Pool caption progress; see the linked stage designs for counting rules.

## Evidence boundary

The original PDF remains the source of record. Generated Markdown is a derived
reading aid: OCR text, table structure, and page order may be wrong. Cite the
original document and page or table for research claims, especially numeric
values used in a reconstruction. Do not cite a Markdown line number as if it
were an original page reference.

## Processing workflow

The [OCR dispatch design](ocr-dispatch.md) owns stage 1 scheduling, resource
bounds, and restart behavior.

1. **OCR extraction.** Read the immutable PDF and its inventory BLAKE3.
   Use the selected local adapter to retain each page's original response,
   ordered chunks, bounding boxes, and generated visual assets. Convert
   every physical page into the [historical DocIR](docir.md), preserving
   blank and failed pages explicitly. Mirror the path below a configurable
   output root: `dec/pdp8/foo.pdf` becomes
   `dec/pdp8/foo.docir.jsonl`. Replace `.PDF` case-insensitively and reject
   any resulting path collision. Publish each document's raw JSONL first
   and DocIR last through temporary files. Keep both outside Git, with
   finalized raw OCR records immutable. A failed page remains explicit in
   staging and is retryable on the next run; documents with failed pages
   are not published.
2. **Image captioning.** Select every valid `Image` or `Figure` crop in
   the [Image Pool](image-pool.md), including ones with a Chandra `alt`
   description. For `Diagram` and `Chart`, skip the second caption
   when Chandra supplied a usable structured representation such as
   Mermaid graph code or table cells; caption unparsed visual crops.
   Store caption results in the local SQLite catalog. Structured OCR
   remains unverified, so important graphics still need visual QA.
3. **DocIR backfill.** Read successful captions from SQLite by the
   block's `image_blake3` and fill its `caption` field. Rewrite each
   affected DocIR file through a temporary file and atomic replace.
   OCR and backfill must not write the same document concurrently.
   SQLite is the source for generated captions; DocIR contains a
   convenient materialized copy for readers. Re-running this stage
   must be idempotent. If OCR changes a crop and its hash, an old
   caption must not be copied into the new block.

These are logical stages. Large runs may process completed documents in
batches, while preserving this order for each document. OCR, captioning,
and backfill should be separately resumable. Use the resulting DocIR to
locate likely instruction tables, timing notes, benchmark scores, and
machine-configuration details. Check every numeric claim on the original
PDF page; escalate ambiguous pages to another VLM or manual review and
record the resolved reading in curated data or a
[verified research finding](../research/README.md).

When curating checked performance values and related observations, also preserve
them in a script-readable form under the [data contract](data-contract.md).
The initial [historical JSONL observation contract](../research/data/historical/README.md)
now stores reviewed PDF values and methodological statements; searchable OCR
Markdown alone is not the curated numerical dataset.

Table row/column alignment, decimal points, signs, exponents, units, footnotes,
model suffixes, and page omissions deserve particular scrutiny. A plausible OCR
value is not enough when it affects a published score or a bridge calibration.

## Minimal processing record

For each generated DocIR document, retain the source PDF identifier and hash,
OCR tool/model and version when known, processing date in `YYYY-MM-DD`, and page
mapping. Mark OCR output as unreviewed, partly reviewed, or reviewed for the
specific extracted claims; do not imply that validating one table certifies the
whole document. Full OCR transcripts and intermediate images are derived data,
not ordinary project documentation or Git content.

## Hardware-year discovery batch

The [hardware-year evidence review](../research/hardware-year-evidence.md)
tracks an 80-document / 947-page batch completed on 2026-09-27 with 64 inflight
pages. All DocIR pages are published, and all 80 documents have completed the
hardware-year review (full text screening plus 145 relevant original-page checks).
This does not certify unrelated benchmark claims. Use `documents report` with
`inventories/hardware-year-ocr.txt` for current completion.
The `documents year-candidates` and `year-evidence` helpers that selected and
searched this batch read the former date tables and were removed on 2026-10-02;
accepted results are date events in the [data schema](data-schema.md).

The subsequent unknown-year expansion searches the other 545 candidate PDFs.
`inventories/hardware-year-expansion-ocr.txt` selects 32 text-poor PDFs / 310 pages;
all pages were published with 64 inflight pages. The separate expansion ledger
records 26 original local pages checked, without marking the entire search corpus
as reviewed. See the hardware-year evidence document for external source checks,
accepted date events and remaining uncertainty.
