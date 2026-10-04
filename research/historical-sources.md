# Historical benchmark sources

Reviewed: 2026-09-26 to 2026-10-03. This report owns the acquired classical
benchmark sources, prior work, PDF table extraction, vendor reports, Usenet
result lists and early pre-benchmark timing evidence. How these results are
calibrated is in [classical fits](classical-fits.md); instruction mixes are in
[instruction mixes](instruction-mix.md). Curated values live in
[`data/curated/observation.jsonl`](../data/curated/observation.jsonl)
([schema](../docs/data-schema.md#curated_observation)) or, for the early
evidence, in [historical observations](data/historical/observations.jsonl)
([contract](data/historical/README.md)).

## Acquired classical sources

The first pass (2026-09-26) acquired 35 source objects (8,246,512 bytes): 17
HTML sources, seven ZIP archives (233 member entries, listed but not executed),
four PDFs, six source-code files and one PostScript report. They are files, not
35 independent datasets. The [acquisition inventory](data/classic/acquisition.csv)
records the latest successful URL and hash; the [collector](../docs/classic-collection.md)
owns commands. Two Netlib HTTPS requests timed out in the TLS handshake and their
HTTP equivalents succeeded; both attempts remain in run manifests.

| Origin / collection | Acquired material | Research use and boundary |
| --- | --- | --- |
| [Longbottom Historic and Classic](http://www.roylongbottom.org.uk/#anchorClassic) | Gibson/ADP compilation, MIPS claims, historical and later Whetstone, Dhrystone, LINPACK, Livermore, Cray comparison, code bundles | Preserve version, precision, compiler and optimization; trace imported results to their earlier source |
| [Netlib benchmark archive](https://netlib.org/benchmark/) | Dhrystone, Whetstone, Livermore and NAS source distributions | Program/rule evidence; shared lineage does not prove comparable run conditions |
| [Netlib Dhrystone](https://www.netlib.org/performance/papers/dhrystone/) | Result table and contributor/compiler notes | Keep version and configuration; some results recur in other compilations |
| [Dongarra LINPACK report](http://www.netlib.org/benchmark/performance.pdf) | Historical performance report PDF | Distinguish problem size, precision, optimization and processor counts |
| [NASA TM-86711](https://ntrs.nasa.gov/api/citations/19850024482/downloads/19850024482.pdf) | NAS Kernel Benchmark Program (cover August 1985) | Separate from the later NAS Parallel Benchmarks |
| [Gabriel's book](https://dreamsongs.com/Files/Timrep.pdf) | Performance and Evaluation of Lisp Systems | Symbolic workloads; PDP-10 and VAX discussions |
| [PERFECT index](https://www.netlib.org/performance/rank/perfect/), [Southampton GBIS](https://www.netlib.org/parkbench/gbis/html/) | Result navigation and GENESIS description | Coverage not yet audited |
| [TUHS Dhampstone posting](https://www.tuhs.org/Usenet/comp.lang.c/1988-March/016129.html) | Discussion and program | Not yet a fitted score series |
| [Apple Assembly Line, 1981-10](https://txbobsc.com/aal/1981/aal8110.html) | Sieve discussion and listings | Distinguish BYTE reprints, retests and algorithm changes |

Two HTML table projections exceeded the parser's depth/node guard
(`longbottom-mips` table 4, `longbottom-whetstone-history` table 1); their HTML
and text remain available. Leads not yet acquired: the
[BYTE 1981-09 scan](https://www.worldradiohistory.com/Archive-Byte/80s/Byte-1981-09.pdf)
for Gilbreath's original Sieve article, and Creative Computing's 1983-11
benchmark comparison.

## Prior work and further tables

The [literature register](data/classic/literature-sources.jsonl) is machine
readable.

- **Tomari and Hiraki (2011)**, [Retrospective Study of Performance and Power
  Consumption of Computer Systems](https://doi.org/10.2197/ipsjtrans.4.217),
  IPSJ Online Transactions 4, 217–227: 70 systems from 1989–2011 with C
  Dhrystone 2.1 and CINT2006 (correlation 0.986, §3.2). Dhrystone is single
  threaded and the paper's CINT2006 is not SPECrate; correlation is not held-out
  prediction accuracy.
- **DEC EC-N3909-10** v3.0 (1994-12), [Alpha and VAX Comparison based on
  Industry-standard Benchmark Results](https://vtda.org/docs/computing/DEC/VAX/EC-N3909-10_AlphaVAXComparison_Dec94.pdf):
  LINPACK 100x100 (§5) and a broad benchmark summary with SPEC92 and Whetstone (§7).
- **SSCL-375** (1991-09), [Benchmarks for the SSCL Physics Detector Simulation
  Computing Facility](https://lss.fnal.gov/archive/other/ssc/sscl-375.pdf):
  Table 2 juxtaposes MIPS, DP MFLOPS, SPECmarks and physics ratings for twelve
  systems. Appendix C's VAX result uses LINPACK n=300, so not every MFLOPS entry
  is n=100; manufacturer ratings and the authors' runs keep distinct provenance.
- **Lopez and Hilbert (2012)**, [methodological appendix](https://www.martinhilbert.net/LopezHilbertSupportAppendix2012.pdf)
  §E.1.3: Dhrystone version harmonization and SPECint89/2000 conversion
  assumptions; a synthesis precedent, not validation data.
- **CERN/HEPiX** ([Giordano et al. 2019](https://doi.org/10.1051/epjconf/201921408011),
  [suite instructions](https://twiki.cern.ch/twiki/bin/view/HEPIX/HEPIXBMKWG-SPEC2017)):
  coordinated Whetstone, HS06 and CPU2017 runs with JSON metadata; an
  execution-tool lead, no public result corpus verified. HS06 is a CPU2006 C++
  subset, not the official integer-rate aggregate.
- The [1990 comp.arch Dhrystone/SPEC discussion](https://groups.google.com/g/comp.arch/c/EfYPECBMzAY)
  asks the same predictive question and warns about version 1.1 compiler
  behavior; provenance only. SPEC-chain precedents are in
  [SPEC chains](spec-chains.md#prior-work-on-chaining-spec-generations).

## Three-source PDF extraction

Scope (2026-09-26): DEC EC-N3909-10 Section 7, SSCL-375 Tables 1–7/B-1/C-1/D-1/E-1
and Tomari/Hiraki Appendix Tables 1–2. Other figures, executive-summary ratios
and prose are not claimed as observations.

| Source | Table page-parts | Table rows | Numeric cells |
| --- | ---: | ---: | ---: |
| DEC, 1994-12 | 7 | 163 metric rows over 88 machine/OS columns | 1,210 |
| SSCL, 1991-09 | 11 | 99 | 316 |
| Tomari/Hiraki, 2011 | 5 | 70 hardware + 70 results | 572 |

The 2,098 numeric cells include hardware metadata; the long-form output has 3,082
records including missing and qualified cells. Originals are hashed blobs, and 57
checked corrections keep both OCR and reviewed strings. Recomputing the Pearson
correlation of Tomari's 28 Dhrystone/CINT2006 pairs gives 0.9859865321170843,
matching the paper's 0.986. DEC's report columns are curated observations
(2026-10-03): each cell keeps the printed value and label, and a
`reviewed_reading` reads printed KWIPS as MWIPS, bare Dhrystone numbers as
omitted-K values, and the page 29 VAX 4000/200 and 4000/300 Whetstone columns
(printed tenfold) at one tenth (4000/300: 6.25 DP / 8.93 SP MWIPS, as Longbottom
reports). SSCL and Tomari values are not fit inputs.

Outputs: [table evidence and schema](data/classic/pdf-extraction/README.md),
[structured snapshot](data/classic/pdf-extraction/tables.jsonl),
[Tomari configurations/results](data/classic/pdf-extraction/tomari-configurations.csv),
[counts](data/classic/pdf-extraction/summary.csv) and
[audit](data/classic/pdf-extraction/audit.json). `classic extract-pdf-tables`
regenerates the long-form CSV/JSONL in `data/derived/classic/pdf-tables/`.

## Vendor performance reports

Vendor reports print many benchmarks for their own and competitors' machines in
one table: dense overlap sources, but each row must say who measured it, and rows
copied from another publication are not independent evidence.

### Digital RISC Family Performance Summary, 1990

Source `src:dec-risc-performance-summary-1990`, Digital Equipment Corporation,
1990-04-02, 35 pages ([PDF](https://web-docs.gsi.de/~kraemer/COLLECTION/DEC/ds5000.cpu.pdf),
BLAKE3 `a0685206…bd85`). Every value was checked against its page's text layer;
the bar figures on pp. 25 and 30 print each value.

| Page | Content | Rows |
| --- | --- | --- |
| 7 | SPECmark89 table | context only (same runs as the SPEC89 package) |
| 21 | LINPACK n=100, DP/SP, standard/rolled BLAS | DP rolled BLAS as calibration input; others context |
| 24 | Whetstone KWIPS DP/SP at -O3 and -O4, DEC systems | -O3 as calibration input; -O4 context |
| 25 | Whetstone figure, -O3, DEC and competitor systems | SPARCstation 1/330, Sun-4/260 FPU1, HP 9000/835 |
| 30 | Dhrystone V1.1 and V2.1 figure, -O3 | both versions |
| 31–32 | System configurations | `conditions` (processor, FPU, clock, memory, OS, compiler) |

87 rows, 43 of them calibration inputs, across 11 report columns. Dhrystones/s ÷
1757 = DMIPS and KWIPS ÷ 1000 = MWIPS (this report prints thousands: DS5000/200
DP 14,271 KWIPS = 14.271 MWIPS), so the N3909 reading does not apply. Context
only: Sun-4/260 FPU2 (a different FPU, measured by Sun), "SPARCsystem 300" (a
family), the SPECmark89 table and other LINPACK/Whetstone variants. Values equal
to Netlib entries (DECstation 3100, DECstation 5000/200 Dhrystone; DECstation
3100, SPARCstation 1 and Sun-4/260 LINPACK) list the other source in
`duplicates`. "Sun-4/260 FPU1" resolves to `sys:sun4/260` by a reviewed alias
(its SPECmark 5.7 equals the package's 5.71). The nine systems have SPEC89 but no
SPECint92 results, so they add SPECint89-inferred targets. Not transcribed: the
Livermore loops, DR Labs CPU2, application benchmarks and the p. 33 SPEC89
per-benchmark times.

### MIPS Performance Brief 3.5, 1988

Source `src:mips-performance-brief-3.5-1988`: John Mashey's comp.arch posting
`<7000@winchester.mips.COM>` (1988-10-26), an extract of the printed issue, from
UTZOO tape `news087f1.tgz` member `b108/comp/arch/6868` (BLAKE3 `35e43455…36bf`).
Every value was matched against the message text.

| Table | Rows used for calibration | Context only |
| --- | --- | --- |
| Dhrystone optimization effects (section 4) | Highest register result without inlining (-O3, or -O), Dhrystone 1.1 for 11 columns and 2.1 for M/120-5 and M/2000-8 | -O4 (inlining) |
| Whetstone (section 5.6) | MIPS's own rows: M/500 to M/2000-8, VAX 11/780 (4.3BSD f77 and LLL compiler), Sun-3/260 | M/2000-8 -O4; Intel 80386 rows posted by Intel |
| LINPACK n=100 (section 5) | VAX 11/780, 4.3BSD, LLL Fortran | MIPS rows copied from Dongarra (duplicate Netlib) |

48 rows, 30 calibration inputs, in 14 results. Uncited rows are `source_author`
for MIPS's own machines and `unattributed` for other vendors'. "MIPS M/2000-8"
resolves to `sys:m/2000` by a reviewed alias (25 MHz R3000, 64K + 64K cache, as
in the SPEC89 package). Only M/120-5 and M/2000 have SPEC89 targets.

Earlier Briefs (1986-10-15, 1987-04-02, 1987-10-29 with errata 1987-11-03 and
1987-11-12) are in UTZOO but not transcribed: they report the same machines with
older compilers and would weight one vendor several times. Issue 3.9 (1990-01),
cited by the DEC summary, has not been found.

## Usenet result lists

All posts come from the UTZOO archive ([sources](../docs/sources.md#utzoo-usenet-archive));
each one used is stored as a raw blob and cited by message ID, tape and member
path in [`data/curated/source.jsonl`](../data/curated/source.jsonl).

### Rick Richardson's Dhrystone lists, 1985–1989

Richardson (PC Research, Inc.) posted readers' Dhrystone results to net.arch and
comp.arch about every three months; he did not re-run them. Each list includes
the earlier rows, so only the last of each version is used, parsed by
[`classical/usenet_results.py`](../python-src/cpushowspeed/classical/usenet_results.py):

| Source | Format | Check |
| --- | --- | --- |
| `src:richardson-dhrystone-1.1-1987-09-20` (`<380@pcrat.UUCP>`) | Shell archive; `report.doc` prints every row twice, by manufacturer and by performance | Both listings hold the same 297 rows |
| `src:richardson-dhrystone-1.1-db-1987-05-18` (`<311@pcrat.UUCP>`) | `dry.db`, tab-separated | Gives submission dates to 204 of the 297 rows |
| `src:richardson-dhrystone-2-db-1989-04-30` (`<754–756@pcrat.UUCP>`) | Uuencoded `raw.db` | Equals, row for row, the same day's boxed report |
| `src:richardson-dhrystone-2-1989-04-30` | Uuencoded, compressed by-performance report | Used only for that check |

Earlier lists (1985-11-08 `<1129@hou2h>` through 1988-12-04) are located. Rules:
the register score is used (the no-register value only when the register value
is not positive); Dhrystones/s ÷ 1757 = DMIPS; the 2.0/2.1 database maps to
Dhrystone 2.1 and keeps "2.0 or 2.1"; Pascal (17) and Ada (8) rows are excluded;
one overflowed Amdahl 5890/300E row is excluded; a clock of 0.00 means unknown;
the submission date is an upper bound on the test date and is not used as a
hardware date. That gives 296 Dhrystone 1.1 and 274 Dhrystone 2 observations,
mostly pre-SPEC machines with no SPEC target. The later Netlib (Aburto) table
shares few rows; both are used.

Five VAX 11/780 rows (4.2BSD, Mach, VMS 4.3 and System V compilers) print
1,307–1,640 Dhrystones/s, 0.74–0.93 DMIPS: the VAX/VMS figure of 1,757 that
defines one DMIPS is the top of that range, not its center.

### Smaller result posts, 1990–1991

Hand-transcribed and matched against the message text (`usenet_text_checked`).

- **SSBA 1.21F** (`src:ssba-hp9000-720-sparcstation2-1991`): Nhuan Doduc's
  comp.benchmarks post `<1575@ftc.framentec.fr>` (1991-03-22; English
  translation `<1993@kuling.UUCP>`) of full AFUU SSBA runs on the HP 9000/720
  (50 MHz, HP-UX 8.01, run 1991-02-22) and SPARCstation 2 (40 MHz, SunOS 4.1.1,
  1990-11-29). Calibration inputs: `dhryro` (Dhrystone 1.1, per
  `src:ssba-dhrystone-list-1991`), `whets`/`whetd` (Whetstone SP/DP) and
  `linpackrd` (LINPACK double rolled); other lines are context. 20 rows, 8 inputs.
- **LINPACK on Sun** (`src:nefzger-linpack-sparc-1990`): Tristan Nefzger,
  `<14274@leadsv.UUCP>` (1990-12-04), Sun FORTRAN 1.3.1 at four optimization
  levels. The `-O3` double-precision summary is used: 3.3 (SPARCstation 2), 1.6
  (SPARCstation 1+) and 3.1 (Sun 4/490) MFLOPS.
- **Livermore Fortran Kernels on the IBM RS/6000 320**
  (`src:mccalpin-lfk-rs6000-320-{64,32}bit-1990`): John McCalpin's comp.unix.aix
  posts of 1990-11-11. The 72-sample harmonic, geometric and arithmetic means
  are transcribed as `Livermore:LFK72_{HM,GM,AM}_MFLOPS` (64-bit 4.8474 / 6.9979
  / 9.3237; 32-bit 4.2465 / 5.6566 / 7.2943); the program's reference results for
  other machines are `cited_third_party`. All are context: the network has no
  Livermore family.

LINPACK-only estimates of these Sun systems fall below their SPEC results
(SPARCstation 2 SPECint92 21.8): LINPACK n=100 on Sun's 1990 Fortran was low
relative to integer speed.

### Printed SPEC89 means, 1990–1991

About 850 UTZOO posts mention SPEC results. Their integer-mean lines were
compared with the [SPEC89 package plus Helman](data/spec89/aggregate89-plus-helman.csv);
four posts print means the package lacks. SPECint89 is a calibration input,
SPECfp89 and SPECmark89 context.

| Source | Systems | SPECint89 / SPECfp89 / SPECmark89 | Basis |
| --- | --- | --- | --- |
| `src:mashey-ymmv-88k-1990`: John Mashey (MIPS), "Re: Fastest 88k", comp.arch `<42586@mips.mips.COM>`, 1990-10-31 | Data General AV/410, 20 MHz | 11.3 / 8.3 / 9.4 | SPEC newsletter, Spring 1990 |
| | Data General AV/6200, 25 MHz | 15.3 / 11.3 / 12.7 | Winter 1990 |
| | Motorola 8864SP, 20 MHz | 14.6 / 10.8 / 12.2 | Winter 1990 |
| | Motorola 8864SP, 25 MHz | 18.3 / 13.5 / 15.2 | Winter 1990 |
| | Motorola 8612, 33 MHz | 21.4 / 15.8 / 17.8 | Winter 1990 |
| | MIPS Magnum (RC3230), 25 MHz | 19.4 / 16.8 / 17.8 | Summer 1990 |
| `src:ragan-cdc4680-spec-1991`: Rich Ragan (Control Data), comp.arch `<32097@shamash.cdc.com>`, 1991-04-08 | MIPS RC6280 | 45.8 / 45.6 / 45.7 | Control Data's run, MIPS 2.20 compilers |
| | CDC 4680 | 45.8 / 63.5 / 55.7 | Same hardware, CDC/KAI FORTRAN; submitted to SPEC |
| `src:mashey-rc3360-spec-1991`: John Mashey, "Re: r4000", comp.arch `<46252@mips.mips.COM>`, 1991-02-27 | MIPS RC3360, 33 MHz | 27.1 / 26.2 / 26.5 | Vendor statement |
| `src:torrie-harris-nighthawk-spec-1991`: Evan Torrie, comp.sys.next `<1991Apr27.004627.27205@neon.Stanford.EDU>`, 1991-04-27 | Harris Night Hawk, 25 MHz 88000 | 20.02 / 15.73 / 17.32 | Unattributed; all three context |

Mashey's table extracts MIPS's *Your Mileage May Vary* issue 2.0; its two
Motorola MPC rows are his estimates and are not transcribed. SPECint89 targets
are taken from any source except the SPEC89/92 bridge table and reference
definitions, so these rows add nine SPEC89 records. The CDC 4680's LINPACK
result was merged into `sys:cdc4680` with the N3909 curated records
(2026-10-03). Posts that only repeat package values or lack a mean: Michael
Slater `<39825@cup.portal.com>` (1991-03-04), Mashey `<42280@mips.mips.COM>`
(1990-10-22), Alan Lovejoy `<7377@pdn.paradyne.com>` and Frederic Despoix
`<7521@imag.imag.fr>` (1990-02, *Microprocessor Report* ratios; the VAX 6000
Model 410 and 450 ratios are evidently copied), and Tom Horsley (Harris,
1990-10-31).

### Posts examined and not transcribed

- Paul Raveling, "Workstation benchmarks (long!!)", comp.unix, 1990-07-13
  (`<3694@zorba.Tynan.COM>`): only ratios to the fastest machine.
- Kevin Carosso, fa.info-vax, 1985-09-11 (`<8509120034.AA04869@cit-vax.ARPA>`):
  Whetstone timings given from memory.
- Alfred Aburto, "Nsieve Results", comp.arch, 1989-05-17 (`<1164@marlin.NOSC.MIL>`):
  sieve times; the model has no sieve family.
- The SSBA result list (`src:ssba-dhrystone-list-1991`): about 110 systems
  published in Tribunix (AFUU, issues 27–35) and IX Magazine (1990), a lead for
  1989–90 Dhrystone 1.1, Whetstone and LINPACK.

## Early timing evidence

A bounded first pass (2026-09-26) over the local watchlist corpus; canonical
values and hashes are in [historical observations](data/historical/observations.jsonl).
These are source timing inputs, not reconstructed benchmark scores.

### Honeywell 300

[Programmers Reference Manual](https://bitsavers.org/pdf/honeywell/h300/Honeywell_300_Programmers_Reference_Manual_Aug64.pdf),
physical page 10 (printed 2): Gibson mix rating 180,000 instructions/s without
memory interlace and 236,000 with (two configurations); main-memory cycle 1.75 µs;
fixed-point add 3.5 µs. Weights, options and provenance of the rating are not
stated, so it is not the CCTA variant. Physical page 24 (printed 19) defines
execution timing (indexed addressing adds at most half a cycle, indirect one
cycle per level); Appendix G (pages 105–107) is an unreviewed timing summary.

### Original PDP-8

[User's Handbook](https://bitsavers.org/pdf/dec/pdp8/pdp8/F-85_PDP-8_Users_Handbook_May66.pdf),
physical page 25 (printed 10): 1.5 µs memory cycle; indirect addressing adds
1.5 µs; AND is 3.0 µs direct and 4.5 µs indirect. Not timings for PDP-8/I or /E.

### DEC programming-benchmark memo

[Programming Benchmarks](https://bitsavers.org/pdf/dec/pdp11/memos/700325_Programming_Benchmarks.pdf),
physical pages 3–4: its coded programs were not run; it compares instruction
sets by words, instruction counts and memory cycles. Analytical ISA evidence, not
measured throughput. It points to PM18-3 (Cohen and McGowan, 1968-05-31), not
yet recovered.

### LGP-30

[Programming Manual](https://bitsavers.org/pdf/generalPrecision/LGP-30/manuals/LGP-30_Programming_Manual_195704.pdf),
physical page 11 (printed 8): a 17 ms drum revolution and about 0.26 ms
recirculating-register sector access, distinct storage paths and not an
instruction time. They were found only after widening the search to drum
terminology, so zero keyword hits do not prove missing timing information.

### OCR reliability

OCR and DocIR output are reading aids; every curated value above was checked on
the rendered original page. A targeted check of Chandra on *A General-Purpose
Time-Sharing System* (2026-09-26) found that its Mermaid code changed a figure's
edges (`PDP1 <--> Displays` instead of Q-32 → Displays → PDP-1), that a hardware
diagram on page 2 was omitted entirely, and that a misspelled row label
(`Inut/Output`) must not be silently corrected. Structured figure code and image
`alt` text help retrieval but do not prove a figure was transcribed or emitted;
important diagrams, numeric charts and suspected missing figures need visual
review.
