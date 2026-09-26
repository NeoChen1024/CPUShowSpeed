# Classical benchmark / SPEC89-92 hardware overlap: first pass

Review date: 2026-09-26. Method: `classic-hardware-overlap-v1`.
These are model-name candidates, not calibrated scores or verified equal
configurations. The [collection guide](../docs/classic-collection.md#hardware-overlap-discovery)
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

The SPEC side contains 724 records: 421 SPEC89 aggregate observations,
20 SPEC89 throughput archive rows, 274 SPEC92 Netlib rate records and nine
SPEC92 rate manufacturer rows. Reference definitions, estimates and other
original evidence flags remain attached to source records. SPEC89 hardware
discovery does not create a throughput calibration edge.

The [coverage CSV](data/classic/overlap-coverage.csv) lists every acquired
source. Gabriel, NAS, Dhampstone and Sieve results are not yet included in
model counts. Vendor MIPS claims are not treated as executed benchmarks.

## Candidate counts

Each cell is **distinct normalized model groups / candidate row pairs**.
Repeated observations remain separate pairs. Model groups are not necessarily
unique physical configurations or independent experiments.

| Benchmark | SPEC89 aggregate | SPEC89 throughput archive | SPEC92 rate Netlib | SPEC92 rate manufacturer |
| --- | ---: | ---: | ---: | ---: |
| Dhrystone | 23 / 291 | 3 / 9 | 11 / 63 | 3 / 7 |
| Whetstone | 10 / 67 | 2 / 6 | 9 / 18 | 1 / 4 |
| LINPACK | 29 / 139 | 7 / 13 | 16 / 19 | 3 / 7 |
| Gibson Mix | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| ADP Mix | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

There are 643 pairs spanning 64 model keys, 166 classical records and
225 SPEC records. Clock checks give 238 compatible within 1%, 62 conflicts
and 343 unknown. Conflicts remain for review; clock compatibility does not
certify the rest of a configuration. Verified configurations and fitting-eligible
pairs are both zero.

Examples include VAX-11/780, DECstation 3100/5000 variants, DEC Alpha systems,
HP 9000 workstations, IBM RS/6000 models and Sun SPARCstations. These are
discovery examples, not an approved alias list. `SPARCstation 1` and `1+`,
DEC `400` and `400S`, and grouped labels such as `735/755` remain distinct.

No direct Gibson/ADP candidate was found under these inputs and rules.
Intermediary classical workloads remain potential bridge paths. Livermore
currently has only CPU-only parsed rows, so its lack of system candidates is
a coverage limitation rather than a negative research finding.

## Reproducibility and checks

- [Summary](data/classic/overlap-summary.csv), [model groups](data/classic/overlap-models.csv)
  and [input/method audit](data/classic/overlap-audit.json) are compact saved outputs.
- Full records and `candidate-pairs.csv` are in ignored
  `data/derived/classic/overlap-spec/`; pairs retain IDs and both source URLs.
- Regression examples cover decimal clocks/starred scores, supplier/section
  boundaries, PDF Table 1 boundaries, variant distinctions, repeats and conflicts.
- Dhrystone IDs 001-328, source/derived hashes and candidate references were
  checked. PDF layout candidates have not been individually source-reviewed.
- No conversion factors, hardware-year corrections or manual source-row
  exclusions were applied. Score columns remain source-specific.

Next, inspect pairs by model and review disclosed processors, FPU/options,
concurrency, software and reprint provenance before fitting any relationship.
