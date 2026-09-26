# Candidate sources and acquisition policy

This is a source inventory and selection policy. The
[SPEC collection guide](spec-collection.md) records which official datasets
have been imported; the other listed sources remain candidates. Prefer
original technical documents and preserve
source-specific conditions before extracting comparable values.

| Source | Intended use | Acquisition caveat |
| --- | --- | --- |
| [SPEC CPU95](https://www.spec.org/cpu95/results/) | Published rate results | HTML/text disclosures; inspect compliance and configuration |
| [SPEC CPU2000](https://www.spec.org/cpu2000/results/) | Published rate results and CPU95/2000 overlap | Confirm matching configurations |
| [SPEC CPU2006](https://www.spec.org/cpu2006/results/) | Published results and generation overlaps | Per-result CSV is available |
| [SPEC CPU2017](https://www.spec.org/cpu2017/results/) | Recent published rate results | Preserve disclosed copy counts |
| [SPEC CPU2026](https://www.spec.org/cpu2026/results/) | New published rate results | Inspect copies and enabled hardware |
| [SPEC CPU89](https://www.spec.org/cpu89/) and [CPU92](https://www.spec.org/cpu92/) | Early source archive | CPU92 rate reports survive at Netlib; SPEC89 remains archival context |
| [EEMBC CoreMark](https://www.eembc.org/coremark/scores.php) and [run rules](https://github.com/eembc/coremark/blob/main/README.md) | Candidate embedded throughput series and possible same-system bridge to SPEC rate | Introduced in 2009; distinguish certified from other uploaded scores, one context from parallel runs, CoreMark from CoreMark/MHz, and record compiler, memory placement, clock, and validation status |
| [CCTA instruction mixes](https://www.researchgate.net/publication/318793156_Computer_Speeds_From_Instruction_Mixes_pre-1960_to_1971) | Early manual-derived estimates | Preserve mix weights, timing assumptions, and introduction dates separately |
| [Whetstone history](https://www.researchgate.net/publication/318755466_Whetstone_Benchmark_History_and_Results) | Early executed benchmark evidence | Distinguish machine age from result date, precision, and language |
| [Netlib LINPACK](https://www.netlib.org/utk/people/JackDongarra/faq-linpack.html) | Historical scientific-computing results | Keep problem size and processor count |

The [SPEC Fair Use Rules](https://www.spec.org/products/fairuse/) govern public
use of SPEC results and require historical normalization to be presented as
approximate. Source documents, PDFs, and downloaded result files are kept in
read-only raw storage outside Git; each imported record points back to its source.

## Curated SPEC89 recovery data

The [versioned SPEC89 snapshot](../research/data/spec89/v2.0.0/README.md)
contains source-linked historical observations, saved Usenet messages, compact
rebuild inputs, and a 25-table CSV export. Its package consistency checks pass,
but source-specific verification flags remain in every result. The larger
user-provided input bundle stays unchanged in the ignored local `inventories/`
area; the generated workbook, redundant JSON export, and broad search index
are not versioned. See the [checked package audit](../research/spec89-curated-snapshot.md)
for CPU89–CPU92 overlap counts and limitations.

The [Helman 1991 supplement](../research/data/spec89/helman-1991/README.md)
preserves a separate source-verified 40-row worksheet derivative. Its
[combined CSV](../research/data/spec89/aggregate89-plus-helman.csv) adds the
rows as source observations without changing the versioned snapshot.

## Pre-SPEC collection phase

Discovery review: 2026-09-26. Start with the existing local PDF mirror and
published DocIR, then acquire sources missing locally. Collect definitions, historical results, source
programs and machine configurations before selecting an assembly reconstruction
pilot or fitting another conversion. The active performance series remains
integer rate; the historical source collection also retains floating-point and
mixed workloads as context and possible validation evidence. Collection does not
make them eligible for the integer-rate fit.

The [script-readable source leads](data/early-benchmark-sources.csv) record
source IDs, URLs, inspection status, locators and the next acquisition step.
This is a discovery catalog, not a numerical performance dataset. `text_reviewed`
means the web-accessible text was inspected; it does not mean a PDF was acquired,
its tables were visually verified, or a score was imported. `index_reviewed`
means a repository listing was inspected. `citation_only` and `inventory_only`
are unverified document leads; `search_excerpt_only` requires full-document review.
`selected_pages_verified` means only the listed pages/claims were checked against
rendered originals; see the linked research record for individual observations.

Priority order:

1. Search the completed watchlist DocIR for benchmark names, performance
   comparisons, instruction timing, references and configuration conditions.
   Search text, table cells and backfilled captions; retain physical page and
   block identity for PDF verification. Query the local inventory for newly
   discovered titles before requesting another download or OCR run.
2. Recover Gibson's original report and TSU/CCTA mix definitions, together with
   Longbottom's Gibson/ADP result tables. His instruction-mix report describes
   a particular Gibson variation and an architecture adjustment in addition to
   weighted instruction timing. Preserve that distinction when reproducing it.
   Its DEC table includes PDP-7, PDP-8 and PDP-10 labels; configurations, column
   alignment and dates still need checking against scans and machine manuals.
3. Follow the Whetstone history's leads to the Process Control Mix and COPRXX
   COBOL suite. Seek original definitions, programs and reports, not just names.
   Preserve scientific, commercial and process-control workloads separately.
4. Collect Dhrystone versions/results and Whetstone, Livermore and LINPACK
   programs/results. Record language, precision, problem size, compiler,
   accelerator, concurrency and measurement date independently of machine age.
5. Search vendor manuals, performance briefs and comparative memos for the same
   machines. The Honeywell 300 manual and DEC programming-benchmark memo are
   already present in the local mirror. Their inventory entries are `ok`. The
   [next candidate OCR batch](../inventories/early-benchmark-ocr.txt) lists these
   two files (125 pages), now fully processed through OCR, captioning and DocIR
   backfill on 2026-09-26. See the [first evidence pass](../research/early-benchmark-evidence.md)
   for checked claims and structural-table exceptions. Trace citations backward
   to original definitions.
6. Build a machine/configuration-by-benchmark coverage table. Select calibration
   candidates and reconstruction targets from documented overlaps and gaps.

For each acquired file, retain retrieval date, original URL, immutable local
path and hash; distinguish archive copies of one report from independent
measurements. Capture publication date at its known precision. Archive.org,
library repositories and Usenet are recovery channels for missing documents,
with snapshot/message identity retained. Direct HTTP access to Longbottom's
site succeeded on 2026-09-26 after an earlier HTTPS failure. The
[classic collector](classic-collection.md) now preserves its Historic/Classic
pages and linked programs alongside other origins; see the
[acquisition audit](../research/classic-benchmark-collection.md).

Before importing numbers, define result records with the original metric and
unit, mix/version, source locator, machine/configuration, timing assumptions,
reported-versus-reconstructed status and verification status. Preserve raw
transcriptions separately from reviewed interpretations. No scores from this
discovery pass have been added to the VAXen chain.

## Local PDF mirror and discovery inventory

On 2026-09-26, the implemented `documents report` read
`data/derived/documents/inventory.sqlite`, whose resolved source root is
`/net/DF32_Pool/neo_chen/archive/bitsavers/pdf`. The database records 68,947
current PDFs, 570.87 GiB and 6,346,386 known pages: 68,946 `ok` records and one
`pdf_error`. These are the current local inventory's counts, not a fresh
remote-mirror completeness audit.

The watchlist report confirms 16/16 published DocIR documents and 2,213/2,213
pages under `data/derived/documents/chandra-ocr`. Image processing reports
1,079 captioned occurrences and 79 structured skips, with no failed or pending
occurrences. The [extraction guide](document-extraction.md),
[DocIR contract](docir.md) and [caption backfill](image-pool.md#backfilling-docir-captions)
own the implemented workflow. Reuse these artifacts for discovery; check claims
against original pages before creating curated results. Local availability,
preprocessing completion and source verification are separate states.

### Earlier rsync listing

<a id="local-bitsavers-discovery-inventory"></a>

`inventories/bitsavers-filelist.txt` is an rsync file listing from
`rsync://ftpmirror.your.org/everything/pub/misc/bitsavers`, generated on
2026-09-25 (Asia/Taipei). This 29 MB local discovery input is kept outside Git;
it is not a collection of the documents themselves.
It has 256,354 directory/file entries,
including 235,222 files and 99,346 PDFs. Its timestamps are mirror file times,
not document publication or hardware introduction dates. Paths are discovery
clues and must be verified against the document contents before use; bitsavers
warns that archive paths can change.

Initial filename candidates for instruction timing and early-machine coverage:

| Machine family | Candidate path within the listed mirror | Why inspect it |
| --- | --- | --- |
| IBM 650 | `pdf/ibm/650/24-5002-0_BasicOpcodes.pdf` | Operation definitions; timing still needs verification |
| IBM 704 | `pdf/ibm/704/24-6661-2_704_Manual_1955.pdf` | Early reference manual candidate |
| IBM 7090 | `pdf/ibm/7090/22-6528-4_7090Manual.pdf` | Instruction timing and configuration candidate |
| DEC PDP-1 | `pdf/dec/pdp1/F15_PDP1_Handbook_Apr60.pdf` | Early machine and instruction documentation |
| IBM System/360 | `pdf/ibm/360/A22-6825-0_360_Instr_Timing.pdf` | Explicit instruction-timing document candidate |

No timings or publication dates have been extracted from these files yet.

The [machine watchlist](machine-watchlist.md) records explicitly prioritized
systems and variant-specific leads from this inventory.
