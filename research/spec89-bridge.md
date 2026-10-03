# SPECint89 bridge to speed-VAXen and joint classical fitting

Computed and reviewed: 2026-09-27. Recomputed on resolved systems: 2026-10-02.
Re-anchored to speed-VAXen: 2026-10-03 (method `spec89-one-edge-speed-joint-v3-resolved-systems`).

## Evidence path

Historical routes are anchored to **speed-VAXen**, the single-job quantity of
the [integer-speed chain](spec-speed-chain.md): VAX-11/780 is the SPEC92
reference machine, so one SPECint92 point is one speed-VAXen. SPECint89 needs
one empirical edge:

`SPECint89 → SPECint92 (= speed-VAXen)`.

The [archived integer bridge](data/spec89/v2.0.0/csv/bridges89_92.csv) supplies
17 paired source rows on 15 resolved systems, including republications and
development-level systems with their existing qualifications, in scope
`historical-spec:spec89-bridge`. Outside that table, six resolved systems
(DECstation 5000/20, /25, /125, /133, /240 and HP 9000/720) have both a
SPECint89 and a SPECint92 result; they are recorded in the audit and not used
as bridge evidence.

| Edge | Role | Systems / source rows | Multiplier | Factor CI95 | LOMO model-center P95 |
| --- | --- | ---: | ---: | --- | ---: |
| SPECint89 → SPECint92 | speed bridge | 15 / 17 | **0.9603866** | 0.943053–0.979110 (joint) | 8.61% |
| SPECint92 → rate-VAXen | diagnostic, not chained | 24 / 48 | 0.9965475 | 0.992201–1.000572 | 1.86% |

Thus `estimated speed-VAXen = 0.9603866 × SPECint89`. The interval quantifies
fitted-factor uncertainty, not a 95% prediction interval for an individual old
machine. Transporting the bridge to earlier architectures remains an assumption.
There is no base-variant bridge, so the route is peak-only.

The second row is the [reviewed DEC N3909 columns](classic-pdf-extraction.md)
reporting both SPECint92 and SPECrate_int92 on one-processor systems. Its factor
is close to 1: for these machines one speed-VAXen and one rate-VAXen nearly
agree. It is kept as a diagnostic of the two quantities; by the 2026-10-03
decision rate is never chained into a speed estimate (formerly SPEC89 targets
reached rate-VAXen through both edges, factor 0.9570709).

## Joint model experiment

The joint model adds the SPECint89 classical pairs after translating their
targets through the bridge, beside directly observed SPECint92 targets. It uses
the `same_system` cohort (resolved system, no clock scaling), fixed
equal-weight geometric composites and the model-balanced log-ratio estimator of
the [direct composite experiment](classic-composite-fitting.md). Dhrystone
versions, Whetstone precision and LINPACK n=100 remain distinct. No residual
threshold removes a source or machine. A result that reports SPECint92 is used
through that value, not also through its SPECint89 estimate.

For each pattern, `spec92_only`, `89_only` and `joint` cohorts are compared, with
all single-component baselines on identical tuples and folds. Every derived row
labels its target `observed_speed_target` or `estimated_89_target`.

CI95 uses 10,000 draws (seed 20260926) that jointly resample resolved systems
from the union of the bridge edge and the classical cohort; a system present in
both receives one weight. Each draw refits the bridge and the classical factor
and applies one shared bridge multiplier to every SPEC89 target, so repeated
converted observations do not shrink the common uncertainty.

Leave-one-model-out removes the test system from the bridge and the classical
fit. Errors against observed SPECint92 are reported separately from agreement
with converted SPEC89 targets; only the former validates against measurements.

## Coverage and observed-target holdouts

Equal-weight composites, `same_system`. P95 is the leave-one-system-out
model-center error on observed SPECint92 targets; the last column is agreement
with the converted SPEC89 targets.

| Composite | SPEC92-only → joint systems | SPEC92-only P95 | Joint P95, observed | Joint P95, SPEC89 |
| --- | ---: | ---: | ---: | ---: |
| Dhrystone 1.1 + LINPACK | 43 → 61 | 40.51% | 49.74% | 77.42% |
| Dhrystone 2.1 + LINPACK | 44 → 56 | 44.26% | 50.53% | 74.87% |
| Whetstone native + LINPACK | 9 → 11 | 22.14% | 27.60% | 51.01% |
| Whetstone DP + LINPACK | 34 → 49 | 27.26% | 43.91% | 59.95% |
| Whetstone SP + LINPACK | 32 → 47 | 21.75% | 34.76% | 62.21% |
| Dhrystone 1.1 + Whetstone DP | 34 → 49 | 26.48% | 33.89% | 45.79% |
| Dhrystone 1.1 + Whetstone DP + LINPACK | 33 → 47 | 22.16% | 34.03% | 44.68% |
| Dhrystone 2.1 + Whetstone DP + LINPACK | 33 → 41 | 25.24% | 36.31% | 38.48% |
| Dhrystone 1.1 + Whetstone SP + LINPACK | 32 → 46 | 20.42% | 30.44% | 43.29% |

Full results and baselines are in the
[machine-readable summary](data/classic/spec89-summary.csv). For Dhrystone 1.1 +
LINPACK the joint factor is 1.530745 (CI95 1.432851–1.633008). The largest
SPEC89 misses remain the IBM RS/6000 systems, whose LINPACK n=100 results are
high relative to their integer speed; one shared composite factor cannot follow them.

### Changes from MIPS Performance Brief 3.5 (2026-10-03)

[Brief 3.5](vendor-performance-reports.md#mips-performance-brief-35-1988) adds
classical results for the MIPS M/120-5 and M/2000, which have SPEC89 but no
SPECint92. Joint cohorts gain one or two systems; both are underpredicted, so joint
factors rise 0.4–1.7% (D1.1 + LINPACK 1.524484 → 1.530745) and observed-target P95
rises 0.6–2.2 points. Whetstone SPEC89-target P95 falls (Dhrystone 1.1 +
Whetstone DP 56.66% → 45.79%).

### Changes from the 1990 DEC report rows (2026-10-03)

The [1990 DEC RISC summary](vendor-performance-reports.md) adds Dhrystone,
Whetstone and LINPACK results for nine 1987–90 RISC systems with SPEC89 results
but no SPECint92. The SPEC92-only cohorts are unchanged; joint cohorts gain 0–8
SPEC89 systems (Dhrystone 1.1 + LINPACK 54 → 60, Whetstone DP + LINPACK 41 → 48).
All new systems are underpredicted, so joint factors rise 3–9% (D1.1 + LINPACK
1.460299 → 1.524484) and observed-target P95 worsens by 0–11 points (42.82% →
49.13%). Whetstone SPEC89-target P95 falls (Whetstone DP + LINPACK 77.78% →
62.59%) as the larger cohort dilutes the N3909 VAX 4000/300 outlier
(see the [network](classic-network-fitting.md#changes-from-the-1990-dec-report-rows-2026-10-03)).

### Changes from the rate-anchored run (2026-10-03)

The SPEC92 cohort is much larger: 43 rather than 25 systems for Dhrystone 1.1 +
LINPACK. SPECint92 is reported by more results than one-processor rate (DEC
columns without a rate row, multi-processor disclosures, and the bridge table's
own SPECint92 values). Systems whose SPECint92 is now observed no longer enter
as SPEC89 estimates, so the joint cohort adds fewer SPEC89-only systems
(43 → 54 instead of 25 → 45). Joint factors move by −5% to +3% (D1.1 + LINPACK
1.447277 → 1.460299). The observed-target P95 values are not comparable with the
earlier rate-target values because the evaluated systems differ.

## Changes from the name-matched run (2026-10-02)

In that (rate-anchored) run the bridge edges were unchanged (17 rows / 15
systems and 48 columns / 24 systems; point factors identical; CI endpoints moved
in the fourth decimal because the bootstrap resamples resolved systems). The 89-only and joint
cohorts grew: Dhrystone 1.1 + LINPACK went from 7 to 17 SPEC89 systems, and
three-family patterns went from none to 5–11. The earlier matching used
normalized names and required an OS match between DEC columns and archive rows,
which SPEC89 rows do not carry; resolved-system pairing treats OS as a run
condition. The pairs were reviewed on 2026-10-02 (below); configuration
equivalence beyond model and clock remains unverified.

## Pair review and spelling merges (2026-10-02)

Every distinct classical↔SPEC text pair that the shared system admits was
listed (135 on 65 systems before the spelling merges, 156 on 80 after) and checked for
model, clock and processor agreement. Five `result_pair` reviews resulted
(`rev:classical-spec-pair/…`):

- **Rejected:** Netlib Dhrystone "SPARCstation 2 (50)" and "SPARCstation 2 (80)"
  (a 50 MHz SPARC and an 80 MHz Weitek part) against the SPEC89 SPARCstation 2,
  which shipped at 40 MHz. Where the SPEC89 row gives no clock, the shared system
  had paired them. The 40 MHz Dhrystone rows stay paired.
- **Accepted unscaled:** HP 9000/730 result A0217 (66.67 MHz) with the Dhrystone
  and LINPACK rows reporting 66 MHz, the same clock rounded; and the CPU92
  Indigo2 Extreme disclosure ("50MHz MIPS R4000SC", the external clock) with
  Dhrystone and LINPACK rows giving the R4000's 100 MHz internal clock, which
  linear clock scaling would have halved.

The DEC 7000 Model 610 Dhrystone row (182 MHz) against the 200 MHz CPU92
disclosure is a genuine clock difference and stays a `linear_clock` scaling. The
reviews move no factor here by more than 0.5%. The larger shift comes from
the [catalogue spelling merges](chronology.md#catalogue-spelling-aliases-2026-10-02):
IBM RS/6000 "RISC Sys/6000-NNN" and "Model NNN" rows now share systems with the
SPEC89 "RS/6000 NNN" results, adding three SPEC89 systems and their LINPACK and
Dhrystone pairs. In that (rate-anchored) run, seven of the eight patterns whose
observed-target holdout changed improved, while agreement with inferred SPEC89
targets worsened (37.45% → 67.09%) on the RS/6000s.

## SPEC89-only hardware estimates

The bridge produces **179 source-record estimates on 90 resolved systems**
from `historical-spec:spec89`, independently of classical availability.
Reference-definition rows are excluded. Each record preserves its reported
SPECint89, record ID and source URL and is labelled `one_edge_estimate`.

In the [estimate table](data/classic/spec89-estimates.csv),
`estimated_speed_vaxen` is the SPECint89 score times the bridge factor;
`factor_ci95_target_low/high` are the score times the factor interval, not
individual prediction bounds. Estimates for architectures outside the bridge
cohort require additional validation.

## Reproduce and validation

```sh
MPLCONFIGDIR=/tmp/cpushowspeed-mpl .venv/bin/cpushowspeed classic spec89-fit
```

Input: the built database (`data build`). Options are documented by CLI help.

Outputs under `data/derived/classic/spec89-fit/`:

- `bridge-evidence.csv`, `bridge-summary.csv`: source-linked edge observations
  and fits of the bridge and the diagnostic edge.
- `observations.csv`: classical components, original and assigned targets,
  with observed/estimated labels.
- `summary.csv`, `predictions.csv`: observed/estimated-target validation and
  matched single-score baselines.
- `joint-scatter.png/.svg`: observed points, estimated triangles and factor CI95.

Compact bridge evidence and summary, cohort summary, estimate table and audit
(database input digest, direct-overlap check, route and settings) are retained
under `research/data/classic/spec89-*`.

Validation: synthetic tests (`tests/test_classical_fit.py`) check that only the
int89_to_int92 edge enters the bridge, that a result reporting SPECint92 is not
also used as a SPEC89 estimate, removal of held-out systems from the bridge,
shared-system covariance and preservation of shared uncertainty when inferred
observations repeat.
