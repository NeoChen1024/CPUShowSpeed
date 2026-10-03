# Usenet result lists

Reviewed: 2026-10-03. Status: Rick Richardson's Dhrystone lists are parsed from
the stored postings by
[`usenet_results.py`](../python-src/cpushowspeed/usenet_results.py) and used by the
classical network. All posts here come from the UTZOO archive
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
