# Candidate sources and acquisition policy

This is a source inventory and selection policy. The
[SPEC collection guide](spec-collection.md) records which official datasets
have been imported; the other listed sources remain candidates. Prefer
original technical documents and preserve
source-specific conditions before extracting comparable values.

| Source | Intended use | Acquisition caveat |
| --- | --- | --- |
| [SPEC CPU95](https://www.spec.org/cpu95/results/) | Published integer and floating-point results | HTML/text disclosures; inspect compliance and configuration |
| [SPEC CPU2000](https://www.spec.org/cpu2000/results/) | Published results and CPU95/2000 overlap | Keep speed distinct from rate |
| [SPEC CPU2006](https://www.spec.org/cpu2006/results/) | Published results and generation overlaps | Per-result CSV is available |
| [SPEC CPU2017](https://www.spec.org/cpu2017/results/) | Recent published results | SPECspeed may use multiple threads |
| [SPEC CPU2026](https://www.spec.org/cpu2026/results/) | New published results | Inspect all supported threading mechanisms |
| [SPEC CPU89](https://www.spec.org/cpu89/) and [CPU92](https://www.spec.org/cpu92/) | Early SPEC lineage | Official archives lack these result sets; see [early archive research](../research/spec-early-archives.md) for Netlib and scanned-table sources |
| [EEMBC CoreMark](https://www.eembc.org/coremark/scores.php) and [run rules](https://github.com/eembc/coremark/blob/main/README.md) | Candidate embedded integer series and possible same-system bridge to SPEC | Introduced in 2009; distinguish certified from other uploaded scores, one context from parallel runs, CoreMark from CoreMark/MHz, and record compiler, memory placement, clock, and validation status |
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

## Local bitsavers discovery inventory

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
