# Three-benchmark intersection and clock normalization

Review date: 2026-09-26. This audit tests the feasibility of fitting a weighted
geometric mean of Dhrystone **1.1 DMIPS**, Whetstone **native or DP MWIPS**,
and LINPACK **n=100 MFLOPS** against separate SPEC targets. It does not pool
SPEC89 aggregate scores with SPEC92 integer rate or update the VAXen chain.

## Actual intersection

Each entry below counts **different normalized machine models**, not the
Cartesian product of source measurements. Native and DP produce the same
counts in this snapshot.

| Target | All clocks known and compatible | Unknown clocks allowed, conflicts rejected | Dhrystone/Whetstone linear clock sensitivity |
| --- | ---: | ---: | ---: |
| SPECmark89 | 0 | 1 | 2 |
| SPECint89 | 0 | 0 | 0 |
| SPECfp89 | 0 | 0 | 0 |
| SPECrate_base_int92 | 0 | 1 | 2 |
| SPECrate_int92 peak | 0 | 4 | 5 |

The four unscaled peak candidates are DEC 2000/300, 3000/600, 3000/800 and
4000/710. They provide five SPEC records and eleven classical-score tuples
per Whetstone variant. Clock scaling additionally admits DEC 7000/610:
eight SPEC records and fourteen tuples across five model groups. This is a
small, entirely DEC cohort, with related Alpha systems and shared compilers
and source compilations; five models are not five unrelated architectures.

The SPECmark89 candidates are DEC 3000/400 and, with scaling, DEC 7000/610.
VAX-11/780 reference-definition records are preserved but are not counted as
independent measured calibration observations. Dhrystone 2.1 cannot fill a
missing Dhrystone 1.1 field. Repeated submissions remain in the vectors.

## Why a clock-scaling scenario is reasonable

For otherwise equivalent implementations, the candidate model is
`adjusted_score = reported_score × target_MHz / reported_MHz`. It assumes
approximately constant work per CPU cycle. Small cache-resident workloads
make this a useful hypothesis; cache residency alone does not prove it.
[Netlib's Dhrystone introduction](https://netlib.org/performance/html/dhrystone.intro.html)
notes its small code footprint and compiler sensitivity, particularly v1.
This hypothesis is not extended to unspecified early hardware without cache,
different CPU/FPU implementations, or arbitrary cache/compiler changes.

For example DEC 7000/610 Dhrystone 1.1 reports **177.3 DMIPS at 182 MHz**;
normalizing it to 200 MHz gives **194.835 DMIPS**, an estimate, while retaining
177.3 as the reported measurement. The corresponding Whetstone source says
200 MHz. Original records, URLs and locators appear in `vectors.csv`.

The sensitivity scenario chooses the target frequency in this order: reported
SPEC MHz, reported LINPACK MHz, Whetstone MHz, Dhrystone MHz. It requires known
Dhrystone and Whetstone clocks, and adjusts those two scores only. LINPACK and
SPEC are never clock-scaled here; a known clock conflict between them still
rejects the tuple. Unknown LINPACK/SPEC clocks remain unresolved assumptions,
even if another source supplies the normalization frequency. Same model keys
do not verify identical CPU/cache/FPU configurations.

## Fitting decision

The proposed model is
`y = k × (D / D0)^wD × (W / W0)^wW × (L / L0)^wL`, with nonnegative weights
summing to one and fixed, declared unit normalizers D0/W0/L0. With a fitted
intercept k this has three free parameters. Four or five related model groups
can produce an algebraic solution, but cannot establish transferable weights
across historical architectures. Leaving one model out leaves only three or
four groups to learn those parameters; duplicates do not fix this problem.

**No optimized weights are published.** The subsequent
[equal-weight held-out comparison](classic-composite-fitting.md) fixes all three
weights and fits only k, using matched single-benchmark baselines. That test is
implemented; it remains a small-cohort diagnostic. The subsequent [two-family study](classic-pair-fitting.md) implements pair
intersections with Dhrystone versions kept separate.

## Reproduction and evidence

```sh
uv run cpushowspeed classic composite-overlap
```

See [summary CSV](data/classic/composite-summary.csv) and
[audit hashes](data/classic/composite-audit.json). Full outputs are
`data/derived/classic/composite-overlap/{coverage,vectors,summary}.csv` and
`audit.json`. Coverage includes incomplete vectors. Vectors preserve every
combination of distinct classical source records per SPEC record, original
scores, adjusted scores, multipliers, normalization-clock source, known-clock
conflicts, processor exclusions, reference definitions and source provenance.
There are 200 tuples across metric variants/targets, not 200 independent
experiments. Exclusion reasons are retained separately for scaled/unscaled
scenarios. Whetstone languages are retained, not silently recoded; the surviving
candidates in this snapshot are Fortran.

The implemented source readers and their limits remain in
[classical collection](../docs/classic-collection.md). SPEC89 throughput is
outside this diagnostic's target list. Source documents are immutable.
