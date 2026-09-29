# SPEC integer-rate collection and fitting

The active collector stores public SPEC result exports and individual
**integer speed and rate** disclosures with source URLs, retrieval dates and SHA-256 metadata.
Original downloaded bytes remain under `data/raw/spec/`; generated manifests,
parsed records and figures remain under ignored `data/derived/spec/`. The
versioned research tables under `research/data/spec/fitting/` contain
source-linked factors. [SPEC Fair Use](https://www.spec.org/products/fairuse/)
governs public presentation of these results.

## Official CPU95–CPU2026 exports

```sh
./.venv/bin/cpushowspeed spec dump
./.venv/bin/cpushowspeed spec index
./.venv/bin/cpushowspeed spec verify
./.venv/bin/cpushowspeed spec fetch --generation cpu2017 --limit 25
./.venv/bin/cpushowspeed spec fetch --generation cpu95 --period res9509 --limit 25
```

`dump` caches one official bulk CSV per generation; `index` caches quarterly
publication pages and records the individual result IDs. `verify` compares
those IDs. The first full bulk snapshot, retrieved on 2026-09-25, contained
2,574 CPU95, 7,654 CPU2000, 48,381 CPU2006, 46,865 CPU2017 and 499 CPU2026
rows, **105,973** in total. These bulk rows cover all metric types; the
rate fit selects only integer-rate rows. An index entry's parsed track decides
which disclosure `fetch` downloads. The default `--track` is `integer-rate`;
`floating-point-rate` is available for separate acquisition.

Collections are resumable: cached pages and disclosures are skipped unless a
refresh flag is requested where supported. Uncached requests use `--delay`.
CPU95 disclosures use HTML; later suites prefer per-result CSV. Month-only
source dates retain month precision, and original exports may contain
non-UTF-8 bytes. The first integer-rate fit parsed respectively **773, 2,481,
15,039, 13,359 and 176** submissions from these five generations.

## Recovered Netlib CPU92 integer-rate results

Netlib separately published `crint92` issue summaries and full CINT92 rate
disclosures. The collector caches 22 issue summaries and 274 unique detailed
rate reports, then checks composite scores against the issue summaries and
per-benchmark rate rows:

```sh
./.venv/bin/cpushowspeed spec legacy92-rate
./.venv/bin/cpushowspeed spec legacy92-rate-fetch
./.venv/bin/cpushowspeed spec legacy92-rate-parse
```

The parser writes [result records](../data/derived/spec/cpu92-rate/cpu92-rate-records.csv)
and [per-benchmark copy counts and timings](../data/derived/spec/cpu92-rate/cpu92-rate-benchmarks.csv).
Netlib's combined rate list omits one detail linked from an issue summary;
the [source audit](../research/spec92-archive-expansion.md) identifies it and
preserves the issue-linked result. The separate 1992 Digital vendor brief is
source evidence, not part of this official-submission fit.

## Reproduce the rate fits

```sh
./.venv/bin/cpushowspeed bridge fit-rate-generations
./.venv/bin/cpushowspeed bridge fit-rate92-anchor
```

The first command fits CPU95→CPU2026 adjacent integer-rate scores from
hash-checked bulk exports. The second fits the recovered CPU92 rate records
directly to CPU95 rate and extends the chain using the first command's strict
factors, after checking source hashes. Both retain repeated submission
pairings in source-linked point exports while weighting processor
configurations in the factor calculation. The [primary rate audit](../research/spec95-spec2026-rate-fitting.md)
owns the methods, tables, scatterplots and limits. The VAXen chain is an
exploratory **throughput** normalization, not a measured score for a modern
VAX or a validated general conversion.

The preserved SPEC89 source snapshot and historical documents are archival
material. They do not enter these rate commands.

## Annual integer-rate view

```sh
./.venv/bin/cpushowspeed plot annual-rate
```

This uses the current hash-checked CPU92 records, official bulk exports, and
tracked rate factors. It writes complete per-submission and undated CSVs plus
PNG/SVG figures to `data/derived/figures/annual-rate/`; the compact
[annual leaders](../research/data/spec/annual-rate-leaders.csv) and
[statistics](../research/data/spec/annual-rate-statistics.csv) are tracked as
research results. All positive scores with a parseable reported hardware month
enter their year; no individual launch-date exclusion is applied. See the
[interpretation and limits](../research/annual-rate-vaxen.md).

## Whole-chain rate confidence intervals

```sh
./.venv/bin/cpushowspeed bridge bootstrap-rate-chain
```

Run after both rate-fitting commands. The source-hash and edge-overlap checks
precede resampling. The command writes the compact
[chain CI table](../research/data/spec/fitting/integer-rate-chain-intervals.csv)
and ignored NPZ replicate arrays and JSON diagnostics under
`data/derived/spec/fitting/`. See the rate audit for the independence assumption
and uncertainty scope before using the draws in yearly plots.

## Combined annual confidence figures

```sh
./.venv/bin/cpushowspeed bridge bootstrap-rate-chain
./.venv/bin/cpushowspeed plot annual-rate-ci
```

The second command checks bootstrap-array and input hashes, then uses complete
replicate vectors to recompute yearly quartiles, fixed representative scores
and the annual frontier. It produces combined hardware/boxplot PNG and SVG
under `data/derived/figures/annual-rate/`, and the compact
[confidence table](../research/data/spec/annual-rate-confidence.csv).
See the [annual figure note](../research/annual-rate-vaxen.md) for the meaning
of the pale envelopes and top-retention statistic.

## Convert one reported integer-rate score

From the repository root:

```sh
./.venv/bin/cpushowspeed convert-rate 2017 base 11800 --format text
./.venv/bin/cpushowspeed convert-rate 2026 peak 100
```

`convert-rate GENERATION MODE SCORE` accepts generations `92`, `95`, `2000`,
`2006`, `2017` and `2026` (also `cpu2017` or `SPEC2017` spellings), and requires
`base` or `peak`. It defaults to JSON on stdout, including the original score,
VAXen, CI95 bounds, calibration scenario, method and table hashes. `--format
text` gives SI-scaled labels. Input scores must be finite and positive. Supply
only the specified suite's integer-rate metric, not floating-point or speed.

The default `--scenario same_os` matches the annual figures;
`--scenario hardware_near` selects the alternate CPU92 anchor. The command
reads the two saved chain/CI CSVs under `--calibration-dir` and rejects mismatched
chain hashes. It needs no raw archives, NPZ samples or new fitting run. The
score multiplies both the central scale and its CI endpoints. This gives a
conditional **calibration** interval and does not estimate individual-machine
prediction error or systematic bias. CPU92's scale is defined, so its
calibration CI has zero width.

## Independent speed/rate experiment

```sh
uv run --no-sync cpushowspeed bridge compare-tracks
uv run --no-sync cpushowspeed classic compare-targets
```

These commands reuse the cached bulk exports and CPU92 speed details. They
write separate experimental outputs and do not replace rate factors or public
prediction manifests. The [dual-track report](../research/spec-dual-track.md)
owns findings, fit semantics and remaining disclosure checks.

For independent-target joint prediction, run
`uv run --no-sync cpushowspeed bridge fit-joint-tracks`. The
[joint experiment](../research/spec-joint-tracks.md) owns cohort restrictions,
masking tests, conditional VAXen coefficients and results.

`uv run --no-sync cpushowspeed bridge audit-95-2000 --fetch-review` reproduces
the [SPEC95/CPU2000 overlap-loss audit](../research/spec95-spec2000-overlap-audit.md).
It exports candidate aliases, RAM/resource ablations and source-field checks
without changing production matches or coefficients. Omit `--fetch-review`
for cached-source-only review.

The [relaxed refit](../research/spec95-spec2000-relaxed-fitting.md) is reproduced
with `bridge fit-joint-tracks --matching-policy ram-aliases` or `cpu-clock`.
Non-strict policies append their name to the output directory roots.
`bridge refit-95-2000` compares the same policies for independent speed/speed
and rate/rate fits. Actual chip/clock conflicts and NC scores remain excluded.

## Field and execution-resource audit

    uv run cpushowspeed spec audit-fields
    uv run cpushowspeed spec fetch-resources --generation cpu2017 --track integer-speed --limit 25
    uv run cpushowspeed spec fetch-resources --generation cpu2017 --track integer-rate --limit 25

The audit's --fetch-samples option restores the versioned reviewed sample manifest.
fetch-resources shares the resumable collector, raw cache and manifest, and accepts
integer/floating-point speed/rate tracks. Current detailed audit scope is integer.
Selected CSV tables retain benchmark copies/threads by mode; legacy CPU95/2000 HTML
rate tables are supported. No runtime count is inferred from enabled CPU resources.
[Resource audit](../research/spec-resource-field-audit.md) owns findings and coverage.
