# Cross-generation SPEC entity resolution precedents
> Archived speed-era research, retained for its source-checked observations.
> Its fitting and plotting commands are retired; it is excluded from the active rate analysis.
> Present-tense descriptions below refer to the original 2026-09-26 research snapshot.

Reviewed on 2026-09-26. This note informs the next matching pass for the
CPU92–CPU2026 fitting audit (retired output). It describes
published methods and a read-only probe of our cached results. It does not
assert that processor-level candidate pairs are the same benchmark system.

## What prior work actually specifies

- [Danowitz et al., *CPU DB: Recording Microprocessor History* (2012),
  methodology, PDF page 3](https://web.engr.oregonstate.edu/~mjb/cs475/CPU-DB.pdf):
  find systems with results under two SPEC versions and take the geometric
  mean of paired score ratios. The paper describes the calibration step but
  does not provide a reproducible fuzzy-name acceptance rule in that passage.
- [Leiserson et al., *There's Plenty of Room at the Top* (2020), Figure 2
  Methods, PDF page 6](https://www.microsoft.com/en-us/research/wp-content/uploads/2020/11/Leiserson-et-al-Theres-plenty-of-room-at-the-top.pdf):
  select a best score per processor and scale consecutive SPECint versions by
  geometric-mean ratios from processors evaluated in both suites. The paper
  specifies the processor-level overlap, not a full system-name equality
  requirement; the cited methods do not spell out a fuzzy-string threshold.
- [Furman, *iLORE: Discovering a Lineage of Microprocessors* (2021), §§3.4–3.5,
  PDF pages 50–62](https://vtechworks.lib.vt.edu/items/be77705e-b48e-40dd-8245-c88c694d3855):
  canonicalize field aliases and units, parse cache/cores/threads from prose,
  remove boilerplate, then resolve benchmark entries to canonical processor
  records. The author notes aliases such as Alpha `21264A` versus `EV67`,
  enabled versus available cores, clock precision differences, ambiguous old
  Pentium/Xeon/Opteron names, and submitted-data mistakes. A token-based
  autocompleter worked best for unique SKUs; an attempted `dedupe` machine
  learning matcher was abandoned as insufficiently accurate. About 1,500
  unique processor tuples covered 95% of benchmark records, so automatic
  guesses were manually reviewed; unresolved entries became explicitly
  incomplete processor stubs. Their overlap set uses the same processor in
  consecutive suites, base integer speed scores, geometric-mean ratios, and
  5-by-5-fold shuffled validation. The thesis also tests regressions using
  original score, threads per core, and core count.
- [*Progress of Computing*, §2.2 and Appendix B,
  PDF pages 5 and 29](https://api.repository.cam.ac.uk/server/api/core/bitstreams/ed2977b5-677d-4002-b7c8-eab877125aad/content):
  uses cross-suite reference systems and collapses submissions by processor,
  availability date, clock, chip count, and core count for a chip-date trend.
  This is a different analysis unit from this project's submitted-system
  distribution. Its appendix explicitly notes that SPEC scores belong to
  full systems with memory, OS, and compiler conditions.

These papers support **processor identity as a candidate-generation layer**.
They do not establish that every same-processor result is a same-configuration
bridge. SPEC's [CPU95→CPU2000 retirement requirement](https://www.spec.org/cpu95/cpu95retirement),
[CPU2000→CPU2006 requirement](https://www.spec.org/cpu2000/), and
[CPU2017→CPU2026 requirement](https://www.spec.org/cpu2017/) deliberately
produce same-configuration dual submissions. Their transition windows,
sponsors, and disclosures can help prioritize candidates even when system
names differ.

## Probe of our current cache

The retired offline matching probe produced the
processor overlap counts (retired output) from
the cached SPEC sources. It groups the same parsed result records used by the
fitting audit by normalized processor key. It then checked clock within 1%,
chip count, and core/SMT counts where available, while *ignoring system name*.
It does not verify per-benchmark requested threads, OS, compiler, cache, or
motherboard. Counts are **candidate pairings**, not unique machines or accepted
conversion evidence. CPU92 memory is not yet parsed in this export. The tracked CSV records input
manifest hashes and the probe method version.

| Adjacent suites | Existing fitting candidate pairings | Shared processor keys | Processor-only pairings | Same CPU + clock/chips/core/SMT pairings | Plus same parsed memory |
| --- | ---: | ---: | ---: | ---: | ---: |
| CPU92–CPU95 | 13 reviewed | 19 | 2,115 | 394 | unknown |
| CPU95–CPU2000 | 29 | 13 | 2,438 | 181 | 78 |
| CPU2000–CPU2006 | 47 | 65 | 3,753 | 1,591 | 831 |
| CPU2006–CPU2017 | 855 | 66 | 33,165 | 17,657 | 8,624 |
| CPU2017–CPU2026 | 70 | 32 | 1,266 | 420 | 220 |

Three processor keys occur in three suites: `21164`, `UltraSPARC II`, and
`UltraSPARC III`. This does **not** overturn the finding that no *same-system
configuration* triangle was found. For example, the 296 MHz, two-chip
UltraSPARC II candidate has a [CPU95 Ultra 60](https://www.spec.org/cpu95/results/res98q1/cpu95-980127-02363.html)
with 512 MB, while its [CPU2000 Ultra Enterprise 2](https://www.spec.org/cpu2000/results/res2006q2/cpu2000-20060612-06193.html)
and [CPU2006 Ultra Enterprise 2](https://www.spec.org/cpu2006/results/res2006q3/cpu2006-20060513-00001.html)
report 2 GB. The first leg changes system and memory; it cannot be accepted as
an equal-hardware three-suite cycle without an explicitly weaker analysis
track. The other two processor keys do not retain the same clock across all
three suites in the current cache.

## First source-linked alias and review pass

The alias registry (retired output) now maps 12 exact
`(generation, raw_processor)` strings to six canonical processor model IDs.
Each row identifies an official bulk-export row by its linked disclosure
URL; the literal processor string was checked in the hash-verified bulk
export.
This is a **processor identity** decision only; a canonical ID does not imply
identical memory, board, firmware, OS, compiler, or benchmark configuration.
The registry is deliberately small: an unlisted spelling is unresolved, even
if the current bulk parser happens to normalize it to the same key. In
particular, the existing generic key conflates some `UltraSPARC IIi` and
`UltraSPARC III` strings, so those are not aliased to each other.

The pair-review register (retired output) uses source URLs
as row identities. Its six initial decisions are one accepted CPU92/CPU95 pair
already checked in the [older audit](cpu92-cpu95-bridge.md), one
`processor_level_only` CPU95/CPU2000 Ultra 60 versus Ultra Enterprise 2 pair (512 versus 2048 MiB),
and four pairs requiring detailed disclosure review. The CPU2006/CPU2017
Cisco-versus-ASUS and CPU2017/CPU2026 ASUS-versus-Fujitsu examples are
explicitly processor-overlap leads, not same-system evidence. The remaining
two same-label candidates still require detailed hardware and software review.
All decisions are dated `2026-09-26`.

The retired `cpushowspeed bridge review-queue` command validated both tracked CSVs against
the cached, hash-checked source records and write the generated queue to
`data/derived/spec/fitting/alias-review-queue.csv` (ignored by Git). It joins
only listed aliases in adjacent suites, then requires equal chip counts and
clocks within 1%. The output retains both source URLs, full system names,
clock, cores, threads per core, memory, OS, base scores, hardware clues, and
any review decision. This first run produced 848 candidate pairings: 1
accepted, 1 processor-level only, 4 awaiting detail review, and 842
unreviewed. These counts reflect repeated submission pairings, not independent processor or
hardware configurations. The alias sensitivity rerun (retired output)
uses these candidates in separately labeled exploratory fits. It does not change the original
factor table or promote unreviewed pairs to accepted same-hardware evidence.

## Proposed matching levels

1. Create an evidence-backed processor identity table: canonical vendor,
   family, exact SKU/revision, codename aliases, and the raw aliases seen in
   each result. Preserve suffixes such as `M`, `F`, or `v4`; do not equate a
   generic family label with a specific SKU.
2. Generate candidates by canonical processor first, then constrain clock
   within disclosed precision, chips, enabled cores and SMT, and metric/run
   mode. Use brand/model-name similarity, publication proximity, SPEC's dual
   submission windows, sponsor/license, memory/cache and source notes to rank
   candidates for review. Fuzzy text scores propose candidates only.
3. Keep separate decisions for **same processor**, **same hardware
   configuration**, and **same measurement conditions**. A processor-level
   bridge can be studied with extra variance and covariates; it must not be
   silently promoted to an exact system bridge. Record each decision and
   source URLs in a review CSV; leave ambiguous labels unmatched.
4. Validate factor generalization by holding out whole processor models or
   families, not random submission pairs. Retain every submission in the
   evidence table, but keep correlated submissions from multiplying the
   effective fitting sample size. Re-run the five adjacent fits and the
   nonadjacent/three-suite search separately for each accepted matching tier.

Our [data contract](../docs/data-contract.md) preserves partial date precision.
iLORE's practice of assigning a month or quarter to its first day should not
be copied into this project's source-date fields.
