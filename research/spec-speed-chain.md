# SPEC integer-speed chain (speed-VAXen)

Reviewed: 2026-10-03. Status: implemented conditional fit on the schema database
(`integer-speed-chain-v1`). It replaces the speed/rate/joint predictors of the
older suite's rate (removed 2026-10-03; in Git history).

## Decision

By user decision (2026-10-03), speed and rate are two parallel quantities, each
with its own chain, and they are not merged:

- **rate-VAXen** (throughput): the existing
  [rate chain](spec95-spec2026-rate-fitting.md), CPU2026 rate → … → SPECrate_int92.
- **speed-VAXen** (one job): this chain, CPU2026 speed → … → SPECint92 speed.

VAX-11/780 is the SPEC92 reference machine, so its SPECint92 speed is 1 by
definition: **one speed-VAXen is one SPECint92 point**. Both quantities set the
VAX-11/780 to 1. For one-processor machines they nearly agree (the SPEC89 bridge's
SPECint92 → rate92 factor is 0.9966 VAXen per SPECint92). On multi-core
machines their ratio approximates effective parallelism; it is a diagnostic,
not a combination. Historical routes (classical, mixes, SPEC89) are anchored to
speed-VAXen.

## Method

`cpushowspeed bridge fit-speed-chain` fits each adjacent speed edge exactly as
the rate chain's later edges:

- **Pairs.** Automatic `hardware_near` speed pairs over resolved identity: same
  system, processor, chip count, clock within 1%, equal memory, compatible cores and
  threads. A known equal-count conflict in a mode drops that mode's ratio.
  The CPU92/CPU95 edge is not individually reviewed, unlike the rate anchor.
- **Estimator.** Log ratios take system medians, then processor-configuration
  (processor, chips, clock) medians, then the mean over configurations.
- **CI95.** Each edge has its own configuration-cluster bootstrap (10,000 draws,
  seed 20261003). The edges share no configuration or submission (checked; the fit
  refuses otherwise) and are combined as independent. Held-out error leaves out
  one configuration.

## Results

2026-10-03, base / peak. Factor = older-suite speed points per newer-suite point.

| Edge | Pairs | Configs | Models | Factor (CI95) | Held-out P95 |
| --- | --- | --- | --- | --- | --- |
| CPU95 → CPU92 | 45 / 45 | 21 / 21 | 9 / 9 | 37.885 (35.866–39.896) / 41.665 (40.029–43.257) | 19.4% / 17.2% |
| CPU2000 → CPU95 | 16 / 13 | 11 / 9 | 7 / 5 | 0.091298 (0.085992–0.097668) / 0.095775 (0.091992–0.10036) | 19.5% / 12.5% |
| CPU2006 → CPU2000 | 90 / 52 | 40 / 21 | 34 / 20 | 155.99 (150.82–160.98) / 146.50 (141.16–152.37) | 19.3% / 13.7% |
| CPU2017 → CPU2006 | 659 / 454 | 114 / 107 | 54 / 51 | 8.5726 (8.4971–8.6726) / 8.6617 (8.5922–8.7515) | 7.3% / 7.0% |
| CPU2026 → CPU2017 | 32 / 22 | 19 / 15 | 18 / 13 | 2.7110 (2.2987–3.2674) / 2.7248 (2.3550–3.2100) | 58.6% / 44.8% |

Speed-VAXen per reported speed point, with the rate chain's VAXen per rate point
(`same_os`) for comparison:

| Suite | Speed base (CI95) | Speed peak (CI95) | Rate base / peak |
| --- | --- | --- | --- |
| CPU92 | 1 (defined) | 1 (defined) | 0.04216 / 0.04216 |
| CPU95 | 37.885 (35.852–39.924) | 41.665 (40.018–43.287) | 4.1283 / 4.6535 |
| CPU2000 | 3.4588 (3.1825–3.7733) | 3.9904 (3.7673–4.2446) | 292.08 / 345.43 |
| CPU2006 | 539.55 (493.82–592.19) | 584.61 (545.05–628.36) | 583.98 / 645.16 |
| CPU2017 | 4,625.3 (4,229.1–5,075.1) | 5,063.7 (4,716.8–5,448.2) | 5,522.2 / 6,064.5 |
| CPU2026 | 12,539 (10,400–15,451) | 13,798 (11,751–16,551) | 12,874 / 14,869 |

Raw per-point scales differ by suite definition, so rate points are not speed
points. Where a suite's speed and rate share benchmarks and reference machine
(CPU2006), a one-copy rate point should be near one speed point; the rate factor
is 8% (base) and 10% (peak) above the speed factor. In CPU2017, whose speed and
rate are different benchmark sets, it is 19% / 20% above.

Files: [factors](data/spec/fitting/integer-speed-factors.csv) and
[chain intervals](data/spec/fitting/integer-speed-chain-intervals.csv). The
pairs, configuration logs, bootstrap draws and audit are in
`data/derived/spec/fitting/integer-speed-*`.

## Checks

- All 45 CPU92/CPU95 pairs were listed (2026-10-03): the same system name and clock
  in both suites; per-pair peak ratios range 29–47. Four systems have two CPU95
  submissions with different scores (e.g. HP 712/60: 1.62 and 2.08), and both are
  kept; system medians limit their weight.
- The chain reproduces each edge's statistic exactly (the fit refuses otherwise).

## Limitations

- CPU2017 speed allows several threads (OpenMP), so speed is "one job", not
  "one thread". CPU2026 speed has sparse overlap (45% / 59% P95).
- The CPU92/CPU95 speed pairs are unreviewed, unlike the rate anchor's
  reviewed pairs.
- Transfer beyond the overlap hardware is unvalidated. CI95 covers the mean scale
  factors, not individual prediction error.
