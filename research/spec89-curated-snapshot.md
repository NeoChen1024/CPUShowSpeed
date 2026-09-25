# Curated SPEC89 recovery snapshot

Reviewed as a package and compared with local CPU92 disclosures on 2026-09-26.
The [versioned dataset](data/spec89/v2.0.0/README.md) is a curated copy of the
user-provided consolidated research package. The package checksum manifest
passed; the integrated `cpushowspeed spec89 verify` command reconstructed all
25 CSV tables and `summary.json` byte-for-byte and rechecked the 37 saved
message hashes. The original package also records a successful re-extraction
from MBOX ZIPs, but those ZIPs are not included here, so that one check was
not rerun. Internal consistency does not independently authenticate every
score against its original external publication.

The [aggregate table](data/spec89/v2.0.0/csv/aggregate89.csv) contains 381
source-observation rows, with 142 reported `SPECint89` values. It includes
reference definitions, development and beta systems, a quarantined possible
CPU-time approximation, and potentially repeated reports. These categories
must remain visible when forming a historical performance series.

## Existing CPU89–CPU92 evidence

The [bridge table](data/spec89/v2.0.0/csv/bridges89_92.csv) has 34 cited
same-source rows. Seventeen give both `SPECint89` and `SPECint92`; the other
seventeen give `SPECmark89` and CPU92 scores without a reported integer-only
CPU89 value. The direct integer rows reduce to 15 distinct literal
system-and-score vectors after recognizing two repeated IBM vectors. Nine of
the 17 direct rows are marked development-level in the source package; the
native-labeled copies of two IBM vectors do not establish independent runs.
Across the 15 distinct direct integer vectors, the *reported*
`SPECint92 / SPECint89` ratios range from about 0.893 to 1.056. This range is
an input-data description, not a validated universal conversion.

An exact normalized system-name **and** equal `SPECint92` score join between
the 34 bridge rows and our current 300 Netlib CINT92 detailed reports found
zero matches. This does not mean the machine families never overlap: names
change and Netlib's cached disclosures begin in 1993, while many bridge rows
cite 1992 material. Candidate model families must be checked at the
configuration level. For example, bridge row `B012` cites the
[DEC Alpha server comparison](https://web-docs.gsi.de/~kraemer/COLLECTION/DEC/alpha-axp-server.pdf),
PDF page 3, Table 1, for `DEC 7000/610 AXP` with a 182 MHz 21064;
Netlib's [DEC 7000 Model 610 disclosure](https://www.netlib.org/performance/html/spec.deoi761.cint92.12_93.notes.html)
reports a 200 MHz 21064. The shared model family does not make these the
same tested setup. The IBM 220 development-level bridge (`B021`) and later
Netlib M20/220 similarly require OS, compiler, memory, and tuning review.

The next bridge analysis should retain all source observations, identify
republications and correlated tests, and grade configuration overlap before
estimating a SPECint89-to-SPECint92 factor. `SPECmark89`-only rows belong in a
separate bridge study; they cannot be silently treated as `SPECint89`.
