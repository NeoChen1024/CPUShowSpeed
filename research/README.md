# Verified research findings

This directory holds source-checked findings and method audits. Preserve the
original metric, machine configuration, source URL or page, review date, and
uncertainty. Historical values extracted from PDFs should also enter a
script-readable [historical observation dataset](data/historical/README.md); Markdown alone is not
the canonical numeric store. The [data contract](../docs/data-contract.md)
defines provenance and date handling.

## Active rate research

- [SPEC CPU92–CPU2026 integer-rate fitting](spec95-spec2026-rate-fitting.md):
  five adjacent throughput fits, source-linked scatterplots, CPU92 VAX
  reference, and exploratory chain.
- [Annual integer-rate VAXen view](annual-rate-vaxen.md): yearly source-linked
  highest submissions and full submission distributions.
- [SPEC92 rate archive expansion](spec92-archive-expansion.md): 274 Netlib
  integer-rate reports and 1992 manufacturer-reported observations.
- [Early SPEC archive locations](spec-early-archives.md): provenance and
  remaining first-issue gaps.

## Preserved historical evidence

- [First local early-benchmark evidence pass](early-benchmark-evidence.md):
  source-checked Honeywell Gibson ratings, original PDP-8 timing inputs and
  the analytical evidence boundary of the DEC programming-benchmark memo.

The [curated SPEC89 source package](data/spec89/v2.0.0/README.md),
[Helman worksheet supplement](spec89-helman-worksheet.md), and
[source-checked hardware-date catalog](spec89-hardware-years.md) remain as
archival research. They are excluded from the active rate fitting pipeline.
The [machine watchlist](../docs/machine-watchlist.md) and
[document extraction policy](../docs/document-extraction.md) guide older
hardware work. The [Chandra OCR sample audit](chandra-timesharing-sample.md)
records checks of page figures and tables.

Keep bulk OCR and temporary debugging transcripts out of research notes. A
reported benchmark, manual reconstruction and normalized estimate must remain
separately identified.
