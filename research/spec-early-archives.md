# Locating early SPEC CPU results

Source locations checked on 2026-09-25. This note distinguishes an original
published result, a later compilation, and an electronically available detailed
report; the dates are not interchangeable.

## SPEC Release 1 / CPU89

[SPEC's CPU89 page](https://www.spec.org/cpu89/) states that it has not put the
1989 results online. Reinhold Weicker's 1990 survey, [“An Overview of Common
Benchmarks”](https://users.ece.utexas.edu/~ljohn/teaching/382m-15/reading/weicker.pdf),
identifies “Benchmark Results,” *SPEC Newsletter* volume 1, issue 1, Fall 1989,
pages 1–15 as the first published result list. The first issue itself has not
yet been located as a digitized, inspectable copy in this project.

An accessible later compilation is Kaivalya M. Dixit's [“Overview of the SPEC
Benchmarks,” chapter 9](https://jimgray.azurewebsites.net/benchmarkhandbook/chapter9.pdf),
Appendix B, Table B.1, printed page 516 (PDF page 28). Visual inspection
confirmed separate SPECmark89, SPECint89, and SPECfp89 columns. The table gives
machine scores, but does not give a per-row test date or a link to each original
submission. It should be used as a traceable historical compilation, not
mistaken for the Fall 1989 newsletter. As a page-level check on
2026-09-25, the Compaq 486/50L row reads SPECmark89 `19.3`, SPECint89 `27.6`,
and SPECfp89 `15.2` in that later compilation.

### Usenet recovery leads

Google Groups preserves contemporary discussions and later result compilations.
Reinhold Weicker's [1989-10-30 `comp.arch` post](https://groups.google.com/g/comp.arch/c/3dBUrduLfqk)
explains the original suite and says the quarterly SPEC Newsletter contained
complete per-program results, but the post itself does not reproduce result
pages. SPEC's [online newsletter index](https://www.spec.org/osg/news/) begins
with 1994-09 even though it acknowledges the first Fall 1989 issue. Neither
source fills the missing first-issue scan.

John DiMarco's [1994-01 `comp.benchmarks` SPECmark table](https://groups.google.com/g/comp.benchmarks/c/zvnlKLIgUDk/m/ut4VeY_t0lcJ)
contains a separate SPECmark89 system table with reported date and source
labels, including entries attributed to 1989-10 `comp.arch` posts. DiMarco
explicitly says the numbers were not independently verified and that dates
and sources in the SPEC89 table may be inaccurate. This is a useful machine
and original-post discovery index, not an official SPEC result archive; its
SPEC89 table supplies only the combined SPECmark, not SPECint89/SPECfp89.

A [1993-01-15 `comp.sys.intel` post by Norbert Juffa](https://groups.google.com/g/comp.sys.intel/c/4t50yI9XsQw)
transcribes Intel literature into columns for SPECmark89, SPECint89, and
SPECfp89, with document numbers and some configurations. Its estimated
AMD/Cyrix row is explicitly marked as an estimate, and two rows have ratios
recomputed by the poster because he says the report was wrong. Treat the
post as a source lead and retain those qualifications. A
[1993 `comp.benchmarks` SPEC FAQ](https://groups.google.com/g/comp.benchmarks/c/syb7is_Xpng)
reproduces another DiMarco table and identifies the 1989 suite's separate
integer, floating-point, and combined metrics. It also points to the
1992-12 newsletter summary list at volume 4, issue 4, pages 6–8.

No complete first-issue SPEC89 reporting pages or original 1989-10 Usenet
result post were located in this search on 2026-09-25. The Usenet tables can
help identify systems and citations to pursue, but their publication dates
must not be used as benchmark test dates. Curate numeric rows into the
script-readable dataset once its schema is selected, with a separate source
reference for each underlying result.

A later [curated SPEC89 recovery snapshot](spec89-curated-snapshot.md) now
preserves additional source-linked Usenet observations and 34 CPU89–CPU92
same-source bridge rows. It does not fill the missing first-issue scan or
turn later collector tables into original SPEC submissions.

## Internet Archive check

On 2026-09-25, the Internet Archive Advanced Search metadata catalog returned
no item for `"SPEC Newsletter"`, `SPECint89`, or `SPECmark89`. Its separate
[full-text search for `"SPEC Newsletter" "Fall 1989"`](https://archive.org/search?tab=fulltext&query=%22SPEC+Newsletter%22+%22Fall+1989%22)
returned 23 text items, including papers and books citing the first issue,
but no item visibly identified as the issue itself. These searches cannot
prove that an unindexed or poorly OCRed scan is absent.

The [Wayback URL listing for SPEC's newsletter directory](https://web.archive.org/web/*/http://www.spec.org/osg/news/*)
showed 52 captured URL paths; the earliest issue path visible in that list was
`news9409/` (1994-09), first captured in 1998. This reflects what the SPEC
website had put online and what Wayback captured, not whether a paper copy or
an independent scan survives. The first-issue scan remains an open acquisition
target; title-level and full-text searches should be revisited if new catalog
records appear.

## CPU92

[SPEC's CPU92 page](https://www.spec.org/cpu92/) explains that its paper-era
submission process left no complete official electronic results archive. The
same Dixit chapter's Appendix A, Table A.1, printed page 512 (PDF page 24),
contains visually verified SPECint92 and SPECfp92 columns. The chapter says its
appendix uses recent SPEC newsletter results through December 1992; the table
does not identify an issue or test date for each row. This is an accessible
1992-era compilation, while the underlying newsletter pages still warrant
source-by-source recovery. The [Computer History Museum finding aid for the
Michael Slater collection](https://archive.computerhistory.org/resources/access/text/finding-aids/102733965-Slater/102733965-Slater.pdf)
lists SPEC newsletters dated 1992-03 and 1992-06 in Box 5, catalog item
102773491. This identifies a holding for early original issues, not a verified
digital scan of their result pages. As a page-level check on 2026-09-25, the
Compaq Deskpro/66M row reads SPECint92 `32.2` and SPECfp92 `16.0` in that
compilation. Neither sample row supplies a test date.

The [contemporary SPEC FAQ preserved by Netlib](https://www.netlib.org/performance/html/specfaq.html)
defines each CPU92 speed ratio as the fixed reference time, originally measured
on a VAX-11/780, divided by the tested system's time. `SPECint92` is the
geometric mean of six CINT92 ratios, and `SPECfp92` is the geometric mean of
14 CFP92 ratios. Thus these original speed scores are already VAX-relative
under their respective workloads: a `SPECint92` score of `58.8` can be displayed
as `58.8 VAXen (CINT92)`, without an extra scale factor. A
[contemporary US GAO explanation](https://www.gao.gov/products/b-254497.2,b-254497.3)
independently describes `SPECint92 = 40` as 40 times the VAX-11/780 on this
benchmark. This does not equate SPECint92 with SPECint89, SPECfp92, or later
SPEC generations; their workloads differ even where the reference machine is
the same. CPU92 `SPECrate` uses a different throughput formula and is not a
single-task VAXen score.

The early CPU92 reports use SPECint92/SPECfp92. SPEC's
[historical FAQ](https://www.netlib.org/performance/html/specfaq.html) states
that baseline results became mandatory with the June 1994 newsletter, so a
missing `SPECbase_int92` in a 1992 or 1993 report is expected and must not be
filled with the ordinary SPECint92 value.

Netlib's [Performance Database Server](https://www.netlib.org/performance/html/spec.html)
has issue summaries and linked full disclosures starting with June 1993
(Volume 5, Issue 2). Its own notice says the material previously appeared in
the SPEC Newsletter. It is selected coverage, not proof that 1992 results did
not exist. The local collector found 44 integer/floating-point speed summary
pages and 537 distinct detailed report links; the June 1993 issue links 38
distinct detailed reports. All 537 linked detailed pages were saved locally on
2026-09-25, without claiming that this is the complete history of CPU92.

A first transcription check on 2026-09-25 compared the June 1993
[CINT92 summary](https://www.netlib.org/performance/html/spec.cint92.6_93.col0.html)
with its [IBM POWERserver 970B full report](https://www.netlib.org/performance/html/spec.990b.cint92.6_93.notes.html).
Both state `SPECint92 = 58.8`; the report identifies a 50 MHz POWER processor
and one CPU. The detailed page also says `Tested: Sep-93`, later than its
labeled June 1993 issue; the score transcription is checked, but the
publication chronology requires further investigation. This verifies one
source-to-disclosure link, not the rest of the archive or a CPU92-to-other-suite
conversion. See the [first VAXen figure](spec92-vaxen.md) for the exclusion.

## Next source search

Locate a complete scan of the Fall 1989 volume 1, issue 1 newsletter and the
1992 CPU92 newsletter issues. Check publisher or archive holdings before using
secondary tables as substitutes for their detailed result disclosures. Record
original page numbers, metric names, configuration, and any withdrawal or
compliance notice when transcribing a score.
