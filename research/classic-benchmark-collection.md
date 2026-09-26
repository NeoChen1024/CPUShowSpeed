# Classic benchmark source acquisition

Review date: 2026-09-26. See the [implemented collector](../docs/classic-collection.md)
and [machine-readable acquisition inventory](data/classic/acquisition.csv).

## Acquired material

The first pass acquired 35 source objects totaling 8,246,512 bytes. These are
files/pages, not 35 independent measurement datasets. There are 17 HTML sources,
seven ZIP archives with 233 member entries (including directories), four PDFs,
six plain source-code files and one PostScript report. Archive members were
listed, not executed or unpacked.

HTML reading projections preserve 18 top-level tables and 66 PRE blocks.
Those counts include layout tables, source listings and other non-result
material. Two table projections exceeded the rich-table depth/node guard:
`longbottom-mips` table index 4 and `longbottom-whetstone-history` table index 1.
Their HTML and complete page text remain available; these are not silently
treated as empty tables. PDF signatures were checked for all four PDFs.

Two Netlib HTTPS requests timed out during the TLS handshake. Their HTTP
equivalents succeeded; both failed and successful attempts remain in run
manifests. The acquisition inventory records the latest successful URL/hash.

## Source families and research use

| Origin / collection | Acquired material | Research use and boundary |
| --- | --- | --- |
| [Longbottom Historic and Classic](http://www.roylongbottom.org.uk/#anchorClassic) | Gibson/ADP compilation, MIPS claims, historical and later Whetstone, Dhrystone, LINPACK, Livermore, Cray comparison, code bundles and Whetstone paper copy | Preserve version, precision, compiler and optimization distinctions; trace imported results to their earlier source |
| [Netlib benchmark archive](https://netlib.org/benchmark/) | Dhrystone, Whetstone, Livermore and NAS source distributions | Original program/rule evidence; shared program lineage does not prove comparable run conditions |
| [Netlib Dhrystone](https://www.netlib.org/performance/papers/dhrystone/) | Result table and contributor/compiler notes | Keep version and submitted configuration; some results may also occur in other compilations |
| [Dongarra LINPACK report](http://www.netlib.org/benchmark/performance.pdf) | Historical performance report PDF | Distinguish problem size, precision, optimization and processor counts |
| [NASA TM-86711](https://ntrs.nasa.gov/api/citations/19850024482/downloads/19850024482.pdf) | The NAS Kernel Benchmark Program, Bailey and Barton | Original scientific-kernel report, separate from later NAS Parallel Benchmarks |
| [Gabriel's book](https://dreamsongs.com/Files/Timrep.pdf) | Performance and Evaluation of Lisp Systems | Symbolic/programming-language workloads and runtime/compiler effects; PDF text includes PDP-10 and VAX discussions |
| [PERFECT index](https://www.netlib.org/performance/rank/perfect/) and [Southampton GBIS](https://www.netlib.org/parkbench/gbis/html/) | Result navigation and GENESIS suite description | Acquired discovery/method material; detailed result coverage has not yet been audited |
| [TUHS Dhampstone posting](https://www.tuhs.org/Usenet/comp.lang.c/1988-March/016129.html) | Archived discussion and program | Preserve posting identity, code variant and follow-up corrections; not yet a fitted score series |
| [Apple Assembly Line, 1981-10](https://txbobsc.com/aal/1981/aal8110.html) | Sieve discussion and assembly listings | Distinguish reprinted BYTE results, author retests and algorithm changes before extracting values |

The NASA report cover reads August 1985 (physical page 1); avoid assuming a
publication month from search-index snippets. PDF-to-text was used for discovery,
not full numerical table verification. No extracted score has entered the
VAXen calibration and no measurement-count claim is made from table counts.

## Next extraction targets and additional leads

1. Parse the Longbottom instruction-mix tables with their weights and
   architecture-adjustment rules; compare relevant machines with source manuals.
2. Build per-result provenance and configuration records for Dhrystone,
   Whetstone and LINPACK, retaining all source rows and disagreements.
3. Read Gabriel and the NAS report through the PDF pipeline before curating
   their numerical tables; preserve runtime and scalar/vector distinctions.
4. Follow the [BYTE 1981-09 scan](https://www.worldradiohistory.com/Archive-Byte/80s/Byte-1981-09.pdf)
   to the original Gilbreath article; this scan is a lead, not downloaded in
   this pass. It can anchor the reprints in Apple Assembly Line.
5. Recover Creative Computing's 1983-11 benchmark comparison and later updates.
   This remains a lead, not an acquired or verified result dataset.

Acquisition manifests and table/PRE locators supply provenance for the next
stage. Fitting remains deferred until workload identity and overlap coverage
are established at the result level.
