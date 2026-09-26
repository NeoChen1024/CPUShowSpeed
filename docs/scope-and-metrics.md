# Scope and metrics

The active research target is **throughput of a documented machine
configuration**. A result belongs to the tested processors, memory, operating
system, compiler and benchmark run settings. The principal evidence is a
published integer-rate measurement, with its concurrent copy counts when the
disclosure provides them. Reported scores and cross-generation estimates must
remain distinguishable.

## Active SPEC rate series

The [CPU92–CPU2026 rate audit](../research/spec95-spec2026-rate-fitting.md)
uses `SPECrate_int92` and the integer-rate metrics in CPU95, CPU2000,
CPU2006, CPU2017 and CPU2026. It fits adjacent suites on matched system
submissions. The CPU92 rate formula defines the VAX-11/780 one-copy throughput
reference; later scores receive *estimated* VAX-reference units through the
matched-suite factors. The chained factors are exploratory because hardware
and software conditions, architecture mix and full-chain uncertainty still
require review.

Do not multiply any single-workload score by processor or core count to make a
rate result. Copy count is a benchmark run setting, not a synonym for chips,
cores, threads or measured runtime workers. Keep base and peak results
separate. A system's introduction, test and publication dates are different
events; the [data contract](data-contract.md) defines how to preserve them.

A first [annual integer-rate view](../research/annual-rate-vaxen.md) now groups
all positive dated submissions by their **reported configuration hardware
availability** and shows the highest score per year plus the submission
distribution. Its frontier is exploratory and not a model-launch history.

## Historical extension

The project may extend machine-capacity evidence earlier than SPEC CPU92 by
checking original benchmark publications and instruction-timing documents.
A manual-derived workload throughput is a separate reconstruction with stated
instruction mix, memory assumptions and source pages; it is never a
retroactively executed SPEC submission. Floating-point/scientific capacity
benchmarks and embedded benchmarks such as CoreMark may become separate
tracks after their workload, parallelism and reference conventions are
specified. The preserved SPEC89 archive is a source corpus, not an input to
the current rate fit.

## Evidence classes

Every numeric value must identify its class:

- **Reported measurement:** a published result of executing a named benchmark.
- **Manual reconstruction:** a calculation from documented instruction timings
  under an explicit workload and configuration.
- **Normalized estimate:** a score inferred through a documented overlap
  between different benchmark generations or workloads.

Exports must keep the original metric, source and class. No normalized
estimate is an official SPEC measurement.
