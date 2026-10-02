# Classical benchmark / SPEC89-92 hardware overlap

Review date: 2026-09-26; pairing recomputed on resolved systems 2026-10-02
(schema step 5c). Parser method: `classic-hardware-overlap-v2-records-only`.
Pairs are automatic resolved-system candidates, not calibrated scores or
verified equal configurations. The [collection guide](../docs/classic-collection.md#hardware-overlap-discovery)
owns commands and parser/matching semantics.

## Coverage

The run extracted 3,794 records from eight acquired sources. These include
CPU-only rows, instruction-mix listings and unreviewed PDF machine-line
candidates; the count is not independent measurements.

| Reader | Records | Boundary |
| --- | ---: | --- |
| Netlib Dhrystone | 328 | All source row IDs, including repeats and starred scores |
| Longbottom Whetstone history | 504 | Historical supplier section; excludes the differently formatted later PC section |
| Gibson / ADP | 190 each | Includes missing-score listings |
| Later PC Whetstone / Dhrystone / LINPACK / Livermore | 574 / 121 / 158 / 356 | CPU-only labels |
| Netlib LINPACK PDF | 1,373 | Table 1 machine-line candidates; no wrapped-row reconstruction or later tables |

The parser's SPEC side contains 724 records: 421 SPEC89 aggregate observations,
20 SPEC89 throughput archive rows, 274 SPEC92 Netlib rate records and nine
SPEC92 rate manufacturer rows. The Netlib rate records are not extracted from
this parser: the same pages are the `spec:cpu92` results. Reference definitions, estimates and other
original evidence flags remain attached to source records. SPEC89 hardware
discovery does not create a throughput calibration edge.

The [coverage CSV](data/classic/overlap-coverage.csv) lists every acquired
source. Gabriel, NAS, Dhampstone and Sieve results are not yet included in
model counts. Vendor MIPS claims are not treated as executed benchmarks.

## Pairing over resolved systems

`classic overlap-spec` now only parses records. Pairing is done by the fitters
on the built database (`classical_store`): a classical result pairs with a SPEC
target result only when both resolve to the same `system_id`. Reported clocks
are compared (within 1%), and CPU counts and reference definitions are checked;
OS, compiler, cache and FPU options remain unverified. Of 1,727 classical
results in the database, 1,684 resolve to a system.

Each cell is **target systems / pairings** (classical result × target result,
excluding same-result DEC columns). Repeated observations remain separate pairings.

| Benchmark | SPEC89 (aggregate) | CPU92 results (`spec:cpu92`) | DEC N3909 columns | DEC SPEC92 OpenVMS table |
| --- | ---: | ---: | ---: | ---: |
| Dhrystone | 21 / 129 | 24 / 149 | 25 / 80 | 3 / 21 |
| Whetstone | 18 / 40 | 19 / 121 | 19 / 62 | 2 / 9 |
| LINPACK | 27 / 70 | 20 / 94 | 24 / 48 | 3 / 14 |

There are 533 cross-result pairings on 68 systems, 173 classical results and
206 target results, plus 62 same-result DEC columns. Clock checks give 158
compatible within 1%, 32 conflicts and 322 unknown; 21 pairings have a
reference-definition target and are excluded. Conflicts and unknown clocks stay
visible in each fitter's audit. No pairing has been individually reviewed.

The name-based candidate counts of 2026-09-26 (643 pairs on 64 normalized model
keys) are archived in
[`data/archive/name-pairing/`](data/archive/name-pairing/README.md). Name
rules kept `SPARCstation 1` and `1+`, DEC `400` and `400S`, and grouped labels
such as `735/755` distinct; resolved identity keeps them distinct through the
curated system table instead.

No direct Gibson/ADP candidate was found under these inputs and rules.
Intermediary classical workloads remain potential bridge paths. Livermore
currently has only CPU-only parsed rows, so its lack of system candidates is
a coverage limitation rather than a negative research finding.

## Reproducibility and checks

- [Coverage](data/classic/overlap-coverage.csv) and the
  [input/method audit](data/classic/overlap-audit.json) are compact saved outputs.
- Full records are in ignored `data/derived/classic/overlap-spec/`; `data extract`
  reads them into the observation table.
- Regression examples cover decimal clocks/starred scores, supplier/section
  boundaries, PDF Table 1 boundaries and variant distinctions; pairing rules are
  tested in `tests/test_classical_store.py`.
- Dhrystone IDs 001-328 and source/derived hashes were checked. PDF layout
  candidates have not been individually source-reviewed.
- No conversion factors, hardware-year corrections or manual source-row
  exclusions were applied. Score columns remain source-specific.

The pairings were reviewed by model, clock and processor on 2026-10-02; five
`result_pair` reviews resulted ([SPEC89 bridge](spec89-bridge.md#pair-review-and-spelling-merges-2026-10-02)).
FPU/options, concurrency, software and reprint provenance remain unreviewed.
