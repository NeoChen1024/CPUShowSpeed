# Research methods

No reconstruction or cross-benchmark conversion has been implemented yet. The
following rules describe what a future method must disclose and validate.

## Instruction-mix reconstruction

Select a named mix and preserve its operation weights. Map each operation to
instructions or software routines on the target machine; cite timing sources
and account for operand, addressing, branch, memory, and precision conditions.
For operation weights `w_i` and corresponding times `t_i`, a simple mix has
`T = sum(w_i * t_i)` and a rate equal to `1 / T` after unit conversion. Record
any architecture adjustment separately rather than hiding it in the raw timing.

Reproduce published mix values on several machines before extrapolating to
machines absent from those tables. Treat unavailable operations and timing
conditions as missing evidence, not as zero-cost operations.

## Cross-benchmark bridges

Build candidate bridges from systems reported under both workloads. Verify
hardware configuration, memory, operating system, run mode, and thread/copy
settings; preserve compiler and tuning differences as covariates. Estimate a
ratio in log space, report the overlap sample and spread, and check prediction
on held-out systems. Multiple submissions for one system must not masquerade as
independent evidence.

Keep the original benchmark scores and the normalized estimate side by side.
Do not use a single reference machine or one ratio as proof of universal
equivalence. The graph or table must disclose approximation and uncertainty.

## Proposed reporting anchor

Use the DEC VAX-11/780 as the reporting reference for a future stitched
performance index, setting its value to `1` by definition **within each
track**. [SPEC's history](https://www.spec.org/spec/30th/osg/) identifies it as
the reference machine for SPEC CPU89; [Henning's historical check](https://open.spec.org/cpu/publications/HowManyVAXesFitInThePalmsOfYourHands-AuthorVersion.pdf)
explains the original SPECmark89 value of 1. This convention follows the
VAX-relative figure in Hennessy and Patterson, cited below. It is a
unitless ratio. For the project-facing display unit, call a value of 1
`1 VAX` and a value of N `N VAXen`; define both as performance relative to
the VAX-11/780 under the stated track and workload. A plot axis may read
`Relative performance (VAXen; VAX-11/780 = 1)`. This name is not an
instruction rate, a physical unit, or an official SPEC metric for later
generations.

For human-readable labels, apply decimal SI magnitude prefixes to the displayed
number: `1k VAXen` means 1,000 VAXen, `2M VAXen` means 2,000,000 VAXen,
and `26m VAX` means 0.026 VAX. Use lowercase `k` for kilo and `m` for
milli; uppercase `M` denotes mega. Formatting and rounding affect labels
only. Store and export the underlying unprefixed numeric ratio with its
track, source metric, and normalization method so scripts never have to parse
a label to recover a value.

Keep integer/general-purpose and floating-point/scientific indices separate.
A value of 1 on each track refers to the VAX under that track's workload and
configuration; it does not equate integer and floating-point performance.
Record the exact VAX reference workload, software, and hardware options used
for each historical bridge. A VAX anchor fixes the display scale but does not
supply missing conversion factors or remove the uncertainty accumulated from
cross-benchmark links. CPU92 speed scores are already VAX-relative under their
own workloads, as documented in the [early SPEC research](../research/spec-early-archives.md).
The initial per-generation plot may show original scores where a defensible
path back to the VAX has not yet been calibrated.

## Published precedents for historical timelines

The following methods were checked against the cited publications on
2026-09-25. They are precedents and validation targets, not conversion factors
already estimated for this project.

- [Danowitz et al., *CPU DB: Recording Microprocessor History* (2012)](https://web.engr.oregonstate.edu/~mjb/cs475/CPU-DB.pdf),
  methodology section, PDF page 3: take systems with scores under two SPEC
  versions, calculate paired new/old ratios, and use their geometric mean as a
  conversion factor toward a SPEC CPU2006-equivalent score. The database also
  preserves raw scores. The paper covers older MIPS and SPEC89–CPU2000 inputs;
  it does not supply a validated CPU2017 or CPU2026 bridge.
- [Leiserson et al., *There's Plenty of Room at the Top* (2020)](https://www.microsoft.com/en-us/research/wp-content/uploads/2020/11/Leiserson-et-al-Theres-plenty-of-room-at-the-top.pdf),
  Figure 2 Methods: use the best recorded SPECint92/95/2000/2006 score for
  each processor and scale consecutive generations by geometric means of
  ratios for processors evaluated on both. Their horizontal dates are
  processor release dates, not SPEC submission dates. Before 1992 they use
  recorded MIPS estimates, joined by setting SPECint92 score 1 equal to
  1 MIPS; this is a weak historical bridge rather than a measured workload
  equivalence. Their [archived data and code](https://zenodo.org/records/3715525)
  provide a reproducibility reference.
- [Hennessy and Patterson, *Computer Architecture: A Quantitative Approach*,
  Figure 1.1](https://maltsystem.ru/images/book/Hennessy.Patterson.Computer%20Architecture.A%20Quantitative%20Approach.4th.pdf)
  plots processor performance relative to the VAX-11/780 and explicitly says
  later SPEC generations are related by scaling factors. The figure does not
  disclose enough matching and uncertainty details to adopt its factors here.
- [Henning, *How Many VAXes Fit in the Palms of Your Hands?* (2021)](https://open.spec.org/cpu/publications/HowManyVAXesFitInThePalmsOfYourHands-AuthorVersion.pdf)
  reruns modified SPECmark89 on one modern Xeon core as a long-span plausibility
  check. The author labels its score an estimate because the modifications
  were not approved by SPEC; it is not an official cross-generation conversion.

For the first annual SPEC figure, use publication year and all distinct,
eligible one-copy integer speed submissions in each year. Keep the selected
metric consistent and deduplicate result IDs and revisions before counting.
Include published multi-processor and multithreaded system-speed results under
the revised scope; retain those settings as data and disclose their effect on
the distribution. Draw one box plot per year for the submitted-score
distribution, and overlay a line with points for the highest eligible submission
in each year. Annotate each year with its submission count and identify the
processor and system behind each maximum. Until the generation bridges are
validated, draw separate per-generation panels; never pool different raw SPEC
scales into one annual box. A year with only one eligible result gets a point
rather than a meaningful box; an incomplete year is marked as provisional.

This box is the distribution of *submitted system configurations*, so popular
processors and vendors with many submissions have more weight; it is not a
distribution of all machines available that year. Later results may exploit
more hardware parallelism than earlier ones; the maximum is a system-speed
frontier rather than an isolated-core trend. The maximum traces the observed
published record and can be moved by one unusually tuned system. Keep the raw scores and disclosures
available for inspection. The box's whiskers are submission spread, not a
confidence interval for the annual maximum or for the cross-generation VAXen
conversion. Show conversion uncertainty separately when available. Leiserson's
best-score-by-processor-release-year curve remains a distinct historical
comparison, with a different date and selection rule.

Keep publication, test, and hardware-release dates separate. Use the published
geometric-mean overlap-ratio method as a baseline bridge, then evaluate paired
ratio spread, outliers, architecture dependence, and held-out prediction error
before considering a global graph fit. A graph fit is a proposed extension,
not a method established by the cited papers. Neither method makes different
SPEC generations directly comparable as raw scores.
