# Verified research findings

This directory is the repository home for findings checked against primary
source pages or other clearly identified evidence. It is an index and
contribution guide. Candidate leads
belong in the [machine watchlist](../docs/machine-watchlist.md), while the
[document extraction policy](../docs/document-extraction.md) governs OCR text.

Create a focused Markdown file here when evidence has been checked, for example
`research/pdp-8.md` or `research/ibm-1401.md`, and link it from this index. Keep
original names, model/revision distinctions, units, conditions, and uncertainty.
A useful finding records:

- The precise claim or transcribed value, including its unit and applicability.
- The original document title, issuing organization, form or revision number,
  and original page/table number; provide a source URL or archive path when
  available.
- How the page was checked, especially if OCR or a VLM first suggested the
  reading, and the review date in `YYYY-MM-DD`.
- Any unresolved ambiguity or conflicting source, without turning the finding
  into a silently chosen single value.

Once historical PDF and KIPS extraction starts, keep checked numerical findings
and their conditions in a script-readable dataset as well. Select its schema and
format then, and migrate checked examples already present in Markdown notes.
Research notes remain useful for the evidence trail and interpretation.

## Current findings

- [Early SPEC archive locations](spec-early-archives.md): verified CPU89/CPU92
  source paths and remaining first-issue gaps.
- [Curated SPEC89 recovery snapshot](spec89-curated-snapshot.md): source-linked
  machine-readable observations, package validation, and CPU89–CPU92 bridge limits.
- [First SPEC92 VAXen figure](spec92-vaxen.md): source-checked annual CINT92
  results and coverage limits.

A checked transcription is still distinct from an executed benchmark result,
manual reconstruction, or cross-benchmark estimate; follow the
[data contract](../docs/data-contract.md) for those records. Do not copy whole
PDFs, bulk OCR Markdown, or transient investigation logs into this directory.
