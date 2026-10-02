# CPUShowSpeed
## 60 Years of CPU Benchmarks

CPUShowSpeed studies historical computer performance on a common **VAXen**
scale in two parallel quantities: **rate-VAXen** (whole-machine integer
throughput) and **speed-VAXen** (one integer job). They are never merged or
converted into each other. Published benchmark results, inferred scores and manual reconstructions remain distinguishable.
The subtitle describes the research horizon; a complete sixty-year series has
not yet been established.

## The unit: 1 VAX

Both quantities set the VAX-11/780 to 1.

**1 rate-VAX is the VAX-11/780 reference throughput under the SPEC CPU92
integer-rate convention.** Its reference rate score is `604800 / 25500 ≈ 23.717647`, so:

```text
rate-VAXen = SPECrate_int92 × 25500 / 604800
```

The same normalization applies to the base metric `SPECrate_base_int92`.

**1 speed-VAX is one SPECint92 speed point.** The VAX-11/780 is the SPEC92
reference machine, so its SPECint92 is 1 by definition:

```text
speed-VAXen = SPECint92   (or SPECbase_int92)
```

Do not apply the rate conversion to a speed score or vice versa. A value inferred
from another suite is an **estimated** VAX-equivalent, not a measured SPEC92
submission. Classical, SPEC89 and instruction-mix estimates are speed-VAXen.
On a multi-core machine rate ÷ speed approximates effective parallelism; it is a
diagnostic, not a conversion. `1 VAX`, `2 VAXen`, `1k VAXen`,
`2M VAXen` and `26m VAX` are display labels; stored values are unprefixed numbers.
See [unit definitions](research/tracks/vaxen.md) and the
[SPEC CPU92 rate definition](https://www.spec.org/cpu92/specrate.txt).

## The fitting assumption: y = kx

The primary calibration assumes a **multiplicative relationship passing through
the origin**, `y = k × x`, between benchmark scales. It does not fit an additive
intercept. The coefficient is estimated from log score ratios: take medians
within the declared model/configuration groups, average the group log ratios,
then exponentiate. For modern adjacent suites, x is the newer suite's score and
y the older suite's score; the direction is recorded for every model.

This is a geometric ratio estimator, not ordinary least squares. On log axes
its slope is fixed at one; a separately reported free slope is diagnostic.
Base and peak are fitted separately. Repeated submissions are retained, while
grouping controls their fit weight. The assumed relationship is approximate
and need not hold equally across architectures, workloads or software.

For classical composites, x is a fixed equal-weight geometric mean of the
specified benchmark scores in declared units; a separate k is fitted for each
combination. Factor CI95, held-out P95 error and prediction uncertainty are
reported separately. Broader historical coverage is a research objective;
increased error after adding valid evidence is not by itself a failed experiment.

Integer speed has its own chain to SPECint92 (speed-VAXen); it is never
fitted against rate and does not change the rate-VAXen definition.

## Four research tracks

| Track | Purpose | Current position |
| --- | --- | --- |
| [1. VAXen reference](research/tracks/vaxen.md) | Define the common unit and evidence classes | Two parallel quantities: rate-VAXen (CPU92 rate normalization) and speed-VAXen (SPECint92 = 1) |
| [2. SPEC92–2026 rate and speed chains](research/tracks/spec-rate.md) | Fit successive integer-rate and integer-speed suites, separately | Both implemented, conditional calibration; CPU2026 coverage remains limited |
| [3. SPEC89 recovery and bridge](research/tracks/spec89.md) | Recover scattered scores and link SPECint89 → SPECint92 speed | Implemented one-edge peak estimate |
| [4. Classical benchmark extension](research/tracks/classical.md) | Use early workloads to establish historical speed-VAXen calibration points | Direct and joint pair/triple experiments; older-machine extrapolation remains conditional |

Start with the [research overview](research/overview.md). The
[model registry](research/model-registry.json) records metric types, datasets,
calculation dependencies and shared evidence; its [generated catalog](research/catalog.md)
provides a readable map of every research document. There is no implication that
all routes are independent evidence or equally validated.

## Reproduce and explore

On Arch Linux, use the repository-local environment managed by `uv`:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -e .
uv run --no-sync cpushowspeed --help
uv run --no-sync cpushowspeed research validate
```

`requirements.txt` is the single dependency list. Convert a modern integer-rate
score with the saved calibration:

```sh
uv run --no-sync cpushowspeed predict spec-rate 2017 base 11800 --format text
```

The converter prints estimated VAXen and conditional calibration CI95.
For arbitrary classical score subsets, use the [classical predictor](docs/classical-prediction.md):

```sh
uv run --no-sync cpushowspeed predict classical --dhrystone-1-1 10 --format text
```

It uses the saved network calibration to estimate SPECint92 peak speed
(speed-VAXen) and joint calibration CI95. Inputs may contain one or several benchmark families.

- [Combined VAXen timeline](docs/timeline.md): CPU-first history, rate-VAXen and speed-VAXen side by side, historical speed estimates and time zoom (`uv run cpushowspeed plot timeline`).
  Initialize `third-party/hyparquet` and `third-party/fzstd` with `git submodule update --init`, then serve the Parquet-backed export over HTTP; no npm build is required.
- [Documentation index](docs/README.md): contracts, methods and acquisition tools.
- [Research index](research/README.md): current analyses, source evidence and diagnostics.
- [Annual rate results](research/annual-rate-vaxen.md): configuration-year views.
- [Roadmap](docs/TODO.md): remaining evidence and validation work.
