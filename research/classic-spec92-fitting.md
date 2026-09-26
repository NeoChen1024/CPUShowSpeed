# Classical benchmarks / SPEC92 rate: first exploratory fits

Review date: 2026-09-26. Implemented with `classic fit-spec92` after the
[hardware overlap audit](classic-spec-overlap.md). These are candidate-cohort
statistics, not configuration-approved calibration. SPEC89 aggregate/mixed
scores and the production CPU92–CPU2026 conversion chain are unchanged.

## Results

The table below uses **known compatible clocks and one reported SPEC CPU**.
The factor multiplies the stated classical unit to estimate SPEC92 rate-VAXen
within this cohort. Intervals are model-cluster bootstrap CI95, conditional on
the selected candidates. Errors are leave-one-model-out P95 on model centers.

| Metric | SPEC variant | Pairs / models | Factor | Factor CI95 | LOO P95 error |
| --- | --- | ---: | ---: | --- | ---: |
| Dhrystone 1.1 DMIPS | base | 12 / 4 | 0.655 | 0.538–0.807 | 42.6% |
| Dhrystone 1.1 DMIPS | peak | 19 / 8 | 0.729 | 0.636–0.857 | 34.3% |
| Dhrystone 2.1 DMIPS | base | 24 / 6 | 0.813 | 0.701–0.949 | 33.1% |
| Dhrystone 2.1 DMIPS | peak | 31 / 10 | 0.863 | 0.741–1.012 | 39.4% |
| Whetstone Fortran native MWIPS | base | 9 / 6 | 0.792 | 0.681–0.976 | 39.5% |
| Whetstone Fortran native MWIPS | peak | 17 / 9 | 0.821 | 0.728–0.981 | 41.1% |
| Whetstone Fortran DP MWIPS | base | 9 / 6 | 0.884 | 0.798–1.013 | 26.1% |
| Whetstone Fortran DP MWIPS | peak | 17 / 9 | 0.920 | 0.838–1.047 | 34.2% |
| LINPACK n=100 MFLOPS | base / peak | 2 / 1 each | insufficient groups | — | — |

Allowing missing clocks increases Dhrystone 2.1 peak to 33 pairs / 12 models:
factor **0.782**, CI95 **0.655–0.934**, LOO P95 **70.9%**. This deterioration
is a useful sensitivity result, not grounds to discard its source rows.
LINPACK then has 14 pairs / 10 models for peak: factor **3.591**, CI95
**3.013–4.619**, LOO P95 **64.8%**. Many DEC entries state nanosecond periods;
this first run does not turn them into verified MHz fields.

All 20 metric/variant/scenario combinations, including two insufficient-group
cases, are in [fitting-summary.csv](data/classic/fitting-summary.csv).
The [audit](data/classic/fitting-audit.json) records hashes, seed and counts.
Full pair-level records, original values, citations and exclusion reasons are
in the generated `data/derived/classic/fit-spec92/pairs.csv` (840 rows;
these are metric/scenario rows, not 840 independent measurements).

## Interpretation and limits

- Dhrystone is the most directly relevant next review cohort for an integer
  comparison. The current fitted factors are not precise enough to justify
  automatically extending the annual rate-VAXen chart into earlier decades.
- Whetstone/LINPACK are cross-workload diagnostics. A smaller observed error
  in one small cohort does not establish general integer-performance validity.
- Same model and clock do not establish identical processor options, operating
  system, compiler or concurrency. Classical concurrency is often unspecified.
  Unknown-clock scenarios can hide real clock differences.
- Repeated rows remain points, including compiler differences. Model medians
  prevent heavily submitted machines dominating total fit weight. The result
  still reflects a small, related, source-biased hardware population.
- A fixed factor assumes slope one. The known-clock Dhrystone 2.1 peak free
  log-log slope diagnostic is approximately 0.697; Whetstone native peak is
  approximately 0.540. Narrow coverage and selection limit their interpretation,
  but neither supports assuming a universal factor over many decades.

## Source and parser checks

Source provenance and immutable hashes are in
[acquisition.csv](data/classic/acquisition.csv); original classical/SPEC IDs
and source URLs are retained in the derived pair CSV. Dhrystone values come
from [Netlib's compilation](http://www.netlib.org/performance/html/dhrystone.data.col0.html);
Whetstone historical rows come from
[Longbottom](http://www.roylongbottom.org.uk/whetstone.htm).
The overlap command owns extraction and source-layout tests.

The [Netlib LINPACK report](http://www.netlib.org/benchmark/performance.pdf),
physical page 32, was visually checked for this fitting pass: DEC 3000-900
has **52** MFLOPS in n=100, **193** in n=1000 and **275** theoretical peak.
The Convex SPP-1000 15-processor row has a blank n=100 cell and must remain
missing. Regression tests cover both. All 19 SPEC92-matched LINPACK machine
lines were inspected against their preserved fixed-width text; wrapped rows
remain outside the partial parser. The conflicting J200 compiler scores
(38 and 5.5 MFLOPS) are both retained.

## Reproduction and plots

```sh
uv run cpushowspeed classic overlap-spec
uv run cpushowspeed classic fit-spec92
```

Acquired sources and existing SPEC92 input datasets must already be present.
The first command regenerates records and LINPACK layout text; the second
writes base/peak scatterplots as PNG and SVG alongside statistics. Blue is
known clocks; orange additionally allows unknown clocks; gray crosses are
numeric excluded pairs. Shading represents conditional factor CI95, not
prediction error. No line is drawn with fewer than two model groups.

[Statistical definitions](../docs/methods.md#classical-workload-association-diagnostics)
and [CLI/output contract](../docs/classic-collection.md#exploratory-score-fitting)
own the reusable method and command documentation.
