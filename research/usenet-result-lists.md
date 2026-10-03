# Usenet result lists

Reviewed: 2026-10-03. Status: Rick Richardson's Dhrystone lists are parsed from
the stored postings by
[`usenet_results.py`](../python-src/cpushowspeed/usenet_results.py) and used by the
classical network. Smaller result posts (SSBA, SPARC LINPACK, Livermore kernels)
are hand-transcribed as curated observations. All posts here come from the UTZOO archive
([sources](../docs/sources.md#utzoo-usenet-archive)); each one used is stored as a
raw blob and cited by message ID, tape and member path in
[`data/curated/source.jsonl`](../data/curated/source.jsonl).

## Rick Richardson's Dhrystone lists, 1985–1989

Rick Richardson (PC Research, Inc.) collected Dhrystone results that readers
mailed to him and posted the list to net.arch and later comp.arch about every
three months. The results were submitted by many people and were not re-run by
him. They are recorded as `historical_source_observation`, one result per row.

### Postings located

| Date | Message | Content |
| --- | --- | --- |
| 1985-11-08 | `<1129@hou2h>` | First list |
| 1985-12-13, 1986-02-18, 1986-03-31 | | Lists |
| 1986-08-14 | `<1863@homxb.UUCP>` | Report and raw database |
| 1986-10-15, 1987-01-31, 1987-03-15 | | Lists with `dry.db` |
| 1987-05-18 | `<311@pcrat.UUCP>` (part 2) | `dry.db`, 252 rows with submission date and submitter |
| 1987-09-20 | `<380@pcrat.UUCP>` (part 1) | Final Dhrystone 1.1 list, `report.doc`, 297 rows |
| 1988-03-13 | | Dhrystone 2.0 first results |
| 1988-07-06, 1988-07-14 | `<520@pcrat.UUCP>`, `<528@pcrat.UUCP>` | Dhrystone 2 results and raw database (199 rows) |
| 1988-12-04 | `<633@pcrat.UUCP>`, `<634@pcrat.UUCP>` | Dhrystone 2 results |
| 1989-04-30 | `<754@pcrat.UUCP>`, `<755@pcrat.UUCP>`, `<756@pcrat.UUCP>` | Dhrystone 2 results (two parts; part 1 holds the by-performance report) and raw database (299 rows) |

Each Dhrystone 1.1 list includes the rows of the earlier ones, and so does each
Dhrystone 2 list. Only the last of each is used: the 1987-09-20 Dhrystone 1.1
list and the 1989-04-30 Dhrystone 2 database.

### What is parsed and how it is checked

| Source | Format | Check |
| --- | --- | --- |
| `src:richardson-dhrystone-1.1-1987-09-20` | Shell archive; `report.doc` prints every row twice, sorted by manufacturer and by performance, in fixed-width columns | The two listings must hold the same 297 rows |
| `src:richardson-dhrystone-1.1-db-1987-05-18` | Shell archive; `dry.db`, a tab-separated Prelude database | Gives submission dates to 204 of the 297 report rows, matched on manufacturer, model and both scores |
| `src:richardson-dhrystone-2-db-1989-04-30` | Shell archive; uuencoded `raw.db` | Must equal, row for row, the boxed report of the same day |
| `src:richardson-dhrystone-2-1989-04-30` | Shell archive; uuencoded, `compress`ed by-performance report | Used only for the check above |

Rules:

- **Score.** Each row prints Dhrystones per second without and with `register`
  variables. The register value is used; the no-register value is used only
  when the register value is zero or negative. Dhrystones/s ÷ 1757 = DMIPS.
- **Version.** The 1.1 list maps to `Dhrystone:v1.1_DMIPS`. Richardson's
  Dhrystone 2 database mixes 2.0 and 2.1 runs, which he states are comparable;
  it maps to `Dhrystone:v2.1_DMIPS`, and the record keeps the version as "2.0
  or 2.1".
- **Language.** The Dhrystone 2 distribution included Pascal and Ada versions.
  Rows whose compiler is Pascal (17) or Ada (8) are excluded; C rows are kept.
- **Invalid values.** One Dhrystone 1.1 row (Amdahl 5890/300E) prints a negative,
  overflowed score and is excluded.
- **Clock.** A printed clock of 0.00 means unknown.
- **Dates.** The submission date (`submitted_on`, read as US month/day/year) is
  when the result was sent to Richardson. It is an upper bound on the test date,
  not a hardware date, and the timeline does not use it.

That gives 296 Dhrystone 1.1 and 274 Dhrystone 2 observations, 570 in all.
The machine name is the manufacturer and model columns joined. Every row
resolves to a system ID by name. Most machines are pre-SPEC (PCs, 68000
workstations, minicomputers and mainframes) and have no SPEC target, so in the
network they are Dhrystone-only nodes.

The later Netlib Dhrystone table (Aburto, 1990s) shares few rows with
Richardson's lists. Both are used.

Generic names group different machines under one system key: "PC/AT" covers
6–9 MHz ATs and accelerated boards, and "Homebrew" and "Macintosh" are not one
configuration. The network's frequency checks list these groups (27 rows, up
from 7); their configurations are not reviewed.

### Effect on the calibration

The new rows give Dhrystone results to about 20 more systems that already had
Whetstone or LINPACK results (for example Amdahl 5860, Apollo DN3000/DN4000,
Gould PN6005/PN9080, Pyramid 90x), so informative systems rise 495 → 515
(`with_spec89`). Only six of the matched systems have a SPEC target (VAX 11/780,
VAX 8700, DECstation 3100, MIPS M/2000, HP 9000/370 and Sun-4/260); VAX 8700 adds
one SPECint89-inferred node (121 → 122). `linear_clock / with_spec89`
coefficients: Dhrystone 1.1 0.64775 → 0.64513 (−0.40%), Dhrystone 2.1 0.69674 →
0.68453 (−1.75%), LINPACK +1.12%, Whetstone −0.45% to −1.13%. The other details
are in the [network](classic-network-fitting.md#changes-from-richardsons-dhrystone-lists-2026-10-03),
[SPEC89 bridge](spec89-bridge.md#changes-from-richardsons-dhrystone-lists-2026-10-03)
and [timeline](unified-vaxen-timeline.md#richardsons-dhrystone-lists--2026-10-03).

Five VAX 11/780 rows (4.2BSD, Mach, VMS 4.3 and System V compilers) print
1,307–1,640 Dhrystones/s, 0.74–0.93 DMIPS. The VAX/VMS figure of 1,757 that
defines one DMIPS is the top of that range, not its center.

## Smaller result posts, 1990–1991

These posts are hand-transcribed into
[`data/curated/observation.jsonl`](../data/curated/observation.jsonl). Every
value was matched against the message text (`usenet_text_checked`).

### SSBA 1.21F: HP 9000/720 and SPARCstation 2, 1991

Source: `src:ssba-hp9000-720-sparcstation2-1991`, Nhuan Doduc's comp.benchmarks
post `<1575@ftc.framentec.fr>` (1991-03-22) of two full runs of the AFUU's SSBA
suite: HP 9000/720 (50 MHz, 64 MB, HP-UX 8.01; run 1991-02-22) and
SPARCstation 2 (40 MHz, 16 MB, SunOS 4.1.1; run 1990-11-29). Bo Thidé's English
translation, `<1993@kuling.UUCP>` (1991-03-25), has the same values. Doduc
states in `<1991Jan17.003521.4137@ox.com>` (`src:ssba-dhrystone-list-1991`) that
SSBA results contain Dhrystone 1.1.

| SSBA line | Calibration input | Context |
| --- | --- | --- |
| `dhryro` (registers, optimized) | Dhrystone 1.1 | `dhrynr`, `dhryr`, `dhrynro` |
| `whets`, `whetd` (optimized) | Whetstone SP and DP, KWIPS ÷ 1000 | |
| `linpackrd` (double, rolled) | LINPACK n=100, KFLOPS ÷ 1000 | `linpackud`, `linpackrs`, `linpackus` |

The DP rolled choice follows the 1990 DEC report. The HP run prints identical
single- and double-precision LINPACK values (8,803 and 13,733 KFLOPS); they are
transcribed as printed. That gives 20 rows, 8 of them calibration inputs. Both
systems have SPECint92 results.

### LINPACK on SPARCstation 2, SPARCstation 1+ and Sun 4/490, 1990

Source: `src:nefzger-linpack-sparc-1990`, Tristan Nefzger (Lockheed),
comp.benchmarks `<14274@leadsv.UUCP>` (1990-12-04). Dongarra's `linpacks` and
`linpackd` were compiled with Sun FORTRAN 1.3.1 at four optimization levels and
timed with `times()` at 1/60 s. The summary table at `-O3` is used: double
precision 3.3 (SPARCstation 2), 1.6 (SPARCstation 1+) and 3.1 (Sun 4/490) MFLOPS
are calibration inputs, and single precision is context. The SPARCstation 2
`-O3` run listing (5.086–5.215 MFLOPS single precision) agrees with its summary
value of 5.1. The SPARCstations ran a SunOS 4.1.1 beta.

### Livermore Fortran Kernels on the IBM RS/6000 Model 320, 1990

Sources: `src:mccalpin-lfk-rs6000-320-64bit-1990` and
`src:mccalpin-lfk-rs6000-320-32bit-1990`, John McCalpin's comp.unix.aix posts
`<MCCALPIN.90Nov11075136@pereland.cms.udel.edu>` (64-bit) and
`<MCCALPIN.90Nov11074522@pereland.cms.udel.edu>` (32-bit), 1990-11-11. Each is the
complete output of the LFK program (version 22/dec/86 mf392) on a 20 MHz Model
320 with AIX 3.1 and `xlf -O`, with `MULTI=50`.

The 72-sample harmonic, geometric and arithmetic means are transcribed for both
precisions as new metrics `Livermore:LFK72_{HM,GM,AM}_MFLOPS` (registry
`livermore-72`): 64-bit 4.8474 / 6.9979 / 9.3237, 32-bit 4.2465 / 5.6566 /
7.2943. The speed-up table also prints the program's built-in reference
results for the Cray Y-MP1, IBM 3090S180, CDC Cyber 180-875, MIPS M/2000 and
VAX 11/785. They are transcribed as `cited_third_party` context, since McCalpin
did not run them.

All Livermore rows are `context`. The classical network has no Livermore
family; adding one would be a method change and needs more than one measured
system.

### Effect on the calibration

The eleven calibration inputs form five results on systems the network already
had, so node and informative-system counts are unchanged. `linear_clock /
with_spec89` coefficients move little (Whetstone SP +1.10%, LINPACK +0.32%,
others within ±0.13%). The timeline gains five classical records, 5.02
(SPARCstation 1+, LINPACK only) to 30.21 (HP 9000/720) speed-VAXen.

The HP 9000/720 and SPARCstation 2 enter the common observed-SPECint92 holdout
cohort (33 → 35 systems), and its P95 rises (all-available 17.99% → 20.17%). The
HP 9000/720's observed node is a 1996 Netlib SPECint92 disclosure (peak 64.0)
made with later compilers than the 1991 SSBA run, which predicts 33.9; against
its 1991 SPECint89 results the same vector is 8–11% low. This is a configuration
mismatch that pairing by system does not catch, not a transcription error.
Details are in the [network](classic-network-fitting.md#changes-from-the-smaller-usenet-result-posts-2026-10-03),
[composite](classic-composite-fitting.md#smaller-usenet-result-posts-2026-10-03),
[SPEC89 bridge](spec89-bridge.md#changes-from-the-smaller-usenet-result-posts-2026-10-03)
and [timeline](unified-vaxen-timeline.md#smaller-usenet-result-posts--2026-10-03)
reports.

## Posts examined and not transcribed

- **Paul Raveling, "Workstation benchmarks (long!!)", comp.unix, 1990-07-13**
  (`<3694@zorba.Tynan.COM>`). It reports only speed ratios relative to the
  fastest machine (HP 9000/370, an unnamed Sun 4 model, Sun 3/80 and VAX 8650),
  with no absolute scores.
- **Kevin Carosso, "My benchmark collection", fa.info-vax, 1985-09-11**
  (`<8509120034.AA04869@cit-vax.ARPA>`). Whetstone timings are given from
  memory ("about 1.3 CPU seconds" on a VAX 11/785 with FPA), and the rest is
  VAX instruction-timing code.
- **Alfred Aburto, "Nsieve Results", comp.arch, 1989-05-17**
  (`<1164@marlin.NOSC.MIL>`). Sieve run times for 48 configurations at six
  array sizes. The model has no sieve family.
- **SSBA result list** (`src:ssba-dhrystone-list-1991`). Doduc lists about 110
  systems whose SSBA results were published in Tribunix (AFUU newsletter,
  issues 27–35, 1989–1990) and IX Magazine (1990). The results are not in the
  post. Those issues are a lead for Dhrystone 1.1, Whetstone and LINPACK on
  1989–90 European and US systems.
