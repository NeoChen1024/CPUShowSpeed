# Track 4 — Classical benchmarks and pre-SPEC extension

The research goal is to obtain older hardware performance evidence and establish
calibration pivots to the speed-VAXen scale (SPECint92 = 1). Benchmark publication date and
the age of tested hardware are distinct: classical workloads also ran on later
machines, which provide overlap rather than pre-SPEC evidence by themselves.

## Current routes

| Route | Owner | State |
| --- | --- | --- |
| Classical composite → observed SPECint92 | [Direct composite experiment](../classic-composite-fitting.md) | Pairs/triples; base/peak separate |
| Classical → SPECint89 → SPECint92 | [SPEC89 bridge experiment](../spec89-bridge.md) | 89-only cohort; peak; sparse intersections |
| Classical → observed plus inferred SPECint92 targets | [Joint experiment](../spec89-bridge.md#joint-model-experiment) | Shared bridge uncertainty; separate validation by target class |

Dhrystone 1.1/2.1, Whetstone native/SP/DP, and LINPACK n=100 are distinct inputs.
Each pair/triple has fixed equal component weights and its own multiplier.
Missing components do not silently change the formula. Broader coverage is an
explicit objective; increased error is diagnostic rather than an exclusion rule.

## Sparse per-benchmark calibration

The [network experiment](../classic-network-fitting.md) now permits missing
measurements and estimates separate benchmark coefficients jointly. A single
measurement can produce an estimate once its metric is anchored. It compares
reported clocks with an explicitly qualified Dhrystone/Whetstone linear-clock
scenario and retains single/family/subset holdout results. This is a new log-WLS
model, distinct from the earlier fixed-composite coefficient estimator.

## Supporting evidence and experiments

- [Acquisition](../classic-benchmark-collection.md), [literature](../classic-spec-literature.md),
  and [PDF tables](../classic-pdf-extraction.md) establish source evidence.
- Earlier single/pair/triple, source-column, environment and pooled-native
  experiments were removed on 2026-10-02; they remain in Git history and are
  listed in the [schema cleanup inventory](../schema-cleanup-inventory.md).
- The [mix network](../instruction-mix-network.md) attaches Gibson/ADP ratings to
  the classical network over resolved systems; its links are unapproved.

## Earlier-machine reconstruction boundary

[Gibson/timing evidence](../early-benchmark-evidence.md), the
[machine watchlist](../../docs/machine-watchlist.md) and local PDF/DocIR pipeline
support future work. SIMH execution of assembly plus trace-based timing remains
planned. Emulator wall time is not hardware execution time. CoreMark, Gibson,
ADP and other leads do not yet have established conversion paths to VAXen.

Use [classic collection commands](../../docs/classic-collection.md) to reproduce
the implemented evidence extraction and experiments.

## Historical hardware plot

The [combined classical and SPEC89 timeline](../historical-vaxen-timeline.md)
aggregates original configurations, retains calibration CI95 and records model-year
estimates separately from unknown dates.
