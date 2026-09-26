# Scope and metrics

The primary research target is the performance of one documented system
configuration, including its processors, memory, operating system, compiler,
and benchmark run settings. This is more appropriate across historical machines
and modern multicore systems than claiming to isolate one core. Scores still
measure particular workloads, not a machine's universal speed.

## Workload modes

- **One-copy speed:** completion time for one benchmark workload. The workload
  may use multiple software threads or hardware cores when its run rules permit
  them. This is the primary longitudinal SPEC track; record the reported thread
  settings and enabled hardware configuration.
- **Throughput/rate:** concurrent benchmark copies and work per unit time.
  Preserve copy counts and plot this as a separate system-capacity track. Do
  not mix speed and rate scores into one annual box or conversion without an
  independently justified model.

A strictly single-threaded view can be a secondary subset where the disclosures
support it; lack of such evidence does not exclude a result from the system
speed track. Historical instruction-timing reconstructions must likewise name
the full machine configuration and the workload mix.

## Tracks

- **General-purpose / integer:** use `SPECint92` as the historical statistical
  backbone, with original `SPECint89` retained as a distinct source metric and
  any conversion marked as an estimate. Earlier instruction mixes and
  synthetic programs are exploratory bridges, not equivalent workloads. See
  the [bridge method](methods.md).
- **Embedded integer:** consider CoreMark as a separate series for MCU and
  embedded CPU systems. Its small workload and memory footprint differ from
  SPEC; connect the tracks only after same-system overlap validation.
- **Floating-point / scientific:** keep Whetstone, LINPACK, Livermore Loops, and
  SPEC floating-point results identifiable by workload, precision, and mode.
- **Instruction-mix prehistory:** report manual-derived estimates separately
  from executed benchmarks. They may extend the machine-introduction timeline
  without implying measurements were made at introduction.

The exact benchmark eligibility rules and any combined index remain open research
questions. No cross-generation score is an official SPEC metric.

## Evidence classes

Every value must be identified as one of:

- **Reported measurement:** a published result of executing a named benchmark.
- **Manual reconstruction:** calculated from documented instruction timings and
  an explicit workload mix, including any emulation or memory-access assumptions.
- **Normalized estimate:** inferred through documented overlap between distinct
  benchmark generations or workloads.

Display and exports must preserve the class and original metric. An estimate
must never be presented as a measured score.
