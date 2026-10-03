# DEC, SSCL and Tomari/Hiraki table extraction

Review date: 2026-09-26. This is a bounded table extraction, not new fitted
calibration or a claim that every original result has identical run conditions.

## Contents and reproducibility

- `recipes.json`: original physical/printed pages, one-based line ranges in
  Poppler layout text, source columns, expected row counts and contextual fields.
- `corrections.json`: 57 visually checked cell corrections, each with the text
  layer's original value, replacement and exact location. These correct OCR or
  merged cells, not apparent scientific inconsistencies in the printed source.
- `labels.json`: checked DEC row-label corrections (e.g. OCR `UNPACK` to
  `LINPACK`), applied in a separate field while retaining `label_raw`.
- `tables.jsonl`: compact reviewed table snapshot; raw lines, original text-layer
  cells, checked cells, corrections, source hash/URL and headers. This is the
  script-readable evidence retained in Git; generated long-form data stays out.
- `tomari-configurations.csv`: seventy exact-name joins between hardware Table 1
  and software/results Table 2, with both physical page/row locations.
- `summary.csv`, `audit.json`: counts, source/recipe/code/text/output hashes,
  Poppler version and published-correlation check.

Sources and immutable blob locations are in `../pdf-acquisition.jsonl`.
Acquisition URLs are listed in `docs/data/classic-pdf-sources.csv` at repo root.
Reproduce after acquiring the matching blobs:

```sh
uv run cpushowspeed classic extract-pdf-tables
```

Fermilab HTTPS and urllib HTTP attempts returned 403. A plain HTTP entry point
with `curl -fL` succeeded; its effective URL and transport are recorded in the
acquisition snapshot. Failed attempts remain in raw manifests. Reacquisition
must match the recorded BLAKE3 or receive a new source identity/review.

The command writes `data/derived/classic/pdf-tables/`: full layout text,
`tables.jsonl`, simplified `tables.md`, `observations.jsonl`, `observations.csv`,
joined Tomari configurations, summary and audit. Markdown is a reading aid;
continuation notes and raw corrections remain in JSON. `observations.context`
is an object in JSONL and a JSON string in CSV.

## Semantics

Table schema version 1 records `orientation`: DEC tables have benchmark rows
and machine/OS columns; other tables have record rows with named fields.
`cells` are reviewed transcriptions; `text_layer_cells` and `raw` preserve
extraction inputs. Empty cells, dashes and question marks are retained. Explicit
program fill-down is applied only to the observation context of SSCL Tables 4/5;
the table cells and Markdown keep the original blank cells. DEC AIM continuation
notes are attached to their original cell and copied into observation context.

Observation `value` parses only literal decimals, comma grouping and explicit
K/M suffixes (decimal 1,000/1,000,000). Missing cells have null values;
parenthesized/expression/estimated/qualified values remain unparsed strings.
The literal observation stream is **not normalization to DMIPS/MWIPS/VAXen**;
the separate interpretation output below supplies declared unit conversions. Metrics retain precision,
matrix size or an explicit unknown-size label; context retains the source's
compiler/OS fields. Metadata numbers (MHz, years, power, cache) are included in
counts and must not be mistaken for benchmark result counts.

All observations remain `fit_eligible=false`. Review status means page layout
and selected cells checked, not a second independent measurement or an exhaustive
cell-by-cell certification. Every table page was rendered and inspected.

## Specific caveats

- DEC cells here stay literal. Their reviewed readings live in the curated
  observations (`data/curated/observation.jsonl`, `cobs:dec-n3909-1994:…`):
  printed KWIPS read as MWIPS (user decision 2026-09-26); the bare-number
  Dhrystone cells on page 27 read as thousands of Dhrystones/s (a declared
  interpretation, not a recovered character); and the page 29 VAX 4000/200 and
  4000/300 Whetstone columns read at one tenth, matching Longbottom's 8.93/6.25
  MWIPS for the 4000/300 (2026-10-03).
- Page 31 prints 73.3 in a Whetstone cell where a related table has 33.3; this
  printed discrepancy is not silently fixed.
- DEC rate rows do not establish copies or active CPUs for every benchmark.
  AIM's `(4 cpus)` annotation applies to those AIM cells, not the whole column.
- SSCL Table 2 has Dhrystone-based MIPS with version unspecified and LINPACK DP
  ratings without an explicit matrix size in the table. Table 6 and Appendix B
  explicitly concern n=300; they must not be merged into n=100 fits. Estimated
  and externally sourced CERN values retain their annotations.
- Tomari Dhrystone is version 2.1, normalized by 1757 in Section 2.3. CINT/CFP
  are reported CPU2006 ratios, not rate scores or asserted official submissions.
  NPB is a geometric-mean ratio referenced to Sun Ultra60 360 MHz, per Section
  2.3. Hardware `core_count` is installed cores, not benchmark threads used.
  `year` is the paper's hardware year, with no invented month/day.
