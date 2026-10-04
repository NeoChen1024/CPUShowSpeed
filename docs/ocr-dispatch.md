# OCR dispatch

The `cpushowspeed documents ocr` command implements stage 1 and completed
the 16-document, 2,213-page watchlist batch against a real SGLang endpoint
on 2026-09-26. It has not been run over the full corpus or tuned for its
throughput. This document covers stage 1 of
[document extraction](document-extraction.md): PDF pages to raw model responses,
DocIR, and Image Pool assets. It does not run
image captioning or write Markdown/HTML files. The completed PDF inventory
currently contains 68,947 PDFs and 6,346,386 known pages, with a median of
32 pages per PDF and a maximum of 3,979. Because OCR of the entire
inventory is not expected to finish quickly, the normal entrypoint is a
selected file list; the dispatcher must not hold one whole document's
rendered pages in RAM.

## Library and command boundary

Use the repository-root uv-managed `.venv`. Both backends use local adapters
and an external OpenAI-compatible SGLang/vLLM server. No `chandra-ocr` or
`infinity-parser2` client is needed. PDFium is the only PDF renderer. Pillow,
BeautifulSoup and Markdownify provide image/HTML primitives. New raw document
headers record backend and local adapter versions, not an installed client version.

`documents/ocr.py` owns rendering, asynchronous HTTP dispatch, retries, page conversion,
ImagePool storage and publication. `documents/ocr_backends.py` selects each model's prompt,
settings, resize and parsing functions and shares the sampling schedule.
`documents/chandra.py` and `documents/infinity.py` normalize their model-specific output into blocks;
table conversion and crop storage then follow the same path. Layout parsing and
conversion run in worker threads, and invalid layouts re-enter the original
page's retry queue without occupying an inference slot.

Defaults still honor environment variables and `local.env` (environment wins):
`VLLM_API_BASE`, `VLLM_API_KEY`, `VLLM_MODEL_NAME`, `MAX_VLLM_RETRIES`, and the
Chandra-specific `IMAGE_DPI`, `MIN_PDF_IMAGE_DIM`, `MAX_OUTPUT_TOKENS`, `BBOX_SCALE`.
Infinity has separate fixed model-format settings described below.

The user-facing command is `cpushowspeed documents ocr` with:

- `--database` and optional `--input-root` for the existing PDF inventory
  and source tree; process only inventory records with readable PDFs;
- `--output-root` for mirrored DocIR and raw JSONL files;
- `--backend auto|chandra|infinity` for the model format (default: auto);
- `--api-base` and `--model` for the OpenAI-compatible SGLang/vLLM server;
- `-j/--jobs` for the **PDF rendering worker-process pool size**;
- `--inflight-pages` for the global limit on outstanding vLLM page requests;
- `--buffer-mib` for rendered-page admission control (default: 4096 MiB);
- `--file-list` for a UTF-8 file containing one PDF path per line;
- `--shutdown-grace` for the seconds to wait for in-flight OCR requests
  after Ctrl+C before cancelling them (default 10);
- `--prefix` or `--limit-documents` for a pilot, and explicit `--all` to
  process the full inventory.

Prepare a file such as `selected-pdfs.txt` with one source-relative PDF
path per line:

```text
simh/hpiop.pdf
ibm/IBM_Systems_Journal/353/preface.pdf
```

Absolute paths inside the inventory PDF root are also accepted. Empty
lines are ignored; repeated paths are processed once. Every entry must
match an inventory row with `ok` status, or the command fails before
sending OCR requests. The list order is the admission order for documents
that have not started; previously started documents retain their earlier
start-time priority. A different list can reuse the same output root:
already published pages are counted and skipped, while only newly listed
PDFs are added to the batch. `--file-list` cannot be combined with
`--prefix`, `--limit-documents`, or `--all`. Omitting every selection option
is an error, so full-corpus processing requires an explicit `--all`.

For the user-provided local SGLang endpoint:

```sh
.venv/bin/cpushowspeed documents ocr \
  --database data/derived/documents/inventory.sqlite \
  --output-root data/derived/documents/chandra-ocr \
  --api-base http://localhost:30000/v1 --model chandra \
  --file-list selected-pdfs.txt --jobs 2 --inflight-pages 2
```

The Rich progress bar uses completed physical pages as its unit. A page
advances it only after its successful or blank OCR record is stored in
staging; failed pages do not advance it. A resumed run starts with pages
already verified in staging or published output. At first dispatch of each
document, stderr reports its source path, inventory page count, and size
formatted by `humanize`. The bar also shows elapsed time and an ETA based
on the observed rate of completed pages. ETA is unavailable until pages
finish and may move substantially as page complexity changes.

On the first Ctrl+C, stop admitting documents and submitting pages. Let
in-flight OCR requests finish for at most `--shutdown-grace` seconds, then
cancel the rest. Finish page conversions and staging writes that already
started, commit document progress with `interrupted` status, and exit 130.
A second Ctrl+C ends the request grace period immediately. PDFium workers
ignore terminal SIGINT so the coordinator can collect their results and
shut them down. Repeating the same command resumes from the completed
staged pages without counting cancelled or merely rendered pages.

These are different resource limits. `--jobs` must never be passed through
as Chandra's `max_workers`: multiple callers would each create their own
request thread pool and defeat a global inference cap. Defaults for
`--inflight-pages` and the buffer should be chosen after a representative
pilot, not inferred from PDF byte size.

## Infinity-Parser2-Flash integration

With the default `--backend auto`, the command detects the format from `--model`
(or `VLLM_MODEL_NAME`). If no model is specified, it queries the endpoint's
`/models` and requires exactly one advertised model; otherwise specify `--model`.
The exact served ID is used unchanged for inference and run identity.

Detection recognizes Chandra and Infinity-Parser2-Flash family tokens without
case sensitivity, accepting repository/path prefixes, separator variations,
and arbitrary quantization suffixes. It does not maintain a quantization-name
list. Unknown or ambiguous names fail before OCR starts. Use an explicit
`--backend chandra|infinity` for a custom alias; this overrides format detection.
An explicit `--model` also allows endpoints without `/models` support. All existing file selection, oldest-document-first dispatch,
page progress/ETA, interruption, staging and publication behavior is shared.

```sh
.venv/bin/cpushowspeed documents ocr \
  --backend infinity --api-base http://localhost:30000/v1 \
  --database data/derived/documents/inventory.sqlite \
  --file-list inventories/watchlist-ocr.txt \
  --output-root data/derived/documents/infinity-ocr \
  --jobs 16 --inflight-pages 64
```

The local adapter reproduces the upstream 0.4.0 `doc2json` prompt (Apache-2.0;
[license](../third-party/Infinity-Parser2-LICENSE.txt)). Its validation and
conversion are independently implemented. No official Infinity client is needed.
PDFium renders one page at 300 DPI. Request images use a 32-pixel grid with
2,048–16,777,216 pixels and bicubic resizing; crops use the full render.
Requests use up to 32,768 output tokens, initial temperature 0 and top-p 1.
Retries increase temperature using the existing schedule, retaining top-p 1.
Configure `enable_thinking: false` on the server; the client does not override it.

Complete JSON arrays, optionally enclosed in a JSON code fence, are accepted.
Each block requires a known category, string text, and finite nondegenerate
coordinates in 0–1000. Empty arrays represent blank pages. Empty responses,
truncation, long repeating suffixes and invalid layouts are retried. No partial
JSON repair or character-count truncation is performed. The raw response is
retained verbatim and `chunks` retains the normalized-coordinate layout array;
DocIR has one block per chunk in the same order. Bounding boxes are floored into
full-render pixels. HTML tables use the shared converter, formula/text content
is retained, and figures become ImagePool crops eligible for captioning.

Backend identity, adapter version, prompt hash and render settings belong to the
run configuration. Use a separate output root when switching backends. Existing
Chandra run configurations remain compatible with resume.

## Chandra integration

The local adapter follows the Chandra 0.2.0 prompt and output behavior
([upstream](https://github.com/datalab-to/chandra),
[Apache-2.0 license](../third-party/Chandra-LICENSE.txt)). PDFium renders one page
at a time at 192 DPI with a minimum short dimension of 1,024 pixels and flattened
forms. Request images use a 28-pixel grid, Lanczos resampling, and the original
50,176–6,291,456 pixel target. PDFium remains isolated in worker processes.

HTML blocks retain source order and raw chunk content. Nested `data-bbox`
attributes are removed from chunks as in the baseline; the untouched response
is also retained. Invalid DocIR bounding boxes remain null. Math, Markdown
escaping, lists, headers/footers and structured Mermaid diagrams retain baseline
behavior. Table conversion and image crops use the shared page converter.

The local repetition detector retains the original suffix thresholds and the
second check that ignores the last 50 characters, including this project's
exception for short binary table cells. First attempts use temperature 0 and
top-p 0.1; retry `n` uses `min(0.2 * n, 0.8)` and top-p 0.95. Both backends default to five
retries after the initial attempt (at most six requests per page), including invalid
layout responses. Override this with `--max-retries` or `MAX_VLLM_RETRIES`.
Transport retries wait `2 * n` seconds while
releasing the inference slot. Empty responses, token-limit truncation, repeated
output and invalid layouts cannot be published as successful pages.

On 2026-09-28, all 2,213 watchlist raw pages produced identical conversion hashes
and repetition decisions before/after replacement, using a fixed blank raster
and mocked crop storage to compare block structure, tables and crop geometry.
Five image sizes also matched the original resize pixels, and 400 generated
cases matched the original suffix detector. A real two-page `2SC3147.PDF` run
completed against local SGLang after uninstalling the official client; rerunning
reused the completed pages. These are adapter checks, not corpus OCR accuracy
measurements or throughput benchmarks.

Legacy runs tagged `chandra_version: 0.2.0` can resume only when all remaining
settings match the local adapter's version-1 configuration. Their existing run
metadata stays unchanged; new runs identify the local backend explicitly.
Changing prompt, rendering settings, model or backend still requires a new
output root. Old published raw files are never rewritten during this transition.

## Oldest-document-first dispatcher

```text
inventory documents
  -> ready-document queue
  -> PDFium process pool (--jobs), short page ranges
  -> byte-bounded rendered-page queue
  -> global vLLM page slots (--inflight-pages)
  -> one result writer -> raw JSONL, DocIR, ImagePool
```

The PDFium processes form a shared pool; a process is not permanently
assigned to one document. Completed renders arrive through one bounded
process-to-coordinator channel tagged with document and page. The
coordinator places each result in that active document's **logical ready
deque**. Do not create one multiprocessing queue per PDF. Only the
coordinator chooses which ready page gets the next global vLLM slot; an
async event loop can do this without a separate scheduling process.
File writes may use a separate single writer so they do not block it.

Each document records a start time when first admitted. Whenever a
render worker or global vLLM request slot becomes free, choose the
**oldest active document with ready work** for that stage. Its pages
may occupy every available inference slot. Give its disjoint page
ranges to idle PDFium workers as well. This deliberately favors
completion of documents that began earlier; there is no per-document
round-robin quota in this batch workflow.

If the oldest document is temporarily waiting for rendering or all
its remaining pages are already in flight, take work from the
next-oldest ready document. Never leave a worker or request slot idle
solely to preserve document order. Results may finish out of order,
and one unusually slow page can delay final publication of its
document, but it does not stop other slots from accepting work.

Admit new documents as capacity permits. Bound the active set and
prefetch to protect RAM and file handles; that bound is a resource
limit, not a scheduling objective. Recover unfinished documents
with their original start times before admitting new ones after
a restart. Choose page-range length on representative files.

Do not wait for a fixed batch or for earlier pages in the same document.
The vLLM server can batch concurrent requests. A slow request holds only
its own slot; other completions continue to refill their slots. Give
requests a finite timeout and bounded retries so a permanently stuck
client request does not hold a slot forever; verify during the pilot that
a timed-out request is cancelled on the server before immediately refilling
that capacity. The page queue has a byte limit, not only an item
count, because page raster sizes vary. Count both rendered pixels
and prepared request bytes toward the budget. When it
is full, PDFium producers stop rendering until results release memory.
Release each image after its OCR result and visual crops are processed.

## Output and restart

For each source-relative path, replace its PDF suffix case-insensitively:

```text
dec/pdp8/foo.pdf -> <output-root>/dec/pdp8/foo.docir.jsonl
dec/pdp8/foo.pdf -> <output-root>/dec/pdp8/foo.raw.jsonl
```

Reject output-name collisions; the current inventory has none under this
rule. Reserve `<output-root>/ImagePool/` for content-addressed lossless
visual crops. The raw JSONL records the one-based PDF page, raw model
response string, parsed chunks, page pixel dimensions, token usage,
and attempt/error status. Its document header holds source/model/render
information. It is JSON even when the model response string contains HTML.
Do not write Chandra's merged Markdown or HTML files.

Results can finish out of order. The coordinator stores one atomic
staging record per page, with explicit page numbers, under the output root.
On restart, recover completed pages from staging and resubmit only missing
or failed pages. A failed page has an explicit staged error record and does
not count toward completed-page progress. A document with failed pages stays
in staging for a later retry and is not published.
For a finished document, validate that every physical page has exactly one
successful or blank record. The raw JSONL starts with one document header for source
identity, model, and rendering settings, then contains one ordered record
per PDF page. Write temporary files beside their final destinations;
publish the raw JSONL first and the DocIR last. The presence of the final
DocIR is the document-completion marker, avoiding a partially published
pair after a crash. Only publish an Image Pool reference after its asset
is safely stored.

A finalized raw JSONL file is immutable. Resume and page retries operate
on the staging copy before publication. If a document is intentionally
re-OCRed with different model or rendering settings, use a new output root
for that run rather than overwriting prior raw evidence. The DocIR in each
run can later receive captions by the separate backfill stage.

## OCR progress in the inventory database

The existing `files` table remains the source inventory. Separate `ocr_runs`
and `ocr_documents` tables live in the **same local SQLite database**; OCR
status does not change a PDF's inventory `status`. A run identifies its
output root and the model, prompt, rendering, and conversion settings. Starting a run with conflicting settings for the
same output root is an error, consistent with immutable finalized raw output.

The document-progress row is keyed by run and source-relative path. It
stores a snapshot of the source BLAKE3 and page count, the time the document
was first admitted, a coarse state, last update/error, and a cached count
of completed pages. The first-admitted time never changes during retries or
resume; it is the scheduler's oldest-document priority key. Rows with no
start time have not been admitted. An inventory rescan may update `files`,
but an OCR document whose source hash no longer matches its snapshot must
be reported as changed, not silently continued against new PDF bytes.

Keep per-page raw responses and success/failure details in bounded staging
records, not millions of SQLite rows or blobs. The cached page count and
coarse state are progress hints, not proof of completion. On restart,
reconcile each active document with its staging records and final output
files, then reconstruct missing work. A document is published only after
its output validation and atomic publication steps succeed; if a crash
occurs between file publication and the SQLite update, the files are
checked before marking it published. Keep database writes in one coordinator
with short transactions. The existing database uses WAL and lives on local
storage. The current buffer limit controls admission of rendered pages using
a provisional per-worker reservation; it is not an exact upper bound on
process memory for an
exceptionally large PDF page. Measure this on representative large pages
before a full-corpus run.

## Progress reporting

`documents report` keeps its full PDF inventory tables and adds OCR progress
for the selected run. It infers the run when the inventory has exactly one;
otherwise pass `--output-root`. `--file-list` applies the same inventoried
PDF selection rules as the OCR command, while `--all` (or omitting a report
scope) uses every currently eligible inventory PDF:

```sh
.venv/bin/cpushowspeed documents report \
  --database data/derived/documents/inventory.sqlite \
  --output-root data/derived/documents/chandra-ocr \
  --file-list inventories/watchlist-ocr.txt
```

The report shows published DocIR documents and pages, successful pages still
in staging, total OCR-completed pages, and active/interrupted/retry/pending
document counts. Denominators are the selected `files.status='ok'` inventory
rows. Source hashes that changed since an OCR run, and published state whose
raw or DocIR file is missing, are reported separately rather than counted
as completed. Staged-page counts are SQLite checkpoints, not a scan of all
staging files; a crash between page publication and the checkpoint may leave
a temporarily low count until OCR resume reconciles it. Tiny full-inventory
percentages retain enough decimal places to remain visible. Displayed
percentages are floored at their shown precision, so unfinished work never
rounds up to 100%.

Pass `--caption-database <output-root>/ImagePool/catalog.sqlite` to add the
separate caption section described in [Image Pool](image-pool.md). Without
that option, `documents report` does not read the caption catalog.

## Throughput validation

The scheduler is dynamic because idle workers and request slots take
work from the oldest active document that is ready, then fall through
to newer documents whenever the older one cannot supply work. This
keeps resources busy while giving earlier-started documents dispatch
priority. The active-set bound protects memory and file handles.
An automatic concurrency controller is unnecessary initially. On a
representative mix of short, long, dense-table, and poor-scan PDFs,
vary `--jobs` and `--inflight-pages` and
measure completed pages per second, render/encode time, request latency,
vLLM running/waiting requests, errors, RAM, and queue occupancy. Then set
defaults from the measured bottleneck. The current Rich progress reports
completed/total pages, elapsed time, and ETA, with dispatch and diagnostics
on stderr. Per-document and in-flight counts can be added if measurement
shows they help tune the full-corpus run.
