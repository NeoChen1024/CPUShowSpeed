# Historical document IR (selected design)

This is the selected CPUShowSpeed DocIR extension for OCR of historical PDFs.
The table converter, Chandra and Infinity page writers, and OCR scheduler are
implemented. The 16-document, 2,213-page watchlist batch was generated
on 2026-09-26; this is OCR output, not source-checked research evidence.
This format is independent of FrontendAgentLoop's existing DocIR and does not
change that repository.

## Source and derivation boundary

The original PDF is immutable and remains the source of record. The completed
PDF inventory supplies its relative path, BLAKE3 digest, and page count. OCR
responses and rendered images are derived evidence stored outside Git; they
must retain model, backend, prompt, rasterization settings, and run identity.
DocIR is a normalized reading and retrieval view, not a source-checked result
table. A cited performance number must still be checked on the original page.

One published DocIR JSONL file represents one fully processed PDF. Each line
is one physical PDF page, including blank pages. Failed pages remain explicit
in staging and are retried before the document is published. `page` is
one-based and must be read explicitly;
the line number is not a page identifier. The sibling raw JSONL begins with a
document header containing source PDF identity, schema version, model, and
rendering settings, followed by page records. Do not repeat these document-wide
values in every DocIR page line. No third manifest file is required.

## Page and block shape

A page record is ordered and keeps the rendered page size so pixel bounding
boxes are interpretable:

```json
{
  "page": 12,
  "page_size_px": [2040, 2640],
  "status": "ok",
  "blocks": [
    {
      "kind": "text",
      "source_label": "Text",
      "bbox_px": [120, 210, 1900, 320],
      "markdown": "Instruction timing depends on memory cycle time."
    },
    {
      "kind": "table",
      "source_label": "Table",
      "bbox_px": [110, 340, 1920, 900],
      "table_schema_version": 2,
      "content": ["… see Tables below …"]
    }
  ]
}
```

`blocks[i]` corresponds to `chunks[i]` in the separately retained,
immutable raw page response. Chandra retains each chunk's original HTML;
Infinity retains each layout object's `category`, `text`, and normalized `bbox`.
Its `figure` becomes a visual block, `table` uses the shared HTML converter,
and other categories retain their content in `markdown`.
Table cells are the stored normalized structure; table Markdown is a derived
view. The page writer must emit exactly one DocIR block for each source chunk, in the same order. It may not
filter, merge, or split chunks in DocIR; unsupported content and conversion
failures retain their block slot with an explicit status. Chandra's empty
`chunks` array corresponds to an empty `blocks` array. Retrieval-oriented
splitting or filtering belongs in a separate derived index. The original
model response may also be retained, but it is the parsed `chunks` array
that provides this positional mapping.

`source_label` retains the backend's label without treating the label as
verified document semantics. `bbox_px` is `[left, top, right, bottom]`
in `page_size_px` coordinates. An invalid or missing bounding box is
`null`, not an invented full-page box.

A blank page has `status: "blank"` and an empty `blocks` array. A staged
OCR failure has `status: "error"`, an empty `blocks` array, and an error
message; it is not counted as complete or included in a published document.
Blocks follow the OCR reading order.

## HTML table conversion

Build table blocks from Chandra's original block HTML, before using its
document-level Markdown. Its current Markdown converter leaves `<table>`
markup intact. The table converter parses one table into a structured cell
list. A separate pure renderer generates a Markdown pipe table on demand;
table blocks do not store Markdown.

- Keep each cell's row, column, rowspan, colspan, text, and `th`/header flag.
  Markdown alone cannot recover merged cells.
- Use the first row as the Markdown header only when all its occupied cells
  are `th`. Otherwise insert an empty synthetic header and keep every source
  row as data. This decision is derived from the stored cell `header` flags,
  so no synthetic-header field is stored.
- Expand spans into empty Markdown positions while retaining their original
  extents in `cells`. Preserve text such as decimal points, signs, units,
  pipes, line breaks, superscripts, and captions in the reading projection.
- Reject malformed or overlapping tables explicitly. A failed conversion keeps its original HTML in the raw OCR
  artifact and records a table conversion failure; it must not silently emit
  plausible Markdown or discard the table. Review the original PDF page before
  curating any numeric value.

For a failed table, the page writer should keep a block with `kind: "table"`,
`table: null`, `conversion_status: "failed"`, and an error message.
Its position in `blocks` still locates the raw HTML in `chunks`.
The page writer was exercised over the watchlist batch after a two-page
pilot that included one 20-row HTML table. One legitimate binary table row
triggered Chandra's trimmed-suffix repeat check; the OCR adapter now exempts
short, complete binary table cells while still retrying degenerate output.
This does not validate the extracted text against original PDF pages.

## Tables: compound tables and rich cells

Implemented and checked on 2026-09-26 as table schema version 2. Every stored
table uses it: the last version-1 blocks were migrated on 2026-10-04 and
version-1 support was removed. The renderer places merged-cell text only at its
top-left anchor,
leaving the other covered grid positions empty. Do not remove spans from the
canonical representation to simplify Markdown.

The Honeywell batch exposes three additional structural cases:

- Physical page 51, block 5: a genuine table inside a parameter-description
  cell, following prose; the inner rows must remain attached to that cell.
- Pages 52, 55, 57, 72 and 83: surrounding text belongs to the same OCR chunk
  as the table. Preserve its position instead of rejecting or dropping it.
- Pages 63, 64 and 89: cells contain `img` elements. Some provide only OCR
  alt text, without a source URI or a cell-specific bounding box. Preserve this
  unresolved visual occurrence rather than inventing a crop or numeric value.

### Canonical representation

Keep exactly one DocIR block per raw OCR chunk. A version-2 table block has
`table_schema_version: 2` and an ordered `content` array. Its children can be
`text`, `table` or `image` nodes. A cell has the existing `row`, `column`,
`rowspan`, `colspan` and `header`, but replaces `text` with its own ordered
`content` array. This supports prose around tables, multiple sibling tables,
and nested tables without flattening their ownership or reading order.

Illustrative structure, not a source transcription:

```json
{
  "kind": "table",
  "source_label": "Table",
  "table_schema_version": 2,
  "bbox_px": [100, 200, 900, 700],
  "content": [
    {"kind": "text", "text": "Parameters"},
    {
      "kind": "table",
      "row_count": 1,
      "column_count": 2,
      "caption": null,
      "row_groups": [],
      "cells": [
        {
          "row": 0, "column": 0, "rowspan": 1, "colspan": 2,
          "header": false,
          "content": [
            {"kind": "text", "text": "Control character"},
            {
              "kind": "image", "source_uri": null,
              "image_blake3": null, "bbox_px": null,
              "alt": "OCR description of a control-field diagram",
              "asset_status": "unresolved"
            }
          ]
        }
      ]
    },
    {"kind": "text", "text": "Footnote following the table."}
  ]
}
```

Text nodes preserve the existing supported superscript/subscript and math
notation; they are content, not a pre-rendered pipe table. A nested table uses
the same table-node shape recursively. `row_groups`, when present in the HTML,
record `thead`, `tbody` or `tfoot` with zero-based `start_row` and `row_count`.
Do not infer semantic headers or footnote targets from typography alone.
Do not duplicate cell content in a stored flattened `text` or `markdown` field.

An image's `source_uri` records the literal source reference, without fetching
it automatically. `image_blake3` is set only when an actual corresponding asset
exists in the Image Pool. An absent cell-image bbox remains null; the enclosing
block/page still locates the source for review. OCR alt text remains unverified.
A whole-table crop may aid review but must not be presented as a cell crop.

### Markdown reading projection

- Expand each table to a rectangular grid; write cell contents only at the
  top-left coordinate of its span. Covered positions stay empty. Retain
  separate header rows; do not merge their labels or repeat their values.
- Use a Markdown header only when supported by the source header cells;
  otherwise add an empty synthetic header as the current renderer does.
- Render text within a cell in order, using `<br>` for paragraph boundaries.
- Render a nested table as an explicit reference in its owning cell, followed
  by a separate pipe table with a deterministic label derived from the parent
  table/cell path. Recursively emit every nested table; never replace it with
  a summary that drops rows. Sibling tables remain in source order.
- Use an explicit image placeholder with its unverified alt text and available
  asset reference. Do not interpret a diagram into invented table values.
- Render surrounding text in order before/between/after tables. Keep footnotes
  verbatim in position unless their semantic association has been reviewed.

The reading projection is deliberately lossy in layout and must not be used to
reconstruct canonical table geometry. Scripts consume the structured records.

### Implementation and migration record

1. `documents/rich_table.py` implements the reader/writer and renderer. Validation
   bounds nesting (32), nodes (100,000), HTML input (8 million characters) and
   aggregate grid slots (1 million), in addition to row (4,096) and column (512)
   limits. Invalid overlapping spans remain explicit errors, rather than being
   silently repaired.
2. The nine real failure blocks are regression fixtures, alongside merged
   headers, nesting, surrounding text, sibling tables and unresolved images.
   Their original text/numeric token multiplicities survive conversion.
   Structural checks and reading projections do not certify OCR accuracy.
3. `walk_content` traverses rich cells and nested nodes for retrieval and image
   consumers. Caption selection/backfill and image reporting use it. The report
   lists unresolved inline images separately from resolved Image Pool assets;
   they are not counted as completed captions. No automatic image resolver is
   implemented, and image URIs are never fetched during conversion.

```sh
.venv/bin/cpushowspeed documents render-tables \
  data/derived/documents/chandra-ocr/honeywell/h300/Honeywell_300_Programmers_Reference_Manual_Aug64.docir.jsonl \
  --page 51
```

Version-1 blocks were reconverted from the immutable raw chunk HTML by a
one-time `documents migrate-tables` command, which checked source hash, page
order, status and block/chunk alignment and replaced each document atomically.
The two-document early-benchmark batch (58 blocks, including the nine former
failures) was migrated on 2026-09-26. The remaining 24 watchlist documents
(1,284 blocks) followed on 2026-10-04, after the command was changed to record a
conversion failure in place, as OCR does, instead of stopping. The corpus then
held 11,115 version-2 table blocks and 143 conversion failures. The command,
the version-1 converter and the version-1 reader were then removed; they remain
in Git history.

## Structured diagrams

When Chandra emits a diagram as machine-readable graph code, keep that code
as the primary normalized representation rather than storing a Markdown code
fence or automatically requesting a second caption. For example,
`graph TD` is Mermaid syntax, not Graphviz DOT:

```json
{"kind":"diagram","source_label":"Diagram","bbox_px":[230,410,1600,1390],"diagram":{"format":"mermaid","code":"graph TD\n  A --> B"}}
```

The diagram code is model-generated and may omit edges or labels. Keep the
original OCR HTML and PDF page for review. The source label need not be
`Diagram`; detection must inspect the code and preserve the actual label.
When a visual crop is available, retain it in the Image Pool for QA.
Structured code can lower captioning priority, but it is not evidence that
edges, labels, or numeric values are correct; important diagrams need a
second visual check against the original page.

## Visual blocks and the Image Pool

Visual blocks retain their source label and `bbox_px` and reference an
immutable crop in the corpus-wide [Image Pool](image-pool.md) by
`image_blake3`. For example:

```json
{"kind":"visual","source_label":"Image","bbox_px":[230,410,1600,1390],"image_blake3":"<64 lowercase hex digits>","caption":null}
```

The PDF page and block position already locate the source occurrence.
Image bytes and encoder metadata belong to the Image Pool. A successful
caption is stored first in its SQLite catalog, then copied into the visual
block's `caption` field by the separate backfill stage. SQLite is the
caption source of truth; `caption: null` means no caption has been copied
into this block yet. Run `documents backfill-captions` after captioning. OCR must not carry a stale caption across a changed
`image_blake3`. If a visual block cannot be cropped safely, keep the
block in place with an explicit error and omit `image_blake3`.
