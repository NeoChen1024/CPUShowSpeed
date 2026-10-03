# Classical benchmark runner

Status (2026-10-03): the `classic-bench` runner is implemented and checked on
Linux x86-64 with GCC 16.2 and Clang 22.1. The FreeBSD, NetBSD and OpenBSD code
paths are written but **not yet compiled or run on those systems**. A Click
wrapper, storage of results and their use in calibration remain planned.

This document owns the runner that executes Dhrystone 1.1/2.1, Whetstone and
LINPACK n=100 on current hardware, as a benchmark or as a timed stress test.
Its results are new measurements by this project, a separate evidence class
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

Byte-identical originals are kept in
[`classic-benchs/original/`](../classic-benchs/original/README.md), whose README
records each file's URL, retrieval date, BLAKE3 and authorship. None carries a
licence or copyright notice; all predate open-source licensing conventions. The
project's modified versions are complete sources (not patch sets) in sibling
directories.

| Benchmark | Original | Modified source |
| --- | --- | --- |
| Dhrystone 2.1 | netlib `dhry-c` (Weicker C 2.1) | `classic-benchs/dhrystone-2.1/` (`dhry.h`, `dhry_1.c`, `dhry_2.c`) |
| Dhrystone 1.1 | `Dhry1.c` from Longbottom's `benchnt.zip` (Richardson's 1.1 via James Day's ANSI C) | `classic-benchs/dhrystone-1.1/dhry11.c` |
| Whetstone | Longbottom `whets.c`, the C/C++ version approved by Harold Curnow | `classic-benchs/whetstone/whets.c` |
| LINPACK n=100 | netlib `linpackc.new` (Toy 1988, Menninger 1993, Dongarra daxpy fix 1994) | `classic-benchs/linpack/linpack.c` |

No original Richardson Dhrystone 1.1 file is archived; Longbottom's copy already
changes `Proc3(NextRecord.PtrComp)` to `Proc3(&…)`. Longbottom's `LINPACK.C`
in `benchnt.zip` derives from the same netlib translation and remains in the
raw archive for comparison.

## What changed

The measured code — the statements each program times, its data types,
per-pass loop counts and call structure — is unchanged; `diff` against
`original/` shows only surrounding code. Each modified file states its changes
in a `CPUShowSpeed:` comment.

- **All**: `main`, prompts, console input, result files and platform timers are
  replaced by entry points declared in `common/classic_kernel.h`. Each runs a
  requested number of passes and returns the time measured **at the program's
  own timing boundaries**, read from `CLOCK_MONOTONIC` instead of process CPU
  time. The sources compile as `gnu89`, so K&R definitions and their argument
  promotion stay as written.
- **Dhrystone 2.1**: the loop is timed as a whole as before, and every final
  variable value the original printed with "should be" is checked.
  `Arr_2_Glob[8][7]` is reset before each call so its `runs + 10` check cannot
  overflow on long runs. `dhry_1.c` and `dhry_2.c` stay separate translation
  units with LTO off, following Weicker's rules.
- **Dhrystone 1.1**: the original single translation unit is kept, with the
  program's own check (`Array2Glob[8][7] == runs + 10`).
- **Whetstone**: one pass runs `whetstones(xtra, 100, …)`; the score is the
  original MWIPS, `xtra × 100 / (10 × TimeUsed)`, where `TimeUsed` sums the
  eight section times with section 1 divided by its repetition factor of 10.
  The file is compiled twice (with and without `DP`) under renamed external
  symbols, so precision is selected at run time. `dtime()` returns seconds since
  the start of the call, which keeps the original `float` timing arithmetic
  precise in single precision. The original check (`Check != 0`) is kept.
- **LINPACK**: `matgen`, `dgefa`, `dgesl` and the BLAS are unchanged. The driver
  uses n = 100 with leading dimension 201, as in Dongarra's benchmark and Toy's
  driver (Menninger's `linpack()` used 2n). It times `dgefa` and `dgesl`
  separately, and reports rolled and unrolled BLAS as separate benchmarks
  instead of averaging them. Menninger's version had no result check. After
  each call, outside the timed region, the driver computes the normalized
  residual of Toy's driver, ‖Ax − b‖ / (n‖A‖‖x‖ε), with ε from `<float.h>`. A
  value above 100, or one that is not finite, fails the run. Single and double
  precision are compiled separately.

## Build

```sh
git submodule update --init third-party/nlohmann-json
cmake -S classic-benchs -B classic-benchs/build -G Ninja
cmake --build classic-benchs/build
```

The C++17 harness uses [nlohmann/json](https://github.com/nlohmann/json)
v3.12.0 from the `third-party/nlohmann-json` submodule.

- **Profiles**: `-DCB_PROFILE=reference` (the default) compiles the kernels
  with `-O2`. `-DCB_PROFILE=custom` takes `-DCB_KERNEL_FLAGS=…` and labels every
  result `custom`.
- **Flag guard**: configure fails if `CMAKE_C_FLAGS` or a build type would add
  flags outside the profile. Interprocedural optimization is off.
- **Provenance**: every result embeds the C compiler and its version, the
  effective kernel flags, the dialect, and the SHA-256 of each original and
  modified source.

The reference flags are provisional. On the development machine (Ryzen 7
5700X3D), switching the reference build from GCC 16 to Clang 22 changes results
substantially, so results from different compilers are not interchangeable:

| Benchmark | GCC 16 | Clang 22 |
| --- | --- | --- |
| Dhrystone 1.1 | ≈ 32,000 DMIPS | ≈ 76,000 DMIPS (the single file is inlined) |
| Dhrystone 2.1 | ≈ 28,000–32,000 DMIPS | ≈ 30,000 DMIPS |
| LINPACK SP rolled | ≈ 6,200 MFLOPS | ≈ 13,000 MFLOPS (the rolled loops are vectorized) |
| LINPACK unrolled | similar for both compilers | similar for both compilers |

## Running

```sh
classic-benchs/build/classic-bench --benchmark dhrystone-2.1 --copies 8 --duration 60
```

`--help` owns the options, and `--list` prints the eight benchmark IDs:
`dhrystone-1.1`, `dhrystone-2.1`, `whetstone-sp`, `whetstone-dp`, and
`linpack100-{dp,sp}-{rolled,unrolled}`. Without `--benchmark`, all eight run in
sequence.

- **Copies**: the runner forks N independent processes. Each is pinned to one
  logical CPU unless `--no-pin` is given or the platform cannot pin. The CPUs
  are either the first N the process may use or those given with `--cpus` (for
  example `0,2,4-7`). Copies share no benchmark state. Each calibrates a pass
  count whose wall time is about `--unit-ms` (default 20 ms), then all copies
  wait at a common start barrier.
- **Duration**: after `--warmup` seconds (default 2, unscored), each copy runs
  units that start within the `--duration` window (default 10 s). The last unit
  may end slightly after the window.
- **Scores**: a copy's score is its total work divided by its total
  program-measured time over the window, in the program's own unit. Wall time is
  reported separately. The aggregate is the sum over copies.

| Benchmark | Unit | Definition |
| --- | --- | --- |
| Dhrystone 1.1 / 2.1 | DMIPS | Dhrystones per second ÷ 1757 (VAX-11/780 VMS) |
| Whetstone SP / DP | MWIPS | As computed by `whets.c` |
| LINPACK n=100 | MFLOPS | (2/3·n³ + 2·n²) operations per solve ÷ (`dgefa` + `dgesl` time) ÷ 10⁶ |

- **Intervals**: every `--interval` seconds (default 1), the runner records:
  - each copy's rate over the units that ended in that interval;
  - the sum of those rates;
  - the OS-reported frequency of each copy's CPU.

  It also reports the median, minimum and maximum of the complete interval
  sums, so a long run shows throttling or decay.

LINPACK n=100 fits in cache on current CPUs; its result describes in-cache
dense solve speed.

## Output

The runner writes one JSON document (`"schema": "classic-bench-v1"`) to stdout,
and progress and errors to stderr. The exit status is:

- 0 when every benchmark is valid;
- 1 when any result check fails or a copy fails;
- 2 for invalid options.

The JSON document contains:

- `tool`: version, build profile, compilers, kernel flags and dialect, and
  source hashes.
- `host`: OS, release, machine, CPU model, logical CPU count, and frequency
  source.
- `settings`: copies, pinning and CPU list, duration, warm-up, interval, unit
  target, and timer.
- `results[]`, one entry per benchmark:
  - benchmark, family, unit, precision, variant and score definition;
  - UTC start and end times;
  - `valid`, `errors` and `aggregate_score`;
  - per-copy CPU, passes per unit, units, program and wall seconds, check
    status and score;
  - the interval summary and series, and frequency samples.

## Platform support

| Item | Linux | FreeBSD | NetBSD | OpenBSD |
| --- | --- | --- | --- | --- |
| Pinning | `sched_setaffinity` | `cpuset_setaffinity` | `sched_setaffinity_np` | not available; runs unpinned |
| Frequency | `/sys/devices/system/cpu/cpuN/cpufreq/scaling_cur_freq` | `sysctl dev.cpu.N.freq` (falls back to CPU 0) | `sysctl machdep.cpu.frequency.current` | `sysctl hw.cpuspeed` |
| CPU model | `/proc/cpuinfo` | `sysctl hw.model` | `sysctl machdep.cpu_brand` or `hw.model` | `sysctl hw.model` |

Unavailable values are reported as `null`, never estimated. The reported
frequency is the OS's current value, not a measured clock; on NetBSD and
OpenBSD it is system-wide.

## Checks performed

- `diff` against `original/` confirms that the measured loops of all four
  programs, and LINPACK's `matgen` through `idamax`, are unchanged.
- All eight benchmarks pass their result checks:
  - with GCC and Clang reference builds, for one copy;
  - with the GCC reference build, for eight pinned copies.
- Invalid options exit with status 2.
- A Clang custom build (`-O3 -march=native`) runs and is labelled `custom`, and
  `-DCMAKE_C_FLAGS` is rejected at configure time.
- Not yet checked:
  - a deliberately failing result check;
  - the BSD code paths;
  - agreement with published scores for a machine whose historical results are
    known.

## Data use (planned)

A `cpushowspeed` Click command would build the runner and store the raw JSON
under `data/derived/bench/`. A curated adapter would record accepted runs as
project measurements, with the machine's resolved system and processor
identity. Only `copies=1` reference-profile results would be eligible as
classical calibration inputs, and only after their machine has matching SPEC
speed results; custom-profile and multi-copy results stay diagnostic.

## Open items

- Choose the reference compiler and flags, including whether to limit inlining
  for single-file Dhrystone 1.1 and vectorization for LINPACK. Check the choice
  against how the historical calibration scores were compiled.
- Compare netlib `linpackc.new` with the Longbottom `LINPACK.C` derivative.
- Search for an original Richardson Dhrystone 1.1 file to compare with the
  Longbottom/Day copy.
- Build and run on FreeBSD, NetBSD and OpenBSD.
