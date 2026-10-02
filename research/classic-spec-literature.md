# Additional classical/SPEC sources and prior work

Review date: 2026-09-26. This source/method review led to the completed
[three-source table extraction](classic-pdf-extraction.md). The source tables are preserved separately; reviewed DEC values now feed the
[direct rate experiment](classic-composite-fitting.md). A machine-readable source register is
[data/classic/literature-sources.jsonl](data/classic/literature-sources.jsonl).

## Direct modern comparison: Tomari and Hiraki (2011)

[Retrospective Study of Performance and Power Consumption of Computer Systems](https://doi.org/10.2197/ipsjtrans.4.217),
IPSJ Online Transactions 4, 217–227, studies 70 systems from 1989–2011.
Section 2.3 specifies C Dhrystone 2.1. Section 3.2 reports correlation 0.986
between Dhrystone and CINT2006; compiler/string-library effects explain notable
deviations. The CPU2006 subset is limited by available memory. Appendix Tables
1–2 contain hardware, OS/compiler and performance records. Full PDF text was
read and physical page 9 (printed 225) visually inspected.

This is both a new result source and a direct prior comparison. It supports
investigating Dhrystone against later SPEC without forcing every path through
SPEC89/92. It does not establish our integer-rate conversion: Dhrystone is
single-threaded and the paper's CINT2006 results must not be relabelled as
SPECrate. Correlation is not held-out prediction accuracy.

## Direct historical tables

### DEC EC-N3909-10, version 3.0 (1994-12)

[Alpha and VAX Comparison based on Industry-standard Benchmark Results](https://vtda.org/docs/computing/DEC/VAX/EC-N3909-10_AlphaVAXComparison_Dec94.pdf).
Section 5 explicitly covers LINPACK 100x100; Section 7 provides a broad
manufacturer benchmark summary including SPEC92 and Whetstone. This is a
high-priority source for joint observations and configuration details.
Check actual rate versus speed rows, Whetstone units/precision, OS columns,
and shared lineage with existing DEC/Longbottom/Netlib reports before merging.
Selected tables have now been extracted and their pages visually inspected;
see the extraction audit for remaining unit questions.

### SSCL-375 (1991-09)

[Benchmarks for the SSCL Physics Detector Simulation Computing Facility](https://lss.fnal.gov/archive/other/ssc/sscl-375.pdf).
Table 2 (physical page 11, printed 5) juxtaposes MIPS, DP MFLOPS, SPECmarks and
physics-workload ratings for twelve systems across DEC, SGI, IBM, Sun and
HP/Apollo. Appendix A supplies configuration/compiler detail; Appendix D adds
clocks/caches. This could reduce our DEC-only selection.

Important: Appendix B describes the industry LINPACK rating as usually n=100,
but the report also runs n=300 precision comparisons; Appendix C's VAX result
explicitly uses n=300. Do not assign every MFLOPS entry to n=100. Manufacturer
ratings and authors' own measurements must retain distinct provenance. Selected tables have now been extracted and their original page images
inspected; see the extraction audit.

## Broader conversion precedent: Lopez and Hilbert (2012)

[Methodological and Statistical Background on The World's Technological
Capacity to Store, Communicate and Compute Information](https://www.martinhilbert.net/LopezHilbertSupportAppendix2012.pdf),
Section E.1.3, discusses Dhrystone version harmonization and SPECint89/2000
conversion assumptions. This is an explicit historical synthesis precedent,
but its chained assumptions are not an independent validation dataset or a
replacement for our measured overlap/error analysis. Trace each cited input
before adopting any factor; do not import their estimates as reported scores.

## Modern Whetstone/SPEC collection infrastructure

[Next Generation of HEP CPU Benchmarks](https://doi.org/10.1051/epjconf/201921408011)
(Giordano, Alef and Michelotto, 2019), and
[CERN's SPEC2017 suite instructions](https://twiki.cern.ch/twiki/bin/view/HEPIX/HEPIXBMKWG-SPEC2017),
describe coordinated execution of Whetstone, HS06, SPEC CPU2017 and other
benchmarks. The suite reports results and machine/run metadata in JSON.
This is a promising source of newer overlap and reproducible collection methods.
HS06 is a SPEC CPU2006 C++ subset, not the official integer-rate aggregate.
Public availability of their complete raw result corpus is not yet verified.
The CERN PDF endpoint encountered a bot check; metadata, indexed section 2.2
and the public run instructions were reviewed, not a complete dataset.

## Existing SPEC-chain precedent and historical discussion

[Danowitz et al., CPU DB (2012)](https://web.engr.oregonstate.edu/~mjb/cs575/CPU-DB.pdf),
physical page 3, explicitly uses geometric means of score ratios from systems
with overlapping SPEC generations. It mentions older MIPS, but the described
overlap method alone does not validate arbitrary DMIPS-to-SPEC conversion.

The [1990 comp.arch Dhrystone/SPEC discussion](https://groups.google.com/g/comp.arch/c/EfYPECBMzAY)
is a contemporary lead, not a validated conversion study. It asks the same
predictive-correlation question and contains warnings about version 1.1/compiler
behavior. Preserve it as provenance/discovery material, not benchmark evidence.

## Follow-up after this extraction round

1. DEC and SSCL extraction is complete for the selected tables; resolve flagged
   units and review same-setup evidence before fitting.
2. Tomari/Hiraki appendix fields are extracted, preserving missing values and
   compiler variants. Evaluate as a separate
   comparison track before any connection to the active rate chain.
3. CERN/HEPiX is retained as an execution-tool lead; no result acquisition is
   scheduled in this round. Do not infer that a documented collector implies a public
   downloadable results archive.
4. Follow Lopez/Hilbert citations for additional source trails and compare their
   assumptions against measured overlap. No evidence reviewed here establishes
   a universal classical-to-modern-SPEC conversion.
