# Scope and metrics

The rate target is **single-node / documented-system throughput**, not
single-core performance; the parallel speed target is one job on that system. A result belongs to the tested processors, memory, operating
system, compiler and benchmark run settings. The principal evidence is a
published integer-rate measurement, with its concurrent copy counts when the
disclosure provides them. Reported scores and cross-generation estimates must
remain distinguishable.

## Two parallel quantities: rate-VAXen and speed-VAXen

By user decision (2026-10-03) VAXen has two parallel quantities, each with its
own chain, and they are never merged or converted into each other:

- **rate-VAXen** (throughput): `SPECrate_int92 × 25500 / 604800`, with later
  suites chained through their integer-rate metrics.
- **speed-VAXen** (one job): SPECint92 speed, since the VAX-11/780 is the SPEC92
  reference machine; later suites are chained through their integer-speed
  metrics ([speed chain](../research/spec-chains.md#speed-chain)).

Both set the VAX-11/780 to 1. Speed denotes task completion, not a single-core
guarantee (CPU2017 speed may run threads). Classical, SPEC89 and instruction-mix
routes are calibrated to speed-VAXen. The rate ÷ speed ratio of one machine
approximates effective parallelism and is a diagnostic only. Base/peak is an
independent dimension. Never combine speed and rate observations into one fit.

## Active SPEC rate series

The [CPU92–CPU2026 rate audit](../research/spec-chains.md)
uses `SPECrate_int92` and the integer-rate metrics in CPU95, CPU2000,
CPU2006, CPU2017 and CPU2026. It fits adjacent suites on matched system
submissions. The CPU92 rate formula defines the VAX-11/780 one-copy throughput
reference; later scores receive *estimated* VAX-reference units through the
matched-suite factors. The chained factors are exploratory because hardware
and software conditions, architecture mix and systematic uncertainty still
require review. Conditional full-chain bootstrap intervals are implemented.

Do not multiply any single-workload score by processor or core count to make a
rate result. Copy count is a benchmark run setting, not a synonym for chips,
cores, threads or measured runtime workers. Keep base and peak results
separate. A system's introduction, test and publication dates are different
events; the [data contract](data-contract.md) defines how to preserve them.

The [shared timeline](timeline.md) is the current interactive view, showing
SPEC92–2026 rate-VAXen and speed-VAXen records side by side with historical
speed-VAXen proxies, all with CPU-first dating. It keeps
source scope and node-count uncertainty visible; reported cluster results are
not silently certified as single-node measurements.

The earlier [annual integer-rate view](../research/spec-chains.md#annual-rate-view) now groups
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
specified. The SPEC89 corpus now supports an implemented one-edge peak
estimate, SPECint89 → SPECint92 speed-VAXen. Direct classical speed fits
and joint fits with these estimated targets are implemented; reported and
inferred targets remain separate. See the [research index](../research/README.md).
These extensions do not turn native SPECint89/92 scores into measured rate
submissions or change either SPEC chain's inputs.

## Evidence classes

Every numeric value must identify its class:

- **Reported measurement:** a published result of executing a named benchmark.
- **Manual reconstruction:** a calculation from documented instruction timings
  under an explicit workload and configuration.
- **Normalized estimate:** a score inferred through a documented overlap
  between different benchmark generations or workloads.

Exports must keep the original metric, source and class. No normalized
estimate is an official SPEC measurement.
