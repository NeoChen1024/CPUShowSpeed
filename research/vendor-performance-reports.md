# Vendor performance reports

Reviewed: 2026-10-03. Status: the 1990 DEC summary and MIPS Performance Brief
3.5 are transcribed into
[`data/curated/observation.jsonl`](../data/curated/observation.jsonl)
([schema](../docs/data-schema.md#curated_observation)) and used by the classical
network. Earlier Brief issues (1986–1987) are located but not transcribed.

Vendor reports print many benchmarks for their own and competitors' machines in
one table. They are dense overlap sources, but each row must say who measured it,
and rows copied from another publication are not independent evidence.

## Digital RISC Family Performance Summary, 1990

Source: `src:dec-risc-performance-summary-1990`, Digital Equipment Corporation,
dated 1990-04-02, 35 pages
([PDF](https://web-docs.gsi.de/~kraemer/COLLECTION/DEC/ds5000.cpu.pdf), retrieved
2026-10-03, BLAKE3 `a0685206…bd85`). The PDF has a text layer. Every transcribed
value was checked against the text of its cited page (`pdf_text_layer_checked`).
The bar figures on pp. 25 and 30 print the value beside each bar, so no value was
read from a bar length.

### What was transcribed

| Page | Content | Rows |
| --- | --- | --- |
| 7 | SPECmark89 table | context only (same runs as the SPEC89 package) |
| 21 | LINPACK n=100, DP/SP, standard/rolled BLAS | DP rolled BLAS as calibration input; otherwise DP standard; other variants as context |
| 24 | Whetstone KWIPS DP/SP at -O3 and -O4, DEC systems | -O3 as calibration input; -O4 as a separate context result |
| 25 | Whetstone figure, -O3, DEC and competitor systems | competitor values (SPARCstation 1/330, Sun-4/260 FPU1, HP 9000/835) |
| 30 | Dhrystone V1.1 and V2.1 figure, -O3, five million loops | both versions |
| 31–32 | System configurations | `conditions` (processor, FPU, clock, memory, OS, compiler) |

That gives 87 rows, 43 of them `calibration_input`, across 11 report columns. Units
are converted as printed: Dhrystones/s ÷ 1757 = DMIPS, and KWIPS ÷ 1000 = MWIPS.
This report prints thousands of Whetstone instructions per second (DS5000/200 DP:
14,271 KWIPS = 14.271 MWIPS), so the N3909 rule that reads a KWIPS label as MWIPS
does not apply to it.

Rows that are context only, and why:

- **Sun-4/260 FPU2.** A different floating-point option, measured by Sun ([SUN89]).
- **SPARCsystem 300.** A family name, not one model; Sun ran its V1.1 value at -O4.
- **SPECmark89 (p. 7).** The DEC and Sun values equal the SPEC89 package's
  (e.g. DS5000/200 18.5; recomputed from the p. 33 elapsed times: 18.55). They
  stay in the package.
- **Other LINPACK and Whetstone variants.** The fit uses one value per metric and
  column.

### Duplicates and identity

The values are identical to entries already in Netlib for DECstation 3100,
DECstation 5000/200 (Dhrystone), and DECstation 3100, SPARCstation 1 and Sun-4/260
(LINPACK). These rows list the other source in `duplicates`. Both copies still
enter the network as results of one system; the network's system-median weighting
limits their weight.

"Sun-4/260 FPU1" resolves to `sys:sun4/260` through a reviewed alias: its p. 8
SPECmark of 5.7 equals the SPEC89 package's 5.71 for that system. HP 9000/835
stays separate from 9000/835SE. The report gives no year for SPARCstation 330 or
HP 9000/835, so their timeline rows are undated.

### Effect on the calibration

The nine systems have SPEC89 results but no SPECint92, so they add
SPECint89-inferred targets, not observed anchors. Every one is underpredicted by
the single-metric joint SPEC89 fits: Dhrystone by 14–30%, Whetstone by 9–57% and
LINPACK by 5–65%. Relative to these benchmarks, 1989–90 RISC workstations score
higher on SPECint89 than the training population does. Classical coefficients rise:
`linear_clock / with_spec89` Dhrystone 1.1 by 0.43%, LINPACK by 1.27% and
Whetstone SP by 10.9%. Details are in the
[network](classic-network-fitting.md#changes-from-the-1990-dec-report-rows-2026-10-03),
[SPEC89 bridge](spec89-bridge.md#changes-from-the-1990-dec-report-rows-2026-10-03)
and [timeline](unified-vaxen-timeline.md#1990-dec-report-rows--2026-10-03).

### Not transcribed

The Livermore loops, DR Labs CPU2, application benchmarks and the p. 33 SPEC89
per-benchmark times are not transcribed. The report cites MIPS Performance Brief
issue 3.9 (1990-01) and SPEC Newsletter vol. 2 no. 1 (Winter 1990).

## MIPS Performance Brief 3.5, 1988

Source: `src:mips-performance-brief-3.5-1988`. This is the comp.arch posting
`<7000@winchester.mips.COM>` by John Mashey, the Brief's editor, dated
1988-10-26. It is an extract of the printed issue. It is UTZOO tape
`news087f1.tgz`, member `b108/comp/arch/6868`; the tape's MD5 matches the
archive.org item. The message bytes are stored as a raw blob (BLAKE3
`35e43455…36bf`, 69,458 bytes). Every printed value was matched against the
message text (`usenet_text_checked`).

| Table | Rows used for calibration | Context only |
| --- | --- | --- |
| Dhrystone optimization effects (section 4) | Highest register result without inlining (-O3, or -O where no -O3 is printed), Dhrystone 1.1 for 11 columns and 2.1 for M/120-5 and M/2000-8 | -O4 (inlining, "beyond the spirit of the benchmark") |
| Whetstone (section 5.6) | MIPS's own rows: M/500 to M/2000-8, VAX 11/780 (4.3BSD f77 and LLL compiler), Sun-3/260 | M/2000-8 -O4; Intel 80386 rows posted by Intel ([Purkiser 87]) |
| LINPACK n=100 (section 5) | VAX 11/780, 4.3BSD, LLL Fortran ([ours]) | MIPS rows, which are from [Dongarra 88] and duplicate the Netlib report |

That gives 48 rows, 30 of them calibration inputs, in 14 results. The Brief says
its tested configurations are in-house systems, and those configurations are the
`conditions` of the MIPS rows. Rows with no citation are recorded as
`source_author` for MIPS's and its own VAX 11/780 measurements, and
`unattributed` for other vendors' machines. The cited Dhrystone list
([Richardson 87] and others) is not transcribed; Richardson's own postings are
in UTZOO and are the source to use. The relative summary table is derived and
is not transcribed.

"MIPS M/2000-8" resolves to `sys:m/2000` through a reviewed alias. The Brief's
tested M/2000-8 (25 MHz R3000, 64K I-cache, 64K D-cache) matches the SPEC89
package's MIPS M/2000 (25.0 MHz, 64 KB I + 64 KB D).

Effect: only M/120-5 and M/2000 have SPEC89 targets. Both are underpredicted
like the DEC systems: Dhrystone by 19–24%, Whetstone by 38–40% and LINPACK by 23%.
`linear_clock / with_spec89` coefficients change by −0.3% to +0.4%; the
exception is Whetstone SP, +5.1%. The VAX 11/780 rows show that classical routes
give the reference machine 0.34–0.67 speed-VAXen
([timeline](unified-vaxen-timeline.md#mips-performance-brief-35-rows--2026-10-03)).

## Earlier MIPS Performance Briefs (located)

These are also in UTZOO (comp.arch and net.arch): 1986-10-15 (M/500 development
system), 1987-04-02, and 1987-10-29 with errata on 1987-11-03 and 1987-11-12.
They report the same MIPS machines with older compilers. Adding them would weight
one vendor's machines several times, so they are context for compiler effects
unless a later issue lacks a value. The DEC summary cites issue 3.9 (1990-01),
which has not been found.
