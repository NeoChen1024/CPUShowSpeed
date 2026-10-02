# SPEC speed, rate and joint predictors of the older suite's rate

Reviewed: 2026-10-02. Status: implemented conditional fit on the schema database
(`spec-speed-rate-predictors-v5-resolved-identity`). It replaces the name-matched
joint-track experiment removed on 2026-10-02, which remains in Git history.

## Question and method

Can a newer suite's integer **speed** score, alone or with its **rate** score,
predict the integer rate a machine scored in the previous suite? Each adjacent
boundary (CPU92/95, 95/2000, 2000/2006, 2006/2017, 2017/2026) fits three
zero-intercept log predictors of the older rate: speed only, rate only, and their
equal geometric mean `sqrt(speed × rate)`.

- **Tuples.** One older-rate target, one newer speed and one newer rate result.
  All three pairs (target–speed, target–rate, speed–rate) must be
  `hardware_near` over resolved identity: same `system_id`, processor key and chip
  count, clock within 1%, equal memory, compatible cores and threads. At the CPU92
  boundary the target–rate pair must instead be review-accepted, as in the
  [CPU92 anchor](cpu92-cpu95-bridge.md). A known rate-copy conflict between target
  and rate input drops that mode.
- **Same tuples for every predictor**, so their errors compare input availability
  on identical hardware.
- **Estimator.** System medians, then configuration (processor, chips, clock)
  medians, then the mean over configurations; at least three processor models.
- **Holdouts** leave out every configuration of one processor model; errors are
  against the observed older rate. Primary statistic: model-center P95.
- **VAXen.** Local factor × the saved `same_os` rate chain of the older suite.
  CI95 combines a processor-model cluster bootstrap of the local factor (one weight
  matrix per boundary and mode) with the saved chain draws. This assumes
  independent cohorts; the tuples share no configuration with the chain edges the
  older suite depends on (checked; the fit refuses otherwise).

## Results

`cpushowspeed bridge fit-speed-predictors`, 2026-10-02. 420 tuples; values are
P95 of held-out model-center error against the observed older rate.

| Boundary | Mode | Tuples / configs / models | Speed only | Rate only | Joint |
| --- | --- | ---: | ---: | ---: | ---: |
| CPU95 → CPU92 | base | 54 / 16 / 7 | 20.2% | 20.3% | 20.3% |
| CPU95 → CPU92 | peak | 54 / 16 / 7 | 18.2% | 17.9% | 18.0% |
| CPU2000 → CPU95 | both | 2 / 1 / 1 | insufficient | insufficient | insufficient |
| CPU2006 → CPU2000 | base | 86 / 30 / 28 | 111.7% | 29.4% | 56.2% |
| CPU2006 → CPU2000 | peak | 44 / 14 / 14 | 116.9% | 24.2% | 49.4% |
| CPU2017 → CPU2006 | base | 89 / 28 / 26 | 167.0% | 15.3% | 71.0% |
| CPU2017 → CPU2006 | peak | 29 / 8 / 8 | 157.2% | 13.8% | 72.9% |
| CPU2026 → CPU2017 | base | 36 / 23 / 20 | 311.3% | 8.0% | 103.3% |
| CPU2026 → CPU2017 | peak | 24 / 15 / 12 | 278.0% | 10.7% | 98.7% |

VAXen per input score (central, CI95), base mode:

| Suite | Speed only | Joint `sqrt(S×R)` |
| --- | --- | --- |
| CPU95 | 37.51 (32.63–41.40) | 12.50 (10.87–13.80) |
| CPU2006 | 2,539 (2,121–3,031) | 1,226 (1,076–1,395) |
| CPU2017 | 99,148 (76,372–133,630) | 23,455 (20,002–27,892) |
| CPU2026 | 912,570 (666,310–1,200,300) | 109,140 (90,863–128,980) |

The [summary CSV](data/spec/speed-predictors/summary.csv) has every boundary,
mode and predictor with local and VAXen intervals; the
[coverage CSV](data/spec/speed-predictors/coverage.csv) and
[audit](data/spec/speed-predictors/audit.json) record counts and input hashes.

## Interpretation

- Until CPU95, one speed copy and one rate copy measure similar work, and all
  three predictors are equivalent (about 20% P95).
- From CPU2006 on, rate counts every core while speed is one task. Speed alone
  misses by 110–310% P95, and adding speed to rate makes the rate-only prediction
  worse. Speed-derived VAXen of multi-core machines are therefore weak estimates.
- Rate only on these small matched cohorts reproduces the full rate chain within
  −5.8% to +2.2%. That checks the triple construction; it is not independent
  validation.
- The CPU2000 boundary has two tuples on one processor model. No CPU2000 speed
  or joint estimate exists. Relaxing the memory requirement adds no tuple there,
  so the gap is the scarcity of CPU95-rate/CPU2000-speed overlaps, not the memory
  rule.

## Changes from the name-matched experiment

The former experiment matched names with three selectable policies (strict,
RAM + aliases, CPU + clock). Resolved identity replaces the aliases. One policy
remains, the same `hardware_near` tier the rate chain uses. The former speed
predictor VAXen differ by one factor per suite and mode: CPU95 −2.7%/+0.9%,
CPU2006 +46.5%/+27.0%, CPU2017 +15.7%/+41.9%, CPU2026 +15.0%/+15.4% (base/peak).
CPU2000 had speed estimates only under the relaxed policies; now it has none.

## Limitations

- Only the CPU92 boundary has VAXen-valued targets. Later boundaries validate the
  local older-rate factor, and their VAXen rest on the saved chain.
- Transfer beyond the overlap hardware is unvalidated. That matters most for
  speed only on many-core machines.
- Speed threads, rate copies and software equivalence within a tuple are not
  verified beyond the recorded counts.
- CI95 covers coefficient sampling, not individual prediction error.
