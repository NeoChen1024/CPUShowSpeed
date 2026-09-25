# Document extraction (proposed)

This workflow is under consideration; no PDF-to-Markdown pipeline has been
implemented or selected. MinerU or another VLM-based OCR tool may be used to
make historical scans searchable and quick to browse with an LLM agent.

## Evidence boundary

The original PDF remains the source of record. Generated Markdown is a derived
reading aid: OCR text, table structure, and page order may be wrong. Cite the
original document and page or table for research claims, especially numeric
values used in a reconstruction. Do not cite a Markdown line number as if it
were an original page reference.

## Proposed workflow

1. Retain the original PDF unchanged and identify its source, edition or
   revision, file hash, and retrieval date.
2. Convert pages to Markdown for search and initial reading. Preserve page
   boundaries and a mapping back to the original PDF pages. Keep the extracted
   text separate from both the PDF and curated result records.
3. Use the Markdown to locate likely instruction tables, timing notes,
   benchmark scores, and machine-configuration details.
4. Inspect the original page for every numeric value used in an analysis.
   Escalate ambiguous pages to a stronger VLM or manual review. Record the
   resolved reading and page-level evidence in a curated result or a
   [verified research finding](../research/README.md).

When curating checked performance values and related observations, also preserve
them in a script-readable form under the [data contract](data-contract.md).
Choose its schema and format when PDF and KIPS extraction starts; searchable OCR
Markdown alone is not the curated numerical dataset.

Table row/column alignment, decimal points, signs, exponents, units, footnotes,
model suffixes, and page omissions deserve particular scrutiny. A plausible OCR
value is not enough when it affects a published score or a bridge calibration.

## Minimal processing record

For each generated Markdown document, retain the source PDF identifier and hash,
OCR tool/model and version when known, processing date in `YYYY-MM-DD`, and page
mapping. Mark OCR output as unreviewed, partly reviewed, or reviewed for the
specific extracted claims; do not imply that validating one table certifies the
whole document. Full OCR transcripts and intermediate images are derived data,
not ordinary project documentation or Git content.
