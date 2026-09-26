# SPEC89–CPU92 source-paired scatter
> Archived speed-era research, retained for its source-checked observations.
> Its fitting and plotting commands are retired; it is excluded from the active rate analysis.
> Present-tense descriptions below refer to the original 2026-09-26 research snapshot.

Plotted and reviewed on 2026-09-26 from the versioned
[SPEC89 recovery snapshot](data/spec89/v2.0.0/README.md). Rebuild with:

```sh
./.venv/bin/cpushowspeed plot spec89-92
```

The command verifies the snapshot first, then writes PNG and SVG figures plus
`data/derived/figures/spec89-cpu92-bridge-records.csv`. The CSV retains every
bridge ID, reported score, source ID, URL, page/table citation, partial source
date, and saved-message location. These generated files stay outside Git.

The [bridge table](data/spec89/v2.0.0/csv/bridges89_92.csv) has 34 source-paired
rows. The left panel plots all 17 rows that explicitly report both `SPECint89`
and `SPECint92`; nine are marked development-level. The right panel plots the
other 17 rows, whose 1989 value is `SPECmark89`, **not** `SPECint89`. Both
panels retain republications and multiple source observations. A `×N` label
means N rows share plotted coordinates; it does not by itself establish that
they were separate benchmark runs or copies of one run. No regression or
universal conversion factor is fitted.

The directly comparable *reported integer-score pairs* have
`SPECint92 / SPECint89` from about 0.893 to 1.056 among 15 distinct literal
system-and-score vectors; their geometric mean is about 0.960. The 17 source
rows include nine development-level IBM entries and two same-score vectors
republished in other sources. The current sample supports `SPECint92` as a
practical statistical backbone, while its source concentration and incomplete
configuration detail leave an 89-to-92 conversion provisional. These are
different benchmark workloads despite the common VAX reference convention. In
the original
[*Microprocessor Report* comparison](https://www.cecs.uci.edu/~papers/mpr/MPR/ARTICLES/061203.pdf),
PDF page 3, Table 1, the author explicitly presents SPEC89 and SPEC92 scores
side by side and discusses why their performance ratings differ. We checked
the IBM 220 values `SPECint89 = 17.5` and `SPECint92 = 15.9` against the
[saved 1992-05-22 Usenet message](data/spec89/v2.0.0/sources/ibm_89_92_bridge_1992-05-22.txt),
lines 34–42, and the plotted CSV row `B021`. This spot check does not newly
verify all external PDF tables in the consolidated package.

Use this figure to inspect the sparse bridge evidence and source dependence.
Before converting the full SPEC89 series, grade the run configurations,
republication groups, development systems, and missing original reports.
The `SPECmark89` panel remains a separate composite-metric study.
