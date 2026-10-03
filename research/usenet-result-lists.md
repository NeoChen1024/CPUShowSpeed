# Usenet result lists

Reviewed: 2026-10-03. Status: Rick Richardson's Dhrystone lists are parsed from
the stored postings by
[`usenet_results.py`](../python-src/cpushowspeed/usenet_results.py) and used by the
classical network. Smaller result posts (SSBA, SPARC LINPACK, Livermore kernels)
and printed SPEC89 means missing from the SPEC89 package are hand-transcribed as
curated observations. All posts here come from the UTZOO archive
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

## Printed SPEC89 means, 1990–1991

About 850 UTZOO posts mention SPEC results. Their integer-mean lines were
extracted and compared with the [SPEC89 package plus the Helman
supplement](data/spec89/aggregate89-plus-helman.csv). Four posts print means
the package lacks. They are transcribed into
[`data/curated/observation.jsonl`](../data/curated/observation.jsonl)
(`usenet_text_checked`): SPECint89 as a calibration input, SPECfp89 and
SPECmark89 as context. SPECint89 is the only SPEC89 target the classical
network and SPEC89 bridge use.

| Source | Systems | SPECint89 / SPECfp89 / SPECmark89 | Basis |
| --- | --- | --- | --- |
| `src:mashey-ymmv-88k-1990`: John Mashey (MIPS), "Re: Fastest 88k", comp.arch `<42586@mips.mips.COM>`, 1990-10-31 | Data General AV/410, 20 MHz | 11.3 / 8.3 / 9.4 | SPEC newsletter, Spring 1990 |
| | Data General AV/6200, 25 MHz | 15.3 / 11.3 / 12.7 | Winter 1990 |
| | Motorola 8864SP, 20 MHz | 14.6 / 10.8 / 12.2 | Winter 1990 |
| | Motorola 8864SP, 25 MHz | 18.3 / 13.5 / 15.2 | Winter 1990 |
| | Motorola 8612, 33 MHz | 21.4 / 15.8 / 17.8 | Winter 1990 |
| | MIPS Magnum (RC3230), 25 MHz | 19.4 / 16.8 / 17.8 | Summer 1990 |
| `src:ragan-cdc4680-spec-1991`: Rich Ragan (Control Data), "Compilers & SPECmarks...", comp.arch `<32097@shamash.cdc.com>`, 1991-04-08 | MIPS RC6280 | 45.8 / 45.6 / 45.7 | Control Data's run, MIPS 2.20 compilers |
| | CDC 4680 | 45.8 / 63.5 / 55.7 | Same hardware, CDC/KAI FORTRAN; submitted to SPEC |
| `src:mashey-rc3360-spec-1991`: John Mashey, "Re: r4000", comp.arch `<46252@mips.mips.COM>`, 1991-02-27 | MIPS RC3360, 33 MHz | 27.1 / 26.2 / 26.5 | Vendor statement |
| `src:torrie-harris-nighthawk-spec-1991`: Evan Torrie, "Re: RISC vs. CISC -- SPECmarks", comp.sys.next `<1991Apr27.004627.27205@neon.Stanford.EDU>`, 1991-04-27 | Harris Night Hawk, 25 MHz 88000 | 20.02 / 15.73 / 17.32 | Unattributed; all three are context |

Mashey's table is an extract from MIPS's *Your Mileage May Vary* issue 2.0.
Its two Motorola MPC rows are Mashey's estimates and are not transcribed; its
"published mips" column is a vendor rating, not a measurement. The DG
AV/6200 and Motorola 8612 SPECmark89 values equal the package's. The Night Hawk
result has no stated source, model number or compiler, and Harris's own
1990-10-31 post ran in-house development compilers, so it is context only.

SPECint89 targets formerly came only from the SPEC89 package; since this
change, the network and SPEC89 bridge take them from any source except the
SPEC89/92 bridge table and reference definitions. The nine SPECint89 rows add
nine SPEC89 timeline records (10.85 to 43.99 speed-VAXen). Four pair with
classical results and become inferred-89 network nodes (122 → 126): CDC 4680
(Whetstone) and MIPS RC3360 (LINPACK) are new SPEC89 systems, and MIPS RC6280 and
RC3230 gain a second node. All four are underpredicted (for example CDC 4680
25.4 vs 44.0 speed-VAXen), so `linear_clock / with_spec89` coefficients rise:
Whetstone native +3.32%, DP +3.13%, LINPACK +1.53%, Dhrystone +0.33–0.38%. The
all-available observed P95 rises 85.1% → 87.9%. The 88k systems have no
classical results and the Night Hawk rows are context, so they do not affect
the fit. Details are in the [network](classic-network-fitting.md#changes-from-the-printed-spec89-means-2026-10-03)
and [timeline](unified-vaxen-timeline.md#printed-spec89-means--2026-10-03) reports.

The CDC 4680's Whetstone results resolve to `sys:cdc4680` and its LINPACK
result to `sys:cyber4680`; the alias is not reviewed, so the LINPACK result
does not pair with the SPECint89 target.

Posts that only repeat package values or lack a printed mean:

- Michael Slater, "Re: 68040 Status - SPEC table with missing line added",
  comp.arch `<39825@cup.portal.com>`, 1991-03-04. Per-benchmark ratios and means
  for eight systems. The HP 425t/425s, 486, SPARCstation 330, RC3240 and RS/6000
  530 means are in the package, and the Motorola 8864SP mean is Mashey's. The
  Intel-published i860 add-in board (16.4) has no classical results and is not
  transcribed.
- Mashey, "Re: 80486 v Sparc [and other good numbers]", comp.arch
  `<42280@mips.mips.COM>`, 1990-10-22. All five systems' means are in the package.
- Alan Lovejoy, "Latest SPECmarks", comp.arch `<7377@pdn.paradyne.com>`,
  1990-02-12, and Frederic Despoix, "DG's use of m88k", comp.sys.m88k
  `<7521@imag.imag.fr>`, 1990-02-20. Per-benchmark ratios from the
  1990-02-07 Microprocessor Report, with SPECmark89 but no integer mean. The
  VAX 6000 Model 410 and 450 rows print identical gcc, espresso, li and eqntott
  ratios (one is evidently copied), so no mean is computed from them.
- Tom Horsley (Harris), "Re: Fastest 88k", comp.sys.m88k, 1990-10-31.
  Per-benchmark ratios for the Night Hawk with unreleased compilers and no
  integer mean.

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
