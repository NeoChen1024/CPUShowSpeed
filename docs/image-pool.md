# Image Pool and captioning (selected design)

The Image Pool stores crops from visual regions found during OCR. BLAKE3
identifies the bytes of each stored crop; it is not a way to match similar
pictures across PDFs. Different pixel crops of the same printed figure will
normally have different hashes. The original PDF remains the source of
record. OCR-stage crop storage and the image-only captioning command are
implemented, including repeatable DocIR caption backfill.

## Storing images

Crop valid visual blocks from the same page image submitted to Chandra.
Consider `Image`, `Figure`, `Diagram`, `Chart`, and other confirmed visual
labels. Chandra's built-in extraction currently crops only `Image` and
`Figure`; do not rely on it as the complete visual-region list. Keep one
DocIR block for each source chunk, with its bbox and `image_blake3` pointing
to the pool. If a crop fails, keep the block and mark that failure.

The current OCR writer uses lossless PNG for pool images so small technical
labels remain legible.
Hash the encoded bytes and store them under a sharded path such as
`images/ab/cd/<digest>.<extension>`. Publish each asset atomically and
verify an existing file with the same digest. Ingest only references from
the current completed OCR result; a CLI output directory may contain
unreferenced files from earlier runs.

The pool stores image files; a small SQLite catalog records digest, path,
media type, and dimensions. DocIR owns the source PDF/page/block reference.
Image bytes are not copied into DocIR. Successful captions are copied from
SQLite into DocIR by the repeatable backfill command.

## Conditional reporting

`documents report` reads the caption catalog only when
`--caption-database` is given. If the specified database has the current
`images` table but no `captions` table, report captioning as **not started**,
not as 0% complete. A missing or invalid specified database is an error.

The implemented report uses image-bearing blocks with a valid
`image_blake3` in **published DocIR documents** of the selected OCR run
as its denominator. It counts image occurrences in documents, not distinct
BLAKE3 hashes; the caption database still looks up each occurrence by hash.
With `--all`, include every published OCR document in that run. With
`--file-list`, include only published documents named in the list. Documents
still in OCR staging have no complete image count and do not enter either
denominator yet. As more documents finish OCR, the image denominator grows
and the captioning percentage may decrease.

Partition those image occurrences into successfully captioned, intentionally
skipped because Chandra supplied usable structured diagram/chart content,
failed caption attempts, and pending. Show both **caption coverage**
(successfully captioned / total images) and **processing progress**
((successfully captioned + intentionally skipped) / total images). Failed
and pending images remain unfinished. A skipped diagram is never described
as having a generated caption. The Image Pool's global `images` row
count is not the denominator: it may contain crops from other documents
or unpublished staging work. If the
selected published documents contain no images, show a count of zero and
an unavailable percentage rather than 100%.

`documents report` measures captions saved in SQLite. The backfill command
separately reports scanned pages, updated documents, and copied caption
occurrences; it does not add persistent progress state.

## Choosing what to caption

Caption every valid `Image` or `Figure` crop, including those with a
Chandra-generated `alt` description. Skip the second caption for a
`Diagram` or `Chart` only when Chandra supplied useful structured content,
such as Mermaid graph code or parsed table cells; caption unparsed crops.
Structured OCR and captions remain unverified. Important relationship
diagrams and numeric charts still need visual checks; a valid-looking
graph can have wrong edges. A source figure can also be omitted from OCR
entirely, which captioning emitted images cannot repair. The
[time-sharing sample review](../research/historical-sources.md#ocr-reliability)
shows both cases.

## Image-only caption batch

`cpushowspeed documents caption` requires `--output-root` and either
`--file-list` or explicit `--all`. Optional `--api-base`, `--model`,
and `--inflight-images` set the backend and global request limit. It selects image references only from
**published DocIR documents** in that scope. `Image` and `Figure` always
qualify, even when Chandra supplied an `alt` string. `Diagram` and `Chart`
qualify when no useful structured representation is present. The command
sends one crop and a fixed prompt per request, deduplicating exact BLAKE3
hashes for transport and storage; `documents report` still counts image
occurrences in documents. No filename, document title, page text, neighboring
blocks, Chandra `alt`, or original PDF page is sent to the caption model.

The prompt should request a plain-text visual description useful for search:
legible labels, units, components, boxes, arrows, connections, axes, and
uncertainty about unreadable details. It must avoid guessing a machine's
identity or a diagram's purpose from prior knowledge. Small crop fragments
may yield deliberately modest descriptions. This stage describes visible
content; any later retrieval view can combine the caption with DocIR page
text without contaminating the caption generation with uncertain OCR text.
Do not add document context to the first batch. If a reviewed pilot shows
that specific crops need context, treat those as a separate targeted pass.

In the completed 2026-09-26 watchlist OCR batch, published DocIR contains
1,158 image occurrences. Seventy-nine structured diagrams are skipped by
the current rule, leaving 1,079 eligible occurrences and 1,074 distinct
image hashes. Among the eligible occurrences, 396 crops have an axis shorter
than 256 pixels. These are workload counts, not evidence that the crops or
model descriptions are accurate.

A four-image IBM logo pilot and a separate large schematic request succeeded on
`gemma-4-26B-A4B-it` at `http://sparksrv.lan:5000/v1` on 2026-09-26.
The pilot does not establish corpus-wide caption accuracy. Before processing
every eligible image, review a small sample spanning
`Image`/`Figure`, large schematics, tiny diagram fragments, and poor scans.
Check legible label transcription and unsupported claims against the crop.
Then run bounded concurrent requests through one persistent
OpenAI-compatible client. Validate the asset's BLAKE3 before submission;
write each success or error to SQLite through one writer, and advance Rich
progress only after commit. The caption command's work unit is a unique
image hash; the report's coverage unit is an image occurrence in DocIR.
The progress display counts unique image attempts; the report counts
occurrences. A restart selects rows without a successful caption. Ctrl+C
stops new requests, saves completed rows, and permits the same command
to resume. The caption model is chosen separately from the
Chandra OCR model. The SQLite `caption_documents.started_at` value persists
when a document first dispatches an image. Each free request slot takes the
next pending image from the earliest-started document; a document may fill
multiple slots. Newly selected documents follow file-list order.

For example, process the watchlist with:

```sh
.venv/bin/cpushowspeed documents caption \
  --output-root data/derived/documents/chandra-ocr \
  --file-list inventories/watchlist-ocr.txt \
  --inflight-images 8
```

The prompt is one plain user message with a single image. The serving backend
handles Gemma 4 chat-template tokens. It asks for visible detail and explicit
uncertainty, following Google's [vision prompting guidance](https://ai.google.dev/gemma/docs/capabilities/vision)
and [Gemma 4 prompt format](https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4).

## Backfilling DocIR captions

The implemented `documents backfill-captions` command reads
successful captions by `image_blake3`, rewrites affected DocIR files through
atomic replacement, and leaves raw OCR JSONL unchanged. The backfill is
idempotent and does not run concurrently with OCR publication of the same
document. Structured diagrams remain uncaptioned by default; important
ones can be reviewed visually or included in a later explicit pass.

```sh
.venv/bin/cpushowspeed documents backfill-captions \
  --output-root data/derived/documents/chandra-ocr \
  --file-list inventories/watchlist-ocr.txt
```

Use `--all` instead of `--file-list` to select all published documents.
`--caption-database` optionally selects a catalog; the default is
`<output-root>/ImagePool/catalog.sqlite`. `--dry-run` validates documents
and reports planned changes without replacing files.

Each invocation reads a consistent SQLite snapshot. A nonempty saved caption
replaces an absent or older DocIR caption for the same image hash, including
any deliberately captioned structured diagram. Missing or empty captions
leave the block unchanged. Each document is streamed into a temporary file
beside the original, validated for page order/status/count, flushed, and
atomically replaced only if captions changed. All other fields and block
positions are preserved. The command holds the OCR output lock to exclude
OCR publication and other backfills. Ctrl+C leaves completed documents in
place and removes the current temporary file; repeating the command resumes
by comparing actual caption values.

The watchlist backfill updated 1,079 image occurrences in 15 of 16 documents
across 2,213 scanned pages. A second invocation updated zero documents;
raw JSONL hashes, non-caption DocIR fields, and second-run file modification
times were checked. This verifies materialization, not caption accuracy.

## SQLite state

The live catalog is `<output-root>/ImagePool/catalog.sqlite` on local storage,
not on the NFS bitsavers mount. OCR already creates `images` with BLAKE3,
filename, media type, and dimensions. Captioning adds one `captions` row per
`image_blake3`, with plain-text `caption`, model name, completion time, and
`last_error`. The existing report accepts `image_blake3`, `caption`, and
`last_error`; it reports captioning as not started while the table is absent.
A successful caption replaces any previous error. Failed or interrupted
requests leave no successful caption and are retryable. If the model or prompt
is deliberately changed, an explicit `--force` run may replace successful
captions; no version-history or contract machinery is planned.

An `<img>` inside a table cell currently causes an explicit table-conversion
failure rather than a guessed crop. The raw OCR and original PDF page remain
available until that case is tested on real output.
