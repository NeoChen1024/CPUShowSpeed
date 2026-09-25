# SPEC result collection

The collector stores original public result exports and disclosures without
changing scores or asserting an isolated-core interpretation. It does not yet
produce a normalized cross-generation performance timeline.

## Official CPU95–CPU2026 results

SPEC's public result tool offers a bulk CSV for each generation. This is the
primary bulk import: one request per generation, with the original bytes and a
source URL, retrieval date, content type, and SHA-256 in adjacent metadata.
The per-quarter index collector supplies individual result IDs and HTML/CSV
links so detailed disclosures can be checked as needed.

```sh
./.venv/bin/cpushowspeed spec dump
./.venv/bin/cpushowspeed spec index
./.venv/bin/cpushowspeed spec verify
./.venv/bin/cpushowspeed spec fetch --generation cpu2017 --track integer-speed --limit 25
./.venv/bin/cpushowspeed spec fetch --generation cpu95 --period res9509 --limit 25
```

All commands are resumable by default. `dump --refresh` refreshes the bulk
snapshot; `index --refresh` refreshes quarterly pages. `fetch` skips already
saved disclosures and prefers the official per-result CSV when present (HTML
for CPU95). Its default track is `integer-speed`; other speed, rate, and all
tracks can be selected explicitly. Requests to publication indexes and detail
pages are paced by `--delay`.

The first full bulk snapshot, retrieved on 2026-09-25, contained:

| Generation | Results |
| --- | ---: |
| CPU95 | 2,574 |
| CPU2000 | 7,654 |
| CPU2006 | 48,381 |
| CPU2017 | 46,865 |
| CPU2026 | 499 |

The total, 105,973, matched the official quarterly indexes by individual
result ID for all five generations, with zero IDs missing from either side.
These are all submitted result types, including speed, rate, integer, and
floating-point measurements; they are not 105,973 points for one common metric. The bulk CSV's `Test Date` and `Published` fields often have month-only
precision; preserve that precision rather than manufacturing `YYYY-MM-DD` dates.
Older exports may contain non-UTF-8 characters; retain their original bytes
and decode text conservatively during later parsing.
CPU2017 and CPU2026 speed disclosures may use multiple threads. Preserve the
per-benchmark requested thread settings when interpreting system speed; keep
rate submissions and their copy counts on a separate throughput track.

Original exports, indexes, and disclosures are in `data/raw/spec/`; result-link
manifests are in `data/derived/spec/`. Both are generated local data, excluded
from Git. Curated findings checked against a disclosure belong in `research/`.
Public use of scores must follow [SPEC Fair Use](https://www.spec.org/products/fairuse/).

## First VAX-anchored figure

The `plot spec92` command uses the locally cached Netlib CPU92 detailed reports
to draw annual CINT92 integer-speed box plots and a highest-submission line.
SPECint92 is already relative to the VAX-11/780 reference time, so these
scores can be labeled `VAXen (CINT92)` without a cross-generation conversion.
The horizontal coordinate is the SPEC Newsletter issue year, not a machine
introduction or test year.

```sh
./.venv/bin/cpushowspeed plot spec92
```

The command writes PNG/SVG figures, per-disclosure source-linked CSV records,
annual statistics, and an exclusion audit to `data/derived/figures/`; its JSON
stdout names each output. The CSV is a reproducible chart input, not the final
schema for historical PDF and KIPS findings. It uses original SPECint92 rather
than the later `SPECbase_int92`, because baseline reporting began in 1994.
Reports with one or more CPUs enter the chart if they have a positive
SPECint92 score and a test month no later than the labeled issue month. The
reported CPU count stays with each record. The source file hash is verified
against its collection metadata before extraction. It does not infer a full
`YYYY-MM-DD` from the issue's month-only date.

The 2026-09-25 cached set contained 305 integer speed disclosures. The figure
regenerated on 2026-09-26 includes 300: three lacked a SPECint92 score, and
two claimed a test month after their issue month. The 1993–1996 yearly counts
are 69, 111, 110, and 10. All 300 included scores were independently checked
against their corresponding Netlib issue summary rows. The original 1992 issues
are still absent from this electronic archive, and 1996 has sparse coverage.
See the [checked chart results](../research/spec92-vaxen.md).

This figure stops at CPU92. Later suites require validated same-system bridges
to use the VAXen axis. In a spot check, a
[CPU2017 speed disclosure](https://www.spec.org/cpu2017/results/res2017q2/cpu2017-20161026-00020.csv)
had 384 selected base threads even though the bulk export's `Parallel` field
was `No`; therefore that field alone cannot describe the workload's
parallelism. [SPEC's field guide](https://www.spec.org/cpu2017/Docs/result-fields.html)
explains that `Parallel` is set from compiler-flag annotations, while the
per-benchmark `Threads` field reports the number allowed. The
[CPU2017](https://www.spec.org/cpu2017/Docs/runrules.html) and
[CPU2026](https://www.spec.org/cpu2026/docs/runrules.html) rules warn that the
number requested may differ from what the benchmark actually implements.
All 75 cached CPU2026 integer-speed disclosures were checked on
2026-09-25, and every selected base benchmark reported more than one requested
thread. These remain valid candidates for the system-speed track after the
CPU92-to-CPU2026 bridges are validated; they cannot be called single-thread
measurements.

## Surviving CPU92 results

SPEC says it has no complete electronic CPU92 result archive. Netlib's
[Performance Database Server](https://www.netlib.org/performance/html/spec.html)
reproduces selected SPEC newsletter submissions. The earliest issue in its
index is June 1993 (Volume 5, Issue 2); it is not the beginning of CPU92.

```sh
./.venv/bin/cpushowspeed spec legacy92
./.venv/bin/cpushowspeed spec legacy92-fetch --issue 6_93
./.venv/bin/cpushowspeed spec legacy92-fetch
```

`legacy92` caches issue summaries and records links to individual reports.
`legacy92-fetch` downloads those reports, optionally restricted to one issue.
On 2026-09-25, all 537 distinct reports linked from the 44 collected speed
summaries were downloaded and have source/sha256 metadata. The collected source
pages remain separate from later transcriptions. See the
[early archive research](../research/spec-early-archives.md) for 1989–1992
sources and remaining gaps.
