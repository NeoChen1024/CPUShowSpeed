# SPEC92–SPEC2026 integer-speed fitting audit

Calculated on 2026-09-26 with `cpushowspeed bridge fit-generations` from the
cached Netlib CPU92 details, five official SPEC bulk CSV exports, and the
[13 reviewed CPU92–CPU95 pairs](cpu92-cpu95-reviewed.csv). The
[machine-readable factors](data/spec/fitting/integer-speed-factors.csv) record
both peak and base fits, matching counts, bootstrap intervals, held-out errors,
and input hashes. The
[provisional VAXen chain](data/spec/fitting/integer-speed-vaxen-chain.csv)
marks every conversion as exploratory and unadopted. The generated
[JSON summary](../data/derived/spec/fitting/integer-speed-generation-fit.json),
[all source records](../data/derived/spec/fitting/integer-speed-source-records.csv),
[all candidate pairings](../data/derived/spec/fitting/integer-speed-generation-pairs.csv),
and [base](../data/derived/spec/fitting/integer-speed-base-overlaps.png) and
[peak](../data/derived/spec/fitting/integer-speed-peak-overlaps.png) figures
remain outside Git and can be rebuilt. The CLI uses no network unless earlier
SPEC collection commands are explicitly run.

## Method and interpretation

Only integer **speed** results enter this test. `Result`/`Peak Result` and
`Baseline`/`Base Result` are fitted separately. CPU92 peak is the reported
`SPECint92`; its base series uses the available reviewed `SPECbase_int92`
values. CPU95–CPU2026 bulk file hashes are verified against collection
metadata. CPU92 detail bytes and their independently published issue-summary
scores are verified by the existing collector. The 13 CPU92–CPU95 fitting
pairs were previously checked against individual disclosures. Eight further
bulk scores, covering each later adjacent edge, were checked on 2026-09-26
against their original official HTML disclosures; examples include
[CPU95](https://www.spec.org/cpu95/results/res2000q1/cpu95-20000313-04092.html),
[CPU2000](https://www.spec.org/cpu2000/results/res1999q4/cpu2000-19991130-00013.html),
[CPU2006](https://www.spec.org/cpu2006/results/res2007q1/cpu2006-20070305-00607.html),
[CPU2017](https://www.spec.org/cpu2017/results/res2018q1/cpu2017-20171224-02028.html), and
[CPU2026](https://www.spec.org/cpu2026/results/res2026q3/cpu2026-20260810-00438.html).
The full later-generation paired population has **not** had per-disclosure
manual review.

For CPU95 onward, an automated candidate requires the same normalized system
name, processor model, and chip count. A pair enters the exploratory fit only
when reported clock (within 1%), total memory capacity, and disclosed enabled
core/SMT counts also agree. This is `hardware_near`, **not** proof of identical
OS, compiler, tuning, storage, or benchmark thread settings. Repeated
submissions remain in the candidate CSV. Their log ratios are first reduced
to one median per system, then to one median per processor configuration; each
processor configuration receives equal weight. The factor is the geometric
mean of those configuration ratios:

`factor(old/new) = exp(mean_config(log(score_old / score_new)))`.

The 95% interval bootstraps processor configurations within this selected
cohort. It describes sampling sensitivity, **not** a universal prediction
interval. The held-out error leaves one processor configuration out, estimates
the factor from the rest, and reports the median multiplicative error
`exp(abs(log(observed_ratio / heldout_factor))) - 1`. A free-slope log-log regression is only a diagnostic;
the conversion estimate remains proportional.

## Adjacent-generation results

The table below uses **base** integer-speed scores. All entries are exploratory
except that the underlying CPU92–CPU95 13 source pairs have been reviewed.
`old/new` means one point in the older suite per point in the newer suite.

| Pair | Candidate pairings | Fit pairings | Processor configs | Factor old/new | 95% cluster bootstrap | Held-out median error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CPU92 / CPU95 | 13 | 13 | 9 | 37.79 | 34.95–40.97 | 14.0% |
| CPU95 / CPU2000 | 29 | 16 | 11 | 0.0913 | 0.085–0.098 | 8.2% |
| CPU2000 / CPU2006 | 47 | 41 | 15 | 156.32 | 146.72–164.43 | 9.1% |
| CPU2006 / CPU2017 | 855 | 659 | 114 | 8.573 | 8.493–8.673 | 0.9% |
| CPU2017 / CPU2026 | 70 | 36 | 23 | 2.797 | 2.425–3.253 | 34.6% |

The CPU2006–CPU2017 fit cohort consists entirely of Xeon processor
configurations; its small within-cohort error does not establish an
architecture-independent factor. The CPU2017–CPU2026 cohort spans a much
wider observed base ratio of **1.855–7.176**, with a large held-out error.
A single 2017→2026 factor is especially unsuitable for relabeling every
CPU2026 submission. Requested benchmark thread counts are disclosed in
per-result pages but absent from these bulk matching fields; they have not
been checked for every pair. In the checked
[2017](https://www.spec.org/cpu2017/results/res2025q3/cpu2017-20250804-49325.html)
and [2026](https://www.spec.org/cpu2026/results/res2026q3/cpu2026-20260810-00438.html)
ASUS Xeon 6787P example, both reported 344 threads for the inspected speed
benchmark, which is one spot check rather than cohort-wide validation.

## VAXen chain and absent cycle checks

Using `SPECint92 = 1 VAXen per score point` as the anchor, the chain-only
**base-score diagnostic** yields approximate factors of 37.79, 3.450,
539.35, 4,623.63, and 12,932.12 VAXen per score point for CPU95, CPU2000,
CPU2006, CPU2017, and CPU2026 respectively. The separate peak chain is in the
JSON output. These products compound selection bias and uncertainty across
edges and must not yet become the public timeline's conversion constants.

All nonadjacent pairs were searched under the same conservative machine key.
None had a fit-eligible overlap, and **zero** keys appeared in three
benchmark generations. Therefore the six-generation graph is a chain: it has
no independent triangle or cycle with which to test accumulated scaling.
The graph solver is implemented for future direct edges, and synthetic tests
verify that a consistent three-generation edge closes while an inconsistent
one produces a residual. No such empirical cycle is present in today's data.

The next evidence step is detailed review of matching, run mode, thread counts,
software, and memory descriptions for the later pairs; expansion of the
small CPU92–CPU95, CPU95–CPU2000, and CPU2000–CPU2006 cohorts; and separate
fits by processor family where coverage permits. [SPEC itself warns](https://spec.org/cpu95/qanda)
that no universal CPU92↔CPU95 formula exists. The factors here are calibrated
estimates under selected overlap cohorts, not official equivalences.
