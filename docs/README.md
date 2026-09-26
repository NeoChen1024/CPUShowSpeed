# Documentation

These documents distinguish implemented source collection from planned
analysis and define how future data should be read.

| Document | Primary responsibility |
| --- | --- |
| [Scope and metrics](scope-and-metrics.md) | Rate target, historical extension, and evidence classes |
| [Data contract](data-contract.md) | Result identity, units, dates, validity, and provenance |
| [Methods](methods.md) | Rate fitting, VAX throughput reference, and manual reconstruction |
| [Sources](sources.md) | Source inventory, acquisition order, and source-specific caveats |
| [SPEC collection](spec-collection.md) | Current integer-rate collectors and fits |
| [Document extraction](document-extraction.md) | Implemented PDF inventory, OCR, captioning, backfill, and evidence policy |
| [OCR dispatch](ocr-dispatch.md) | Implemented bounded PDF rendering, page inference, and resumable DocIR publication |
| [Historical DocIR](docir.md) | Implemented OCR page/block writer and HTML table projection |
| [Image Pool and captioning](image-pool.md) | Implemented visual asset pool, batch captions, and DocIR backfill |
| [Machine watchlist](machine-watchlist.md) | Priority historical systems and variant-specific evidence needs |
| [TODO](TODO.md) | Unimplemented or unverified research work |

The root [README](../README.md) is the public entry point. The
[research index](../research/README.md) owns source-checked findings. CLI `--help`
describes commands that have actually been implemented.
