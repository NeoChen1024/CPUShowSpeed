# Documentation

These documents distinguish implemented source collection from planned
analysis and define how future data should be read.

| Document | Primary responsibility |
| --- | --- |
| [Scope and metrics](scope-and-metrics.md) | Timeline population, performance tracks, and evidence classes |
| [Data contract](data-contract.md) | Result identity, units, dates, validity, and provenance |
| [Methods](methods.md) | Instruction-mix reconstruction and benchmark bridging |
| [Sources](sources.md) | Source inventory, acquisition order, and source-specific caveats |
| [SPEC collection](spec-collection.md) | Current bulk, quarterly, and CPU92 archive collectors |
| [Document extraction](document-extraction.md) | Implemented PDF inventory and OCR extraction, planned captioning, and evidence checks |
| [OCR dispatch](ocr-dispatch.md) | Implemented bounded PDF rendering, page inference, and resumable DocIR publication |
| [Historical DocIR](docir.md) | Implemented OCR page/block writer and HTML table projection |
| [Image Pool and captioning](image-pool.md) | Implemented visual asset pool and planned batch captions |
| [Machine watchlist](machine-watchlist.md) | Priority historical systems and variant-specific evidence needs |
| [TODO](TODO.md) | Unimplemented or unverified research work |

The root [README](../README.md) is the public entry point. The
[research index](../research/README.md) owns source-checked findings. CLI `--help`
describes commands that have actually been implemented.
