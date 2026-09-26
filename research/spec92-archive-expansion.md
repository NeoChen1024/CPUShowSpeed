# SPEC CPU92 integer-rate archive expansion

Reviewed on 2026-09-26. This search found a separately published Netlib
**integer-rate** archive and a contemporary Digital Equipment Corporation
performance brief with 1992 CPU92 rate values. The two sources differ in
provenance; neither makes the Netlib rate series a complete census.

## Netlib CINT92 rate disclosures

Netlib's [SPEC directory](https://www.netlib.org/performance/html/spec.html)
links `crint92` issue summaries outside the ordinary CINT92 result list. The [combined integer-rate summary](https://www.netlib.org/performance/html/new.spec.crint92.col0.html)
links 273 distinct details. The issue summaries link **274**: the
[HP 9000 Model R500 report](https://www.netlib.org/performance/html/spec.hpr50012.crint.12_93.notes.html)
is present in the [1993-12 issue summary](https://www.netlib.org/performance/html/spec.crint92.12_93.col0.html)
but absent from the combined list. This is a source-index discrepancy, not a
reason to discard the issue-linked result.

The commands below cached all 22 issue summary pages and all 274 unique
integer-rate details, preserving source URL, retrieval date, and SHA-256. The
parser checks every composite rate score against its separate issue summary
and exports [274 result records](../data/derived/spec/cpu92-rate/cpu92-rate-records.csv)
plus [1,644 per-benchmark rows](../data/derived/spec/cpu92-rate/cpu92-rate-benchmarks.csv)
with copy counts and timings. All 274 details parsed without exclusions; 199
report a base rate score. Two HP details omit hardware availability, which is
left blank rather than inferred. The earliest reported **test month** is
1993-03; these pages still do not fill the 1992 original-result gap. This
archive is the earliest currently parsed **official rate** cohort.

```console
./.venv/bin/cpushowspeed spec legacy92-rate
./.venv/bin/cpushowspeed spec legacy92-rate-fetch
./.venv/bin/cpushowspeed spec legacy92-rate-parse
```

[SPEC's CPU92 rate description](https://www.spec.org/cpu92/specrate.txt)
confirms that `SPECrate_int92` is a throughput metric with concurrent copies.
The recovered rate disclosures feed the [direct CPU92→CPU95 rate-to-rate
fit](spec95-spec2026-rate-fitting.md).

## Contemporary 1992 Digital performance brief

Digital's *Alpha AXP Server Family Performance Brief - OpenVMS*, second
edition, document **EB-N0104-51**, dated **1992-11-20**, Table 1 on printed
page 3 / PDF page 3, reports five `SPECint92` scores (65.3, 74.3, 83.5,
96.6, 106.5) for its named Alpha server configurations. It reports nine
numeric `SPECrate_int92` system/CPU-count scores. The brief labels how many
CPUs were configured, but not the per-benchmark concurrent copy counts. These 14 observations are in
the [source-linked CSV](data/spec/cpu92-dec-alpha-openvms-1992.csv). The
[archived PDF](https://web-docs.gsi.de/~kraemer/COLLECTION/DEC/alpha-axp-server.pdf)
was cached with its original bytes and SHA-256 under `data/raw/spec/cpu92/dec/`.
The separate [1992-11-20 workstation brief](https://web-docs.gsi.de/~kraemer/COLLECTION/ftp.cuhk.edu.hk/pub/doc/digital/alpha-axp-openvms-workstation.pdf)
repeats the 65.3 and 74.3 values for DEC 3000 Model 400/500 workstation
variants. Treat the repetition as a possible reused measurement, not two new
independent submissions.

Digital calls these its latest measured results, but the brief does not give
an individual SPEC submission ID or test date. Its values are **manufacturer
reported**, with SPEC publication/compliance unverified. The report date is
not substituted for either test date or hardware introduction. The five reported speed values are retained in the source transcription but
are not used by the active rate analysis. Competitor
scores in the brief were not transcribed because Digital says those figures
were taken from other publications and not independently verified.

## Remaining early-source gap

A [Computer History Museum scan](https://archive.computerhistory.org/resources/access/text/2024/09/102749924-05-0002-acc.pdf)
contains the front page of the **1992-03 SPEC Newsletter**, whose contents
list CINT92 result pages beginning at printed page 16. The scanned packet
moves to other documents after that cover; it does **not** provide those
result pages. The [Michael Slater collection finding aid](https://archive.computerhistory.org/resources/access/text/finding-aids/102733965-Slater/102733965-Slater.pdf)
identifies physical SPEC newsletters dated 1992-03 and 1992-06. A
[contemporary SPEC FAQ transcription](https://groups.google.com/g/comp.benchmarks/c/syb7is_Xpng)
says the 1992-12 issue contained a summary of all CINT92/CFP92 results to
that point, with issue pointers. Full scans or independently inspectable
report pages for those early issues remain the highest-value acquisition
target. Other leads include HP's [1992-11 *Computer Update*](https://www.hpmuseum.net/pdf/HPComputerUpdate_1992_11_37pages_Nov92_OCR.pdf)
claim for its Series 700i systems, the [HP 9000/735 technical paper](https://bitsavers.org/pdf/hp/pa-risc/HP_9000_735_Second-Generation_PA-RISC_Snakes_Workstation.pdf)
that cites a 1992 performance brief, and the [1992-07 *SunExpert* model
lineup](https://files.serialport.org/media/SunExpert/SunExpert-v03n07-1992-07.pdf)
that attributes scores to Sun. These have not been promoted to individual
SPEC submissions; their score provenance, configurations, and possible
republication still need page-level review. Later Usenet tables and vendor
scoreboards can generate leads, but must retain their weaker source class and
be deduplicated against original reports before entering annual submission
counts.
