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

- DEC Whetstone numeric values are interpreted as **MWIPS**, per the user's
  corrected decision on 2026-09-26. The printed KWIPS label remains in raw fields:
  a printed value of 189.4 is interpreted as 189.4 MWIPS. The earlier literal-KWIPS
  rule is superseded and retained only in the policy revision history.
- The eight bare-number Dhrystone cells on page 27 are interpreted as thousands
  of Dhrystones/s, per the user's visual review and same-scale judgment. This
  is a declared interpretation, not an OCR correction or independently recovered
  missing character. Explicit K/M suffixes are not multiplied twice; blank cells
  stay missing. Source strings and literal values remain unchanged.
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

## DEC interpretation output

`interpretation-policy.json` records the two source-hash-bound decisions, their
basis, authority and date. `dec-interpreted.csv` records interpreted Dhrystones/s
or MWIPS alongside original strings/literal values, applied multipliers, rule
IDs and a missing-suffix assumption flag. It additionally provides DMIPS using
1757 Dhrystones/s per DMIPS, or MWIPS with no numeric rescaling under the corrected Whetstone interpretation. Row references
join back to the source observations and table snapshot. No interpretation is
applied to other documents. Configuration review and fitting eligibility remain
separate; the affected source-pair fits were rerun after this correction.
