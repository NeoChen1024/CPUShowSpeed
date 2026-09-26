# CPU92–CPU95 integer-speed overlap audit

Reviewed on 2026-09-26. The [reviewed pair table](cpu92-cpu95-reviewed.csv)
contains the original source URLs, published scores, and review notes in CSV.
The reproducible audit command and its generated candidate table are documented
in [SPEC collection](../docs/spec-collection.md). This is an overlap study, not
a calibrated conversion for all CPU95 systems.

## Evidence and selection

The locally cached official CPU95 bulk CSV has 548 `CINT95` speed records, of
which 528 report a positive `SPECint95` peak score. The bulk CSV and quarterly
indexes have identical CPU95 result IDs (2,574 across all CPU95 tracks). Exact
normalized system name, processor description, and CPU count identify 71
CPU92–CPU95 candidate combinations involving 50 distinct CPU95 disclosures.
These combinations are only a search aid: repeated submissions and changed
configurations create multiple pairs for one machine name.

Thirteen distinct systems were reviewed and retained. Their CPU count, CPU
model and clock, reported cache capacities, and memory capacity agree in both
disclosures; test months differ by at most three months. The reported OS release
agrees after reading the disclosure text. Compiler products agree, though some
HP compiler builds differ slightly. `UnixWare 2.0, SDK` and `UnixWare 2.0` are
treated as the same OS release with a disclosure wording difference. These are
**configuration-near pairs**, not proof of identical binaries or run-time
conditions. The other 58 candidate combinations have not been accepted or
classified as permanently invalid.

For each pair, the script verifies Netlib's CPU92 detail score against its
separate issue summary and verifies the CPU95 bulk peak/base scores against
its HTML disclosure. It checks source SHA-256 metadata, the cited URLs, and
the reviewed CSV scores. For example, the [Alder System 166 MHz CPU92 report](https://www.netlib.org/performance/html/spec.inteli4.cint92.12_95.notes.html)
reports `SPECint92 = 327.1`, while its [CPU95 report](https://www.spec.org/cpu95/results/res9512/p032.html)
reports `SPECint95 = 7.11`. Their ratio is `327.1 / 7.11 = 46.006`.
The [HP 9000 J200 CPU92 report](https://www.netlib.org/performance/html/spec.j200i.cint92.12_95.notes.html)
and [CPU95 report](https://www.spec.org/cpu95/results/res9509/p029.html)
provide another checked pair: `141.1 / 3.64 = 38.764`.

## Expanded overlap scatter

The scatter plot is generated locally at
`data/derived/figures/cpu92-cpu95-overlap-scatter.png` from **all 71 candidate
pairings**; its source-linked plotted records are
`data/derived/spec/cpu92-cpu95-candidates.csv`. Both generated files stay out of Git.
There are 13 reviewed configuration-near pairs, 54 additional relaxed pairs
whose reported cache capacities agree, and four whose cache capacities differ
or cannot be resolved from the disclosure wording. All retain the same
normalized system name, CPU description, and CPU count, but relaxed pairs may
change memory, OS, compiler, or test month. No per-system deduplication is
applied. Exact coordinate ties are labeled with their multiplicity.

These are 71 *pairings*, not 71 independent machines: multiple submissions on
one or both sides can create several points for one configuration. The scatter
retains those observations as requested, while its gray constant-ratio guides
are visual references, not fitted conversion factors. The 13 reviewed pairs
alone support the provisional ratio summary below; the relaxed points are
exploratory until their configuration differences are evaluated.

## Provisional ratios

The reported factor is the geometric mean of per-system
`SPECint92 / SPECint95` ratios. It is in **VAXen per SPECint95 point** only as
an approximate bridge under the matched workload and software conditions.
Each row below is based on distinct system names. The ranges show observed
pair ratios, not confidence intervals.

| Reviewed stratum | Pairs | Peak factor | Peak pair range | Base factor sensitivity |
| --- | ---: | ---: | ---: | ---: |
| x86, UnixWare, Intel Reference C | 7 | 45.205 | 44.689–46.006 | 42.039 |
| PA-RISC, HP-UX, HP C | 6 | 39.243 | 38.764–39.792 | 33.253 |
| Both pooled, diagnostic only | 13 | 42.349 | 38.764–46.006 | — |

The two peak stratum means differ by about 15.2%. Architecture, OS, compiler,
and vendor are confounded in this sample, so this difference cannot be
attributed to the CPU architecture alone. Pooled 42.349 is strongly affected
by the chosen mix of the two groups and **must not be used to relabel all
CPU95 results as VAXen**. Base-to-base sensitivity also differs by group;
`SPECbase_int92` is only available for the relevant later CPU92 submissions
and is not interchangeable with the original peak series.

[SPEC's CPU95 Q&A](https://spec.org/cpu95/qanda) explicitly says there is no
universal CPU92↔CPU95 conversion. The present evidence supports narrow,
software-conditioned bridge estimates for the reviewed systems. Before
extending the annual VAXen figure, collect and review overlaps for additional
processor and software families, examine original tuning notes and OS/build
differences, and validate predictions on independent systems. Keep original
CPU95 scores and estimated VAXen values as separate fields.
