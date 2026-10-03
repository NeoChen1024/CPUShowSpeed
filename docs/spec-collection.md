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
Netlib's 305 CINT92 speed disclosures (`data/raw/spec/cpu92/netlib/details/`) are read
by the input catalogue directly, with each composite checked against its six ratios
and the issue summaries. Both tracks use one page parser
(`cpushowspeed.spec92_disclosure`) that keeps all 21 labelled fields of the fixed PDS
layout verbatim, the issue (volume, number, month), the result table, the reported
means and the tuning notes; hardware availability, software availability and test
months are normalized to `YYYY-MM` and an unreadable value (two rate pages print
`######`) stays empty. A second compiler line (often the Fortran compiler) is joined
with `; `. The same parser reads all 232 CFP92 pages, which no adapter consumes.

Netlib's combined rate list omits one detail linked from an issue summary;
the [source audit](../research/spec-sources.md#spec-cpu92-integer-rate-archive) identifies it and
preserves the issue-linked result. The separate 1992 Digital vendor brief is
source evidence, not part of this official-submission fit.

## Reproduce the rate fits

```sh
./.venv/bin/cpushowspeed data extract
./.venv/bin/cpushowspeed data build
./.venv/bin/cpushowspeed bridge fit-rate-generations
./.venv/bin/cpushowspeed bridge fit-rate92-anchor
```

Both fit commands read the built database (`--database`, default
`data/derived/schema/cpushowspeed.sqlite`), whose observations come from the
hash-checked bulk exports and parsed CPU92 rate records, and pair results over
resolved system and processor identity. The first fits CPU95→CPU2026 adjacent
integer-rate scores. The second fits CPU92 rate directly to CPU95 rate and
extends the chain using the first command's strict factors, after checking
that both were fitted from the same database inputs. Both retain repeated submission
pairings in source-linked point exports while weighting processor
configurations in the factor calculation. The [primary rate audit](../research/spec-chains.md)
owns the methods, tables, scatterplots and limits. The VAXen chain is an
exploratory **throughput** normalization, not a measured score for a modern
VAX or a validated general conversion.

The preserved SPEC89 source snapshot and historical documents are archival
material. They do not enter these rate commands.

## Whole-chain rate confidence intervals

```sh
./.venv/bin/cpushowspeed bridge bootstrap-rate-chain
```

Run after both rate-fitting commands. The source-hash and edge-overlap checks
precede resampling. The command writes the compact
[chain CI table](../research/data/spec/fitting/integer-rate-chain-intervals.csv)
and ignored NPZ replicate arrays and JSON diagnostics under
`data/derived/spec/fitting/`. See the rate audit for the independence assumption
and uncertainty scope before propagating the draws.

## SPEC95/CPU2000 overlap-loss audit

`uv run --no-sync cpushowspeed bridge audit-95-2000 --fetch-review` reproduces
the [SPEC95/CPU2000 overlap-loss audit](../research/spec-sources.md#cpu95cpu2000-overlap-audit).
It exports candidate aliases, RAM/resource ablations and source-field checks
without changing production matches or coefficients. Omit `--fetch-review`
for cached-source-only review.

## Field and execution-resource audit

    uv run cpushowspeed spec audit-fields
    uv run cpushowspeed spec fetch-resources --generation cpu2017 --track integer-speed --limit 25
    uv run cpushowspeed spec fetch-resources --generation cpu2017 --track integer-rate --limit 25

The audit's --fetch-samples option restores the versioned reviewed sample manifest.
fetch-resources shares the resumable collector, raw cache and manifest, and accepts
integer/floating-point speed/rate tracks. Current detailed audit scope is integer.
Selected CSV tables retain benchmark copies/threads by mode; legacy CPU95/2000 HTML
rate tables are supported. No runtime count is inferred from enabled CPU resources.
[Resource audit](../research/spec-sources.md#source-fields-and-execution-resources) owns findings and coverage.
