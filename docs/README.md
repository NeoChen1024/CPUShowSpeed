# Documentation index

For the research story, begin with the [four-track overview](../research/overview.md).
For exact metric/model dependencies and document roles, use the
[registry catalog](../research/catalog.md). The root [README](../README.md)
introduces the unit, zero-intercept fitting assumption and local setup.

## Scientific contracts

| Document | Primary responsibility |
| --- | --- |
| [Scope and metrics](scope-and-metrics.md) | Speed/rate targets, historical routes and evidence classes |
| [Shared input catalog](input-catalog.md) | Source adapters, the observation envelope and execution-count admission |
| [Data contract](data-contract.md) | Identity, units, dates, validity and provenance |
| [Data schema](data-schema.md) | Target tables, identity resolution and migration plan (design) |
| [Methods](methods.md) | Estimation, normalization, uncertainty and research selection rules |
| [Sources](sources.md) | Source selection, acquisition priorities and caveats |
| [Machine watchlist](machine-watchlist.md) | Priority systems and variant-specific evidence needs |
| [Roadmap](TODO.md) | Unimplemented or unverified research work |

## Reproduction and data processing

| Document | Primary responsibility |
| --- | --- |
| [SPEC collection](spec-collection.md) | Integer-rate scraping, fitting and conversion commands |
| [Shared VAXen timeline](timeline.md) | Common record schema, CPU-first chronology, combined interactive view |
| [Classical prediction](classical-prediction.md) | Arbitrary score subsets to estimated SPECint92 speed-VAXen and calibration CI95 |
| [Classic collection](classic-collection.md) | Classical source extraction and experimental fitting commands |
| [Document extraction](document-extraction.md) | PDF inventory, processing workflow and evidence policy |
| [OCR dispatch](ocr-dispatch.md) | Bounded rendering/inference and resumable publication |
| [DocIR](docir.md) | Page/block schema, rich tables and Markdown projection |
| [Image Pool](image-pool.md) | Visual asset identity, captions and backfill |

CLI `--help` owns command options. The [research index](../research/README.md)
owns result navigation; topic reports own their numerical conclusions. Registry
maintenance is documented in the [overview](../research/overview.md#registry-maintenance).
