# SPEC sources and audits

Reviewed: 2026-09-25 to 2026-09-29. This report owns where early SPEC results
were found, the recovered CPU92 rate archive, and the audits of SPEC source
fields, execution resources and CPU95/CPU2000 overlap. The fits that use these
inputs are in [SPEC chains](spec-chains.md); SPEC89 recovery is in
[SPEC89](spec89.md). Collection commands are owned by
[SPEC collection](../docs/spec-collection.md).

## Early SPEC result archives

An original published result, a later compilation and an electronically
available detailed report are distinguished here; their dates are not
interchangeable.

### SPEC Release 1 / CPU89

[SPEC's CPU89 page](https://www.spec.org/cpu89/) states that it has not put the
1989 results online. Reinhold Weicker's 1990 survey, [“An Overview of Common
Benchmarks”](https://users.ece.utexas.edu/~ljohn/teaching/382m-15/reading/weicker.pdf),
identifies *SPEC Newsletter* volume 1, issue 1, Fall 1989, pages 1–15 as the
first published result list. That issue has not been located as a digitized,
inspectable copy.

Kaivalya M. Dixit's [“Overview of the SPEC Benchmarks,” chapter 9](https://jimgray.azurewebsites.net/benchmarkhandbook/chapter9.pdf),
Appendix B, Table B.1, printed page 516 (PDF page 28), is an accessible later
compilation with separate SPECmark89, SPECint89 and SPECfp89 columns but no
per-row test date or submission link. Page check 2026-09-25: Compaq 486/50L
reads SPECmark89 `19.3`, SPECint89 `27.6`, SPECfp89 `15.2`.

Usenet leads (Google Groups):

- Weicker's [1989-10-30 `comp.arch` post](https://groups.google.com/g/comp.arch/c/3dBUrduLfqk)
  explains the suite and says the quarterly newsletter carried per-program
  results, but reproduces none. SPEC's [newsletter index](https://www.spec.org/osg/news/)
  begins with 1994-09.
- John DiMarco's [1994-01 `comp.benchmarks` SPECmark table](https://groups.google.com/g/comp.benchmarks/c/zvnlKLIgUDk/m/ut4VeY_t0lcJ)
  has a SPECmark89 table with dates and source labels that he says are
  unverified. It is a discovery index, and gives no SPECint89/SPECfp89.
- Norbert Juffa's [1993-01-15 `comp.sys.intel` post](https://groups.google.com/g/comp.sys.intel/c/4t50yI9XsQw)
  transcribes Intel literature with SPECmark89, SPECint89 and SPECfp89; its
  AMD/Cyrix row is an estimate and two rows were recomputed by the poster.
- A [1993 `comp.benchmarks` SPEC FAQ](https://groups.google.com/g/comp.benchmarks/c/syb7is_Xpng)
  points to the 1992-12 newsletter summary list (volume 4, issue 4, pages 6–8).

On 2026-09-25 the Internet Archive metadata catalog returned no item for
`"SPEC Newsletter"`, `SPECint89` or `SPECmark89`; a
[full-text search](https://archive.org/search?tab=fulltext&query=%22SPEC+Newsletter%22+%22Fall+1989%22)
returned 23 items citing the first issue but not the issue itself. The
[Wayback listing of SPEC's newsletter directory](https://web.archive.org/web/*/http://www.spec.org/osg/news/*)
shows `news9409/` (1994-09) as its earliest issue. Neither search proves that
no scan exists. The [SPEC89 recovery snapshot](spec89.md#curated-spec89-snapshot)
preserves the Usenet observations recovered later.

### CPU92

[SPEC's CPU92 page](https://www.spec.org/cpu92/) explains that the paper-era
process left no complete official electronic archive. Dixit's Appendix A,
Table A.1, printed page 512 (PDF page 24), has SPECint92 and SPECfp92 columns
from newsletters through December 1992, without per-row issue or test date. Page
check: Compaq Deskpro/66M reads SPECint92 `32.2`, SPECfp92 `16.0`. The
[Computer History Museum finding aid for the Michael Slater collection](https://archive.computerhistory.org/resources/access/text/finding-aids/102733965-Slater/102733965-Slater.pdf)
lists SPEC newsletters dated 1992-03 and 1992-06 (Box 5, catalog item
102773491): a physical holding, not a verified scan.

The [contemporary SPEC FAQ preserved by Netlib](https://www.netlib.org/performance/html/specfaq.html)
defines each CPU92 speed ratio as the reference time, originally measured on a
VAX-11/780, divided by the tested system's time; `SPECint92` is the geometric
mean of six CINT92 ratios. So a `SPECint92` of `58.8` is 58.8 speed-VAXen
without an extra factor; a [US GAO explanation](https://www.gao.gov/products/b-254497.2,b-254497.3)
independently describes `SPECint92 = 40` as 40 times the VAX-11/780. This does
not equate SPECint92 with SPECint89, SPECfp92 or later suites. The FAQ also
states that baseline results became mandatory with the June 1994 newsletter, so
a missing `SPECbase_int92` in a 1992 or 1993 report must not be filled with
SPECint92.

Netlib's [Performance Database Server](https://www.netlib.org/performance/html/spec.html)
has issue summaries and full disclosures from June 1993 (volume 5, issue 2):
44 speed summary pages and 537 distinct detailed reports, all cached on
2026-09-25. It is selected coverage, not proof that 1992 results did not exist.
A transcription check compared the June 1993 [CINT92 summary](https://www.netlib.org/performance/html/spec.cint92.6_93.col0.html)
with the [IBM POWERserver 970B report](https://www.netlib.org/performance/html/spec.990b.cint92.6_93.notes.html):
both state `SPECint92 = 58.8`. Two 1993-06 labeled disclosures (this one and
[IBM 990](https://www.netlib.org/performance/html/spec.ibmi990.cint92.6_93.notes.html))
claim testing in 1993-09; both stay score observations, flagged
`test_after_issue_month`.

## SPEC CPU92 integer-rate archive

Netlib's [SPEC directory](https://www.netlib.org/performance/html/spec.html)
links `crint92` issue summaries outside the ordinary CINT92 list. The [combined
integer-rate summary](https://www.netlib.org/performance/html/new.spec.crint92.col0.html)
links 273 details; the issue summaries link **274**: the
[HP 9000 Model R500 report](https://www.netlib.org/performance/html/spec.hpr50012.crint.12_93.notes.html)
is in the [1993-12 issue summary](https://www.netlib.org/performance/html/spec.crint92.12_93.col0.html)
but not the combined list, a source-index discrepancy rather than a reason to
discard it.

`spec legacy92-rate`, `legacy92-rate-fetch` and `legacy92-rate-parse` cached all
22 issue summaries and 274 details with URL, retrieval date and SHA-256, and
export 274 result records plus 1,644 per-benchmark rows with copy counts and
timings to `data/derived/spec/cpu92-rate/`. All parsed without exclusions; 199
report a base rate; two HP details omit hardware availability, left blank. The
earliest test month is 1993-03, so these pages do not fill the 1992 gap.
[SPEC's CPU92 rate description](https://www.spec.org/cpu92/specrate.txt)
confirms `SPECrate_int92` is a throughput metric with concurrent copies.

### 1992 Digital performance brief

Digital's *Alpha AXP Server Family Performance Brief - OpenVMS*, second edition,
**EB-N0104-51**, dated **1992-11-20**, Table 1 on page 3, reports five
`SPECint92` scores (65.3, 74.3, 83.5, 96.6, 106.5) and nine `SPECrate_int92`
system/CPU-count scores, without per-benchmark copy counts. The 14 observations
are in the [source-linked CSV](data/spec/cpu92-dec-alpha-openvms-1992.csv); the
[archived PDF](https://web-docs.gsi.de/~kraemer/COLLECTION/DEC/alpha-axp-server.pdf)
is cached under `data/raw/spec/cpu92/dec/`. The [1992-11-20 workstation brief](https://web-docs.gsi.de/~kraemer/COLLECTION/ftp.cuhk.edu.hk/pub/doc/digital/alpha-axp-openvms-workstation.pdf)
repeats 65.3 and 74.3 for DEC 3000 Model 400/500; treat that as a possibly
reused measurement. Values are **manufacturer reported**, SPEC publication
unverified, with no submission ID or test date; the report date is not
substituted for either. Competitor scores were not transcribed because Digital
says they were copied unverified from other publications.

### Remaining early-source gap

A [Computer History Museum scan](https://archive.computerhistory.org/resources/access/text/2024/09/102749924-05-0002-acc.pdf)
contains the cover and contents of the **1992-03 SPEC Newsletter** (CINT92 result
pages from printed page 16) but not those pages. Full scans of the Fall 1989
issue and the 1992 result pages remain the highest-value acquisition targets.
Other leads: HP's [1992-11 *Computer Update*](https://www.hpmuseum.net/pdf/HPComputerUpdate_1992_11_37pages_Nov92_OCR.pdf)
for Series 700i, the [HP 9000/735 technical paper](https://bitsavers.org/pdf/hp/pa-risc/HP_9000_735_Second-Generation_PA-RISC_Snakes_Workstation.pdf)
citing a 1992 brief, and the [1992-07 *SunExpert* lineup](https://files.serialport.org/media/SunExpert/SunExpert-v03n07-1992-07.pdf).
None is promoted to an individual SPEC submission; secondary tables keep their
weaker source class and must be deduplicated against original reports.

## Source fields and execution resources

`spec audit-fields` inventories all **105,973 bulk rows** and columns across
CPU95–2026, plus the SPEC89 tables, the DEC SPEC92 table and the Netlib CPU92
adapters. Detailed extraction targets integer speed and rate; floating-point
columns are inventoried only. Tracked outputs are in
[`data/spec/field-audit/`](data/spec/field-audit/) (field inventory and
consumers, generation coverage, resource flags, bulk/detail crosschecks,
execution coverage, Netlib speed coverage, sample manifest,
verified findings and audit hashes); full per-benchmark resources are generated
in `data/derived/spec/field-audit/disclosures.jsonl`.

### Full disclosure refresh

All **54,014 indexed integer speed/rate results** across CPU95–CPU2026 have
cached detail files (2026-09-29), plus one positive bulk result absent from the
integer index, [CPU2017-20170828-00068](https://www.spec.org/cpu2017/results/res2017q3/cpu2017-20170828-00068.html)
(88 copies in both modes). The audit examined **54,015 disclosures** and made
**164,062 hardware crosschecks with zero contradictions**; there are 261
resource review flags. Records: [acquisition](data/resource-refresh/acquisition-summary.json),
[per-generation counts](data/resource-refresh/generation-summary.csv),
[audit totals](data/resource-refresh/resource-audit-summary.json) and
[runtime coverage](data/resource-refresh/positive-score-runtime-coverage.csv).

Coverage of the **98,072 positive modern score observations** (base and peak
counted separately):

| Track / declaration status | Observations |
| --- | ---: |
| Integer rate: reported copies | 58,340 |
| Integer speed: reported threads | 17,757 |
| Integer speed: earlier tables without explicit thread counts | 21,971 |
| Integer speed: unparsed non-integer thread declarations | 4 |
| Missing disclosure for a positive modern score | 0 |

The four unparsed observations are two HPE submissions whose tables and runcpu
commands literally report `64i` and `88i`; they stay
[source strings](data/resource-refresh/unparsed-thread-values.csv), not 64/88
threads. The parser distinguishes unparsed declarations from absent fields.

### Resource quantities stay separate

| Quantity | Meaning / current use |
| --- | --- |
| Enabled chips | Hardware enabled for the run; matching guard |
| Enabled cores | Enabled resources, possibly below installed capacity; matching guard when known |
| Cores/chip | Chip capacity; cannot be multiplied into an assumed enabled-core count |
| Hardware threads/core | Hardware/SMT configuration; not benchmark worker count |
| Rate copies | Concurrent benchmark processes; retain benchmark and base/peak separately |
| Speed benchmark threads | For CPU2017, allowed OpenMP threads; not measured active cores or OS thread count |
| CPUs orderable | Product sales options, not tested processor count |
| CPU92 Number of CPUs | Legacy count used in the matcher's chips slot; chip equivalence unverified |

The [CPU2017 glossary](https://www.spec.org/cpu2017/Docs/result-fields.html#Copies)
defines copies and threads separately. CPU95/2000/2006 speed details lack a
structured benchmark-threads column; absence does not justify imputing one
thread. Recovered SPEC89 scores generally lack runtime disclosures.

### Checked findings

1. **Low enabled counts can be deliberate.**
   [Bull POWER5+ CPU2006](https://www.spec.org/cpu2006/results/res2007q1/cpu2006-20070215-00481.html)
   reports one core of a two-core chip; its notes describe removing 15 cores and
   disabling SMT. 256 positive-score bulk records have enabled cores below chips
   × cores/chip; only sampled cases are explained.
2. **Internal topology inconsistency.**
   [HP ProLiant ML150 G3 / Xeon 5050](https://www.spec.org/cpu2000/results/res2006q3/cpu2000-20060901-07172.html)
   says four cores, one chip, two cores/chip with Hyper-Threading, and four
   copies; possibly logical threads read as cores. Numbers are preserved and the
   topology flagged.
3. **Zero counts belong to redacted non-compliant sources.** CPU2017
   20200119-20586 (rate) and 20200119-20589 (speed) report zero cores and lack a
   positive aggregate ([rate report](https://www.spec.org/cpu2017/results/res2020q1/cpu2017-20200119-20586.html)).
4. **Speed threads can vary within a submission.**
   [CPU2026 20260810-00424](https://www.spec.org/cpu2026/results/res2026q3/cpu2026-20260810-00424.html)
   reports base threads 384 and peak threads from 1 to 384 on 192 cores with SMT.
5. **Hardware admission does not establish equal concurrency.** A base
   CPU2006→CPU2017 tuple paired
   [CPU2006 20070331-00717](https://www.spec.org/cpu2006/results/res2007q2/cpu2006-20070331-00717.html)
   (8 copies) with [CPU2017 20161026-00003](https://www.spec.org/cpu2017/results/res2017q2/cpu2017-20161026-00003.html)
   (1 copy). This finding introduced the fitters' rule that drops a mode with a
   confirmed conflict between two reported constant counts.

### Information not controlled by the fits

| Dimension | Current use / gap |
| --- | --- |
| Cache size, sharing, external cache | Preserved raw and shown as context; not a pairing guard |
| Memory capacity | Hardware-near pairing requires equal parsed capacity |
| Channels, DIMM population/ranks/speed, NUMA | Raw memory/notes; not modeled |
| Nominal versus max/turbo frequency | Nominal or text fallback; no frequency score scaling |
| Disabled cores, partitions, affinity, SMT | Partial bulk fields; notes require review |
| Compiler, flags, PGO, libraries, pointer size | Retained in pair provenance; no equality guard |
| OS, firmware, huge pages, power settings | Same-OS constraint only in the CPU92/95 rate sensitivity tier |
| Benchmark copies / threads | Extracted; only confirmed constant-count conflicts exclude a mode |

Bootstrap CI95 does not cover these systematic differences. A complete runtime
audit would compare per-benchmark vectors on matched pairs under explicitly
defined policies; points are not discarded by residual size and copies are not
filled from cores or SMT.

## CPU95/CPU2000 overlap audit

Reviewed 2026-09-29. The cached CPU95 bulk has 2,574 result IDs and CPU2000
7,654; both agree exactly with the quarterly-index manifest
([index coverage](data/spec/95-2000-audit/index-coverage.json)). Usable
populations are 773 CPU95 integer-rate, 1,374 CPU2000 integer-speed and 2,481
CPU2000 integer-rate submissions; 7 speed and 12 rate CPU2000 rows have no
positive aggregate ([exclusions](data/spec/95-2000-audit/collection-exclusions.csv)).

The audit asked why a three-way overlap (CPU95 rate, CPU2000 speed, CPU2000
rate) was small. Counts per mode under alternative admission rules (machine
readable: [ablation](data/spec/95-2000-audit/ablation.csv),
[blockers](data/spec/95-2000-audit/blockers.csv),
[alias candidates](data/spec/95-2000-audit/alias-candidates.csv),
[system coverage](data/spec/95-2000-audit/system-coverage.csv)):

| Admission rule | Triples | CPU95 system names | CPU models | CPU/chips/clock configurations |
| --- | ---: | ---: | ---: | ---: |
| Strict name matching | 2 | 1 | 1 | 1 |
| Allow different RAM only | 5 | 4 | 2 | 3 |
| Candidate aliases only; equal RAM | 4 | 3 | 1 | 2 |
| Different RAM + candidate aliases | **10** | **9** | **3** | **5** |
| Ignore platform identity and RAM (diagnostic only) | 72 | 14 | 3 | 5 |

The recovered CPUs are 21264, 21264A and UltraSPARC II: two architecture
families and five configurations. Findings:

1. **RAM differences are real.** AlphaServer DS10 6/600 (2 GB / 1 GB / 1 GB),
   ES40 6/667 (4 / 4 / 16 GB) and Sun Enterprise 3500/4500 400 MHz (2 / 8 / 8 GB)
   otherwise match on model, CPU, clock and count.
2. **Names hide available results.** `AlphaServer GS160 6/731` versus
   `AlphaServer GS160 Model 6/731` (the [CPU95 rate](https://www.spec.org/cpu95/results/res2000q2/cpu95-20000605-04245.html)
   and [CPU2000 speed](https://www.spec.org/cpu2000/results/res2000q2/cpu2000-20000511-00103.html)
   disclosures agree on CPU, 731 MHz, one CPU and 4 GB), GS320, DS20, ES40 and
   XP1000 branding. DS20 versus DS20E stays distinct.
3. **Speed and rate often enable different CPU counts.** HP N4000 at 552 MHz has
   one-CPU [speed](https://www.spec.org/cpu2000/results/res2000q1/cpu2000-20000313-00044.html)
   and two-CPU [rate](https://www.spec.org/cpu2000/results/res2000q1/cpu2000-20000313-00045.html)
   results. A `2X` in a model name does not override the disclosed count; no
   rate is synthesized from speed.
4. **SGI 2200 2X 400 MHz has a withdrawn result.** Its
   [CPU2000 result](https://www.spec.org/cpu2000/results/res1999q4/cpu2000-19991130-00023.html)
   marks both integer aggregates NC (three-month availability rule); the bulk
   encodes them as zero, which is not measured performance. The later positive
   [speed](https://www.spec.org/cpu2000/results/res2000q2/cpu2000-20000509-00095.html)
   and [rate](https://www.spec.org/cpu2000/results/res2000q2/cpu2000-20000509-00097.html)
   results enable one and two chips.
5. **Clock and CPU wording must be preserved.** Sun Enterprise 450 candidates
   differ (400 vs 480 MHz); IBM 44P-270 says Power3 versus Power3-II.

Forty original disclosures were checked: 39 agree with the bulk on model, CPU,
clock, chip count and memory; the other is the SGI NC record
([checks](data/spec/95-2000-audit/disclosure-checks.csv)). Reproduce with
`bridge audit-95-2000 [--fetch-review]` and `spec verify --generation cpu95
--generation cpu2000`. The rate chain now pairs over resolved identity (which
absorbs the naming differences above) and still requires equal RAM.
