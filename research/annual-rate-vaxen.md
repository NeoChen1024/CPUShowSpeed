# Annual SPEC integer-rate VAXen view

Generated and reviewed on 2026-09-26 with
`./.venv/bin/cpushowspeed plot annual-rate`. The [leader CSV](data/spec/annual-rate-leaders.csv)
and [annual statistics CSV](data/spec/annual-rate-statistics.csv) are the small,
script-readable research results. The complete [per-submission records](../data/derived/figures/annual-rate/annual-rate-records.csv),
[undated records](../data/derived/figures/annual-rate/annual-rate-undated.csv),
and [input-hash summary](../data/derived/figures/annual-rate/annual-rate-summary.json)
are generated locally outside Git. Each plotted point retains its original
score, benchmark generation, full system and CPU names, reported hardware
month, result URL, and source container SHA-256.

The [base distribution](../data/derived/figures/annual-rate/annual-rate-distribution-base.png)
and [peak distribution](../data/derived/figures/annual-rate/annual-rate-distribution-peak.png)
show one box per year with the year's highest submission overlaid. The
[base representatives](../data/derived/figures/annual-rate/annual-rate-leaders-base.png)
and [peak representatives](../data/derived/figures/annual-rate/annual-rate-leaders-peak.png)
show the system and CPU separately. Zoomable SVG files and full-name,
source-linked [base HTML](../data/derived/figures/annual-rate/annual-rate-leaders-base.html)
and [peak HTML](../data/derived/figures/annual-rate/annual-rate-leaders-peak.html)
are beside the PNGs.

## Combined distribution, hardware and confidence figures

Run the chain bootstrap first, then `./.venv/bin/cpushowspeed plot annual-rate-ci`.
The [combined base figure](../data/derived/figures/annual-rate/annual-rate-combined-base.png)
and [combined peak figure](../data/derived/figures/annual-rate/annual-rate-combined-peak.png)
place each year's representative System/CPU, submission count and horizontal
boxplot on the same row. Their [base HTML](../data/derived/figures/annual-rate/annual-rate-combined-base.html)
and [peak HTML](../data/derived/figures/annual-rate/annual-rate-combined-peak.html)
include SVG and complete names, clickable sources and interval tables.
The [annual confidence CSV](data/spec/annual-rate-confidence.csv) records all
72 year/mode results at full precision, including quartile, fixed-leader and
annual-frontier intervals and the original central values.

Each of the 10,000 bootstrap replicates supplies one shared multiplier per
SPEC generation. Every source submission in a year receives that generation's
same multiplier; Q1, median, Q3 and maximum are recomputed from the complete
resulting vector. Computation is batched in 128 replicates to bound memory.
The source population is fixed, including repeated submissions; only calibration
uncertainty is resampled. Raw score and date fields are unchanged.

The solid box is the central Q1–Q3 range, with a median line, standard 1.5-IQR
whiskers and faint outlier points. Pale blue spans **Q1's lower 95% limit to
Q3's upper 95% limit**. It is an envelope of two pointwise quartile intervals,
not a 95% interval for all observations. Blue strokes below each box show the
separate Q1, median and Q3 intervals. The orange point is the central highest
submission; its pale orange band is the fixed representative's conditional
95% calibration interval. This keeps the band tied to the System/CPU at left.
All intervals are percentile intervals from the saved chain draws, with the
scope and edge-independence assumptions in the [chain audit](spec95-spec2026-rate-fitting.md#conditional-whole-chain-confidence-intervals).

The CSV/HTML also supplies a **frontier interval** that allows the highest
submission to change across replicates. Top retention counts a tied highest
score as remaining at the top. The central **2018 base** representative stays
at the top in **65.81%** of replicates; its plot label therefore notes the
retention rate. All other year/mode representatives remain co-highest in
100% of these draws. That describes calibration sensitivity under this model,
not certainty that those machines were historically the fastest.

## Population and year definition

The population is **every parsed SPEC integer-rate submission with a positive
score in that mode and a parseable reported `HW Avail` month**. CPU92 comes
from the 274 hash-checked Netlib rate disclosures; later generations come
from the five hash-checked official bulk exports. Base has **32,025** dated
submission scores and peak has **26,784**. Two CPU92 results lack hardware
availability, yielding four mode-specific undated scores; they remain in the
source export and are absent from annual groups. A missing or nonpositive
base/peak score is not replaced with the other mode. Repeated submissions,
large configurations and submissions naming clusters are retained. No result
is removed because its reported date disagrees with an external product
launch date.

The year is the disclosure's **availability of the tested hardware
configuration**, preserved at month precision in the per-record CSV. It is
not necessarily the introduction year of its named CPU or system. A benchmark
published years later can enter an earlier hardware-year group; the chart
therefore describes published submissions *grouped by reported hardware
availability*, not performance measured during each year. Source dates may
contain errors and have not all been independently audited.

For each year and mode, the **representative** is the submission with the
highest normalized VAXen value; ties choose the lexicographically first
source URL while the CSV records the tie count. This is a performance
frontier among the available submissions, not the median or a typical
machine. The yearly box and count panel show the wider source population.
There are **36** annual leaders in each mode from **1991–2026**. The 1991
base and peak groups each have only one submission, so their "leader" has
no within-year competition. Coverage varies strongly across later years.

## Units and fitting choice

The [rate fitting audit](spec95-spec2026-rate-fitting.md) defines the VAX
throughput reference and the cross-generation chain. This figure multiplies
each original rate score by the appropriate generation's **same-OS CPU92
anchor + strict later-edge** factor, separately for base and peak. It also
stores the hardware-near CPU92 anchor result as `alternate_vaxen` in the
leader CSV and `vaxen_hardware_near` in the complete record CSV. The two
scenarios are sensitivity choices, **not** a confidence interval. The
CPU92 value uses its published VAX rate formula directly; later suites use
exploratory fitted conversions. `VAXen` labels here always mean
**integer-rate throughput** relative to the CPU92 VAX reference.

| Hardware year | Base highest VAXen | Peak highest VAXen | Source pattern |
| --- | ---: | ---: | --- |
| 1992 | 766 | 809 | DEC 7000 Model 660, CPU92 rate |
| 2000 | 137k | 175k | SGI Origin 3800, CPU2000 rate |
| 2010 | 11.9M | 7.61M | Different base/peak leader submissions |
| 2019 | 39.2M | 14.4M | Different CPU2017 rate submissions |
| 2026 | 65.2M | 77.2M | HPE Compute Scale-up Server 3250, CPU2017 rate |

Rounded values are display examples; use the full-precision CSV for
calculation. Base and peak yearly maxima can come from different submissions,
so a smaller peak maximum in a year does not mean one machine's peak score is
below its own base score. The 2026 highest result is a CPU2017 submission on
hardware reported available in 2026; the currently smaller CPU2026 suite
submission cohort does not force the latest year to use the latest suite.

## Independent disclosure checks

The [1991-year HP 9000 720/50 CPU95 rate disclosure](https://www.spec.org/cpu95/results/res96q1/cpu95-960131-00125.html)
reports base and peak **14.1**, hardware availability **1991-03**, and a
**1996-01** test. That independently checks the earliest leader's metric and
shows why its plot year is not its measurement year. The [2026-year HPE
Compute Scale-up Server 3250 CPU2017 rate disclosure](https://www.spec.org/cpu2017/results/res2026q2/cpu2017-20260323-51229.html)
reports base **11,800**, peak **12,200**, hardware availability **2026-04**,
16 chips / 1,376 enabled cores, and 2,752 copies in its rate table. These
checks confirm two selected leaders against detailed disclosures; the other
leader rows presently rely on the hash-checked bulk exports or Netlib reports
and still merit per-result review.

## Interpretation limits

No manual or model-specific date correction enters the population. A known
EPYC 7313 result, for example, reports `HW Avail = Aug-2019` even though
[AMD lists that CPU's launch as 2021-03-15](https://www.amd.com/en/products/processors/server/epyc/7003-series/amd-epyc-7313.html).
Its source score and reported year remain included. This illustrates why the
horizontal axis must say **reported configuration availability**. Any future
date-quality filter must be defined and audited systematically across the
whole population before producing a separate sensitivity figure.

The boxes contain submissions rather than independent machine models;
multiple results for one platform may affect their distribution. The VAXen
chain has architecture and software dependence. The [conditional whole-chain
bootstrap](spec95-spec2026-rate-fitting.md#conditional-whole-chain-confidence-intervals)
estimates sampling variation of the calibration scale. The combined figures
propagate those draws into pointwise annual intervals; they do not include
individual-machine prediction error or systematic calibration bias. In particular, the sparse first year and changing suite coverage
make the leader curve unsuitable as a claim of uninterrupted annual hardware
progress. Review individual leader disclosures, copy counts and unusual
configuration dates before using the chart as a public historical index.
