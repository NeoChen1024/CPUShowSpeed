# SPEC89 recovery and bridge

Reviewed: 2026-09-26 to 2026-10-03. This report owns the recovered SPEC89
evidence, the one-edge `SPECint89 → SPECint92` bridge to speed-VAXen, the joint
classical experiment that uses it and the SPEC89-only hardware estimates
(method `spec89-one-edge-speed-joint-v4-power-law-vax780`). Where SPEC89 results
were searched for is in [SPEC sources](spec-sources.md#spec-release-1--cpu89).

## Curated SPEC89 snapshot

The [versioned dataset](data/spec89/v2.0.0/README.md) is a curated copy of the
user-provided consolidated research package. Its checksum manifest passed, and
`cpushowspeed spec89 verify` reconstructs all 25 CSV tables and `summary.json`
byte-for-byte and rechecks the 37 saved message hashes (2026-09-26). The
package records a re-extraction from MBOX ZIPs that are not included here, so
that one check was not rerun. Internal consistency does not authenticate every
score against its original publication.

The [aggregate table](data/spec89/v2.0.0/csv/aggregate89.csv) has 381 source
observations, 142 with `SPECint89`. It includes reference definitions,
development and beta systems, a quarantined possible CPU-time approximation and
repeated reports; these categories stay visible.

### Helman 1991 worksheet supplement

James Helman's Usenet post `<JIM.91Mar30161055@baroque.Stanford.EDU>` prints 40
SPEC89 rows for 34 system labels, derived from McCalpin's `spec.sc` worksheet
with added clocks and recent HP results. The preserved
[message](data/spec89/helman-1991/source.txt) and
[row-level CSV](data/spec89/helman-1991/observations.csv) agree line by line;
the message matched the supplied `comp.benchmarks.mbox.zip` at its offsets and
SHA-256 ([supplement directory](data/spec89/helman-1991/README.md)).

The [combined CSV](data/spec89/aggregate89-plus-helman.csv) keeps all 381
original observations and appends these as `R3H0001`–`R3H0040`
(`measurement_type=published_worksheet_derivative`), **421 observations** in
total, with no deduplication or score replacement. The post warns that
redundancies remain and clocks may be wrong: 25 rows cite note 7 (calculated
from Mashey's *Your Mileage May Vary*), four mark the clock uncertain, one is an
estimate and one a beta. Per-MHz values are worksheet calculations. The post
date `1991-03-31` is a publication date, not a test or launch date.

```sh
./.venv/bin/cpushowspeed spec89 merge-helman [--mbox-zip /path/to/comp.benchmarks.mbox.zip]
```

The original `spec.sc`, `spec.print` and Aburto `bench.tar.gz` were not in the
package; this is the 40-row derivative table, not their recovery.

### Hardware years

Hardware introduction years for the SPEC89 systems are curated `date_event`
rows (see [identity and dates](identity-and-dates.md#date-events)): 26 of the
160 normalized labels had a source-checked year when first reviewed, with
introduction, announcement, general availability and manufacturer model year
kept distinct. Sources include DIGITAL's [historical timeline](https://archive.computerhistory.org/resources/text/DEC/dec.digital_%28DEC%29_timeline_1957-1997.102630354/timelinetext.htm)
(VAX-11/780 introduction 1977-10, not first delivery; DECstation 3100 1989-01;
DEC 3000 Model 400/500 1992-11), IBM's [POWER1 history](https://www.redbooks.ibm.com/redbooks/pdfs/sg247071.pdf)
(Model 220 1992-01, 580 1993-09) and lifecycle pages
([340](https://www.ibm.com/support/pages/node/7093897),
[560](https://www.ibm.com/support/pages/node/7094379): 1992-01-21), Sun's
[Numerical Computation Guide, Table B-1](https://docs.oracle.com/cd/E19957-01/802-5692/802-5692.pdf)
(year-level model years), a 1990 [NeXT advertisement](https://archive.computerhistory.org/resources/access/text/2024/05/102734476-05-0012-acc.pdf),
Intel's [processor chronology](https://www.intel.com/pressroom/kits/quickrefyr.htm)
(processor dates only) and HP's [1989 *Measure* index](https://www.hp.com/hpinfo/abouthp/histnfacts/publications/measure/index.html).
The RS/6000 530 stays undated: the checked Redbook passage does not date it.

## Evidence path

Historical routes are anchored to **speed-VAXen**, the single-job quantity of
the [integer-speed chain](spec-chains.md#speed-chain): VAX-11/780 is the SPEC92
reference machine, so one SPECint92 point is one speed-VAXen. SPECint89 needs one
empirical edge:

`SPECint89 → SPECint92 (= speed-VAXen)`.

The [bridge table](data/spec89/v2.0.0/csv/bridges89_92.csv) has 34 cited
same-source rows. Seventeen give both `SPECint89` and `SPECint92`; the other
seventeen give `SPECmark89`, which is a separate composite and is never treated
as `SPECint89`. The 17 integer rows are 15 resolved systems (two IBM vectors are
republished); nine are development-level. Their reported `SPECint92 /
SPECint89` ratios range 0.893–1.056. The IBM 220 values `SPECint89 = 17.5`,
`SPECint92 = 15.9` were checked against the
[saved 1992-05-22 Usenet message](data/spec89/v2.0.0/sources/ibm_89_92_bridge_1992-05-22.txt),
lines 34–42; the [*Microprocessor Report* comparison](https://www.cecs.uci.edu/~papers/mpr/MPR/ARTICLES/061203.pdf),
PDF page 3, Table 1, discusses why the two suites' ratings differ. Outside the
table, six resolved systems (DECstation 5000/20, /25, /125, /133, /240 and HP
9000/720) have both scores; they are recorded in the audit, not used.

| Edge | Role | Systems / source rows | Multiplier | Factor CI95 | LOMO model-center P95 |
| --- | --- | ---: | ---: | --- | ---: |
| SPECint89 → SPECint92 | speed bridge | 15 / 17 | **0.9603866** | 0.943053–0.979110 (joint) | 8.61% |
| SPECint92 → rate-VAXen | diagnostic, not chained | 24 / 48 | 0.9965475 | 0.992201–1.000572 | 1.86% |

Thus `estimated speed-VAXen = 0.9603866 × SPECint89`, proportional because both
sides are SPEC integer suites on the same reference machine. The interval is
fitted-factor uncertainty, not a prediction interval for an individual old
machine; transport to earlier architectures is an assumption. There is no
base-variant bridge, so the route is peak-only.

The second row uses the [reviewed DEC N3909 columns](historical-sources.md#three-source-pdf-extraction)
reporting both SPECint92 and SPECrate_int92 on one-processor systems. Its factor
near 1 shows that the two quantities nearly agree there; by the 2026-10-03
decision rate is never chained into a speed estimate.

Name joins between the bridge rows and the Netlib CPU92 reports found no exact
matches: names change, and Netlib begins in 1993 while many bridge rows cite
1992 material. Row `B012` cites the
[DEC Alpha server brief](https://web-docs.gsi.de/~kraemer/COLLECTION/DEC/alpha-axp-server.pdf)
for a DEC 7000/610 with a 182 MHz 21064, while Netlib's
[DEC 7000 Model 610 disclosure](https://www.netlib.org/performance/html/spec.deoi761.cint92.12_93.notes.html)
reports 200 MHz: a shared family is not the same tested setup.

## Joint model experiment

The joint model adds the SPECint89 classical pairs after translating their
targets through the bridge, beside directly observed SPECint92 targets. It uses
the `same_system` cohort (resolved system, no clock scaling), fixed equal-weight
geometric composites and the power law through the VAX-11/780 of the
[direct composites](classical-fits.md#direct-composites):
`log(target) = b × (log C − log C₇₈₀)`, where a SPEC89 target is
`SPECint89 × bridge`. A result that reports SPECint92 is used through that value,
not also through its SPECint89 estimate. No residual threshold removes a source.

For each pattern, `spec92_only`, `89_only` and `joint` cohorts are compared with
all single-component baselines on identical tuples and folds. Every derived row
labels its target `observed_speed_target` or `estimated_89_target`.

CI95 uses 10,000 draws (seed 20260926) that jointly resample resolved systems
from the union of the bridge edge and the classical cohort; a system in both
receives one weight. Each draw refits the bridge and the exponent, redraws the
780's log anchors and applies one shared bridge multiplier to every SPEC89
target, so repeated converted observations do not shrink the common
uncertainty. Leave-one-model-out removes the test system from both the bridge
and the classical fit; errors against observed SPECint92 are reported
separately from agreement with converted SPEC89 targets.

### Coverage and observed-target holdouts

Equal-weight composites, `same_system`. P95 is the leave-one-system-out
model-center error on observed SPECint92 targets; the last column is agreement
with the converted SPEC89 targets.

| Composite | SPEC92-only → joint systems | SPEC92-only b / P95 | Joint b | Joint P95, observed | Joint P95, SPEC89 |
| --- | ---: | --- | ---: | ---: | ---: |
| Dhrystone 1.1 + LINPACK | 42 → 61 | 0.8506 / 34.61% | 0.8483 | 33.10% | 70.26% |
| Dhrystone 2.1 + LINPACK | 43 → 56 | 0.8484 / 31.63% | 0.8472 | 30.71% | 76.17% |
| Whetstone native + LINPACK | 9 → 12 | 0.8823 / 26.46% | 0.8843 | 27.40% | 47.67% |
| Whetstone DP + LINPACK | 35 → 52 | 0.8610 / 20.95% | 0.8685 | 22.19% | 45.68% |
| Whetstone SP + LINPACK | 33 → 49 | 0.8483 / 22.98% | 0.8510 | 24.20% | 28.69% |
| Dhrystone 1.1 + Whetstone DP | 35 → 51 | 0.8734 / 26.84% | 0.8752 | 27.80% | 25.85% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 34 → 49 | 0.8646 / 21.10% | 0.8679 | 21.33% | 17.35% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 34 → 43 | 0.8652 / 19.15% | 0.8692 | 18.26% | 19.88% |
| Dhrystone 1.1 + Whetstone SP + LINPACK | 33 → 48 | 0.8550 / 24.06% | 0.8559 | 23.54% | 20.63% |

Full results and baselines are in the
[machine-readable summary](data/classic/spec89-summary.csv). For Dhrystone 1.1 +
LINPACK the joint exponent is 0.8483 (CI95 0.8345–0.8617). Adding the SPEC89
systems moves each exponent by at most 0.008 and the observed-target P95 by at
most 1.5 points: SPEC89 and SPEC92 targets lie on one power law through the 780.
Under the former proportional factor the 1987–90 SPEC89 systems lay below the
line fitted to 1990s systems, and joining them raised the observed-target P95 by
10–20 points; the anchored exponent below one removes most of that conflict. The
largest SPEC89 misses remain the IBM RS/6000 systems (Dhrystone 1.1 + LINPACK:
the RS/6000 530, 550 and 320 overpredicted by 67–85%), whose LINPACK n=100 is high
relative to their integer speed.

### Pair review

Every distinct classical↔SPEC text pair the shared system admits was listed
(156 on 80 systems) and checked for model, clock and processor agreement
(2026-10-02). Reviews (`rev:classical-spec-pair/…`):

- **Rejected:** Netlib Dhrystone "SPARCstation 2 (50)" and "SPARCstation 2 (80)"
  (a 50 MHz SPARC and an 80 MHz Weitek part) against the SPEC89 SPARCstation 2,
  which shipped at 40 MHz. The 40 MHz Dhrystone rows stay paired.
- **Accepted unscaled:** HP 9000/730 result A0217 (66.67 MHz) with Dhrystone and
  LINPACK rows reporting 66 MHz; and the CPU92 Indigo2 Extreme disclosure ("50MHz
  MIPS R4000SC", the external clock) with rows giving the R4000's 100 MHz
  internal clock, which linear clock scaling would have halved.
- **Rejected (2026-10-03, user decision):** the HP 9000/720's January 1996
  SPECint92 disclosure (HP-UX B.10.01, C A.10.11) against its 1991-era SSBA,
  Netlib Dhrystone and LINPACK results: same hardware, five years of compiler
  gains on the SPEC side only. The system leaves the SPEC92-only cohorts but
  stays in the joint cohorts through its SPEC89 results.

The DEC 7000 Model 610 Dhrystone row (182 MHz) against the 200 MHz CPU92
disclosure is a genuine clock difference. The
[catalogue spelling aliases](identity-and-dates.md#catalogue-spelling-aliases)
let IBM RS/6000 "RISC Sys/6000-NNN" and "Model NNN" rows share systems with the
SPEC89 "RS/6000 NNN" results.

## SPEC89-only hardware estimates

The bridge produces **188 source-record estimates on 95 resolved systems** from
SPECint89 results of the SPEC89 package and curated observations (including the
[printed SPEC89 means](historical-sources.md#printed-spec89-means-19901991)),
independently of classical availability. Bridge-table rows are the bridge's own
evidence and reference-definition rows are excluded. Each record keeps its
reported SPECint89, record ID and source URL and is labelled
`one_edge_estimate`. In the [estimate table](data/classic/spec89-estimates.csv),
`factor_ci95_target_low/high` are the score times the factor interval, not
individual prediction bounds.

## Reproduce and validation

```sh
MPLCONFIGDIR=/tmp/cpushowspeed-mpl .venv/bin/cpushowspeed classic spec89-fit
```

Input is the built database. Outputs under `data/derived/classic/spec89-fit/`:
bridge evidence and summary, observations with observed/estimated labels,
summary and predictions with matched baselines, and the joint scatter. Compact
bridge evidence and summary, cohort summary, estimate table and audit are kept
in `research/data/classic/spec89-*`.

Synthetic tests (`tests/test_classical_fit.py`) check that only the
int89_to_int92 edge enters the bridge, that a result reporting SPECint92 is not
also a SPEC89 estimate, removal of held-out systems from the bridge, shared-system
covariance and preserved shared uncertainty when inferred observations repeat.

## History

- 2026-09-26: snapshot verified; an archived 89/92 source-paired scatter (now
  retired) plotted the 17 integer and 17 SPECmark89 rows without fitting.
- 2026-09-27: two-edge bridge `SPECint89 → SPECint92 → rate-VAXen` (factor
  0.9570709) and the joint experiment on name-matched pairs.
- 2026-10-02: pairing over resolved systems; the 89-only and joint cohorts grew
  (Dhrystone 1.1 + LINPACK from 7 to 17 SPEC89 systems).
- 2026-10-03: re-anchored to SPECint92 (one edge, 0.9603866); the printed SPEC89
  means, vendor reports and Usenet lists added SPEC89 systems to the joint
  cohorts; the proportional factor was replaced by the power law through the
  VAX-11/780 (median observed-target P95 33.6% → 27.8%, SPEC89-target P95 42.0%
  → 32.8% over 114 rows).
