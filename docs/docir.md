# Historical document IR (selected design)

This is the selected CPUShowSpeed DocIR extension for OCR of historical PDFs.
The table converter, Chandra-to-DocIR page writer, and OCR scheduler are
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
      "table": {
        "row_count": 2,
        "column_count": 2,
        "caption": null,
        "cells": [
          {"row": 0, "column": 0, "rowspan": 1, "colspan": 1, "text": "Operation", "header": true},
          {"row": 0, "column": 1, "rowspan": 1, "colspan": 1, "text": "Time (µs)", "header": true},
          {"row": 1, "column": 0, "rowspan": 1, "colspan": 1, "text": "ADD", "header": false},
          {"row": 1, "column": 1, "rowspan": 1, "colspan": 1, "text": "1.5", "header": false}
        ]
      }
    }
  ]
}
```

`blocks[i]` corresponds to `chunks[i]` in the separately retained,
immutable Chandra page response. Keep each chunk's original HTML there.
Table cells are the stored normalized structure; table Markdown is a derived
view. The page writer must emit exactly one DocIR block for each Chandra chunk, in the same order. It may not
filter, merge, or split chunks in DocIR; unsupported content and conversion
failures retain their block slot with an explicit status. Chandra's empty
`chunks` array corresponds to an empty `blocks` array. Retrieval-oriented
splitting or filtering belongs in a separate derived index. The original
model response may also be retained, but it is the parsed `chunks` array
that provides this positional mapping.

`source_label` retains Chandra's label without treating the label as
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
- Reject nested, malformed, overlapping, or unsupported image-bearing tables
  explicitly. A failed conversion keeps its original HTML in the raw OCR
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
caption source of truth; `caption: null` means no successful caption is
available. OCR must not carry a stale caption across a changed
`image_blake3`. If a visual block cannot be cropped safely, keep the
block in place with an explicit error and omit `image_blake3`.
