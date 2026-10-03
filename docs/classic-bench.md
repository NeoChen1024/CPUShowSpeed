# Classical benchmark runner (planned design)

Status: design selected 2026-10-03; **nothing here is implemented yet**. This
document owns the planned runner that executes Dhrystone 1.1/2.1, Whetstone and
LINPACK n=100 on current hardware, as a benchmark or as a timed stress test.
Its results would be new measurements by this project, a separate evidence class
from historical published scores.

## Purpose

Same-machine classical and SPEC results calibrate the classical speed-VAXen
routes ([classical fits](../research/classical-fits.md)). Running the classical
programs on machines that also have SPEC CPU results adds modern overlap points
under recorded compiler, flags and execution conditions. A `copies=1` result is
compared with SPEC integer **speed**; a `copies=N` result is a throughput
measure, comparable in form to SPEC rate, and never enters speed-VAXen
calibration.

## Sources

Original files are vendored unchanged under `bench/upstream/`; local changes are
kept as patches under `bench/patches/` and applied in the build tree, so the
originals stay byte-identical to the archived blobs. Each upstream directory has
a `PROVENANCE.md` with the original URL, retrieval date, BLAKE3 of the archived
file, the original author line and the statement that the source carries **no
licence or copyright notice** (all predate open-source licensing conventions).

| Benchmark | Source | Archived blob | Notes |
| --- | --- | --- | --- |
| Dhrystone 2.1 | [netlib `dhry-c`](https://www.netlib.org/benchmark/dhry-c) (Weicker C 2.1: `dhry.h`, `dhry_1.c`, `dhry_2.c`, RATIONALE, README_C) | `2ec5910d…` (shar, unpacked without executing it) | Reference version |
| Dhrystone 1.1 | `Dhry1.c` in Longbottom's [`benchnt.zip`](http://www.roylongbottom.org.uk/benchnt.zip) (Richardson's 1.1 via James Day's ANSI C) | `f661844b…` | No original Richardson 1.1 file is archived; this copy already changes `Proc3(NextRecord.PtrComp)` to `Proc3(&…)` and uses DOS `conio.h` |
| Whetstone | Longbottom [`whets.c`](http://www.roylongbottom.org.uk/whets.c), the C/C++ version approved by Harold Curnow | `f031750c…` | Reports MWIPS; `DP` selects double precision |
| LINPACK n=100 | netlib `linpackc.new` (Bonnie Toy, 1988; daxpy fix 1994) — **not yet archived**; fallback `LINPACK.C` in `benchnt.zip` | `f661844b…` (fallback) | `SP`/`DP`, `ROLL`/`UNROLL` |

## Patch policy

Patches may only:

- replace platform timing, console I/O, prompts and result-file writing;
- turn each program's `main` into an entry function that runs a requested number
  of benchmark passes and returns elapsed work, leaving the measured loop body
  untouched;
- make file-scope state `static` and give the entry function a
  precision-specific name, so the Whetstone source compiles twice (SP and DP)
  into one binary and the precision is chosen **at runtime**; one invocation can
  measure both;
- keep each program's own result check (Dhrystone final variable values,
  Whetstone checksums, LINPACK normalized residual). A failed check invalidates
  the run.

Every patch states what it changes and why. Changes to arithmetic, loop counts
per pass, data types or call structure are not allowed.

## Build

CMake builds the C kernels and a C++ harness (`nlohmann/json`, added as a
`third-party/` submodule from [nlohmann/json](https://github.com/nlohmann/json)
for its single header). Requirements:

- Dhrystone 2.1 keeps `dhry_1.c` and `dhry_2.c` as separate translation units
  with interprocedural optimization (LTO) off, following Weicker's measurement
  rules in RATIONALE.
- A **reference profile** fixes flags (planned: `-O2`, no LTO, no
  `-ffast-math`, no target-specific `-march`); a user profile may override them
  and is labelled as such.
- The configure step writes compiler ID, version, target triple and the full
  per-kernel flags into the binary, so every result reports them.

## Execution

```
cpushowspeed-bench --benchmark dhrystone21 --copies 8 --duration 60 --interval 1
```

(Planned interface; final option names belong to `--help`.)

- **Benchmarks**: `dhrystone11`, `dhrystone21`, `whetstone-sp`, `whetstone-dp`,
  `linpack100-dp` (and `linpack100-sp` as a non-calibration variant). Several
  may run in sequence in one invocation.
- **Copies**: the parent forks N independent processes, one per selected
  hardware thread; no benchmark state is shared. All copies pass a start barrier
  before timing begins. Pinning is on by default where the platform supports it
  and recorded either way.
- **Duration**: each copy first calibrates a pass count giving work units of
  roughly 10–50 ms, runs a warm-up excluded from scoring, then repeats units
  until the requested duration ends. Time comes from
  `clock_gettime(CLOCK_MONOTONIC)`.
- **Intervals**: copies report completed units with timestamps to the parent,
  which forms per-interval rates and samples CPU frequency, so a long run also
  works as a stress test showing throttling or decay.

## Scores

| Benchmark | Unit | Definition |
| --- | --- | --- |
| Dhrystone 1.1 / 2.1 | DMIPS | Dhrystones per second ÷ 1757 (VAX-11/780 VMS) |
| Whetstone SP / DP | MWIPS | As computed by `whets.c` |
| LINPACK n=100 | MFLOPS | (2/3·n³ + 2·n²) floating-point operations per solve ÷ time ÷ 10⁶ |

Each copy's score is its rate over the measured window. The run reports every
copy, their sum (throughput), and median and minimum interval rates. LINPACK
n=100 fits in cache on current CPUs; its result describes in-cache dense solve
speed and needs many repetitions for timer accuracy.

## Output

One JSON document per invocation on stdout; progress and errors on stderr.
Planned fields:

- benchmark, unit, precision, source and patch hashes;
- compiler ID/version, target, flags and build profile;
- copies, CPU list and pinning status, duration, warm-up, interval length;
- per-copy scores, aggregate, interval series (aggregate and per copy), median
  and minimum, result-check status;
- host: OS and version, CPU model, logical CPU count, frequency samples or
  `unknown`, start and end timestamps.

## Platform support

| Item | Linux | FreeBSD | NetBSD | OpenBSD |
| --- | --- | --- | --- | --- |
| Pinning | `sched_setaffinity` | `cpuset_setaffinity` | `sched_setaffinity_np` | not available; recorded as unpinned |
| Frequency | `/sys/devices/system/cpu/cpuN/cpufreq/scaling_cur_freq` | `sysctl dev.cpu.N.freq` | `sysctl machdep.cpu.frequency.current` (architecture dependent) | `sysctl hw.cpuspeed` (system-wide) |
| CPU model | `/proc/cpuinfo` | `sysctl hw.model` | `sysctl machdep.cpu_brand` / `hw.model` | `sysctl hw.model` |

Unavailable values are reported as `unknown`, never estimated. Reported
frequency is the OS's current value, not a measured clock.

## Data use

Planned: a `cpushowspeed` Click command builds the runner, stores the raw JSON
under `data/derived/bench/`, and a curated adapter records accepted runs as
project measurements with the machine's resolved system and processor identity.
Only `copies=1` reference-profile results would be eligible as classical
calibration inputs, and only after their machine has matching SPEC speed
results; user-profile and multi-copy results stay diagnostic.

## Open items

- Archive netlib `linpackc.new` (21,903 bytes) and compare it with the
  Longbottom `LINPACK.C` derivative.
- Choose the reference compiler flags and check them against how the historical
  calibration scores were compiled.
- Search for an original Richardson Dhrystone 1.1 file to compare with the
  Longbottom/Day copy.
