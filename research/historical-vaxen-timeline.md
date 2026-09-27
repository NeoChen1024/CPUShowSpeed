# Classical and SPEC89 historical VAXen timeline

Reviewed: 2026-09-27. Status: implemented exploratory aggregation; hardware dating
remains incomplete. This is the primary document for the combined historical plot.

## Reproduce

```sh
uv run cpushowspeed classic historical-timeline
```

Requires the existing classical overlap records, source vectors, LINPACK text,
SPEC89 bridge estimates, SPEC92/SPEC95 availability records and the verified
`classic network-fit` prediction bundle. It performs no downloads or refitting.
The output directory defaults to `data/derived/classic/historical-timeline/`.

- `historical-vaxen.png` / `.svg`: large logarithmic timeline, with unresolved
  years retained in a separate panel on the same vertical scale.
- `historical-vaxen.html`: offline searchable plot and table; hover identifies
  source configuration, input scores, dating method and calibration CI95.
- `configurations.csv`: one aggregated classical source/configuration or one
  SPEC89 source submission per row; estimated values and dating fields.
- `observations.csv`: all contributing score observations, source IDs, locators
  and provenance, including repeated measurements.
- `date-evidence.csv`: model-year evidence candidates, original date precision,
  source URL, locator, interpretation and priority.
- `undated.csv`: explicit year-review queue; these results remain in the output.
- `audit.json`: counts, exclusions, complete input hashes and local code hashes.

Large outputs remain ignored. The small, reviewed dating rules are versioned in
[data/historical/timeline-year-overrides.csv](data/historical/timeline-year-overrides.csv).

## Aggregation and numerical meaning

Use original positive Dhrystone 1.1/2.1 DMIPS, Whetstone native/SP/DP MWIPS and
LINPACK n=100 MFLOPS. Do not reuse synthetic fitting pairings as new observations.
A classical grouping key includes source, exact system name, reported clock,
processor, OS, configuration, language and optimization. Unknown clocks retain
separate source rows. Different sources are not silently declared identical.
Repeated scores within that key use their median in log space; every contributing
observation is retained. DEC reviewed table columns already contain multiple
benchmarks measured under one source-specific configuration.

Predict using the existing `linear_clock / with_spec89` coefficients, equal
available benchmark-family weights and equal supplied variants within each
family. Supplied scores are not additionally clock-scaled. Explicit multiple-
processor classical configurations are outside this one-processor calibration
scope; the audit counts them separately. Unknown counts remain qualified. Rows
without interpreted supported metrics are not converted by guessing columns.

Each SPEC89 integer submission retains its existing two-edge estimate and interval:
`SPECint89 -> SPECint92 -> rate-VAXen`. It is not pooled with a classical record
merely because names match. Both routes are estimates of equivalent SPEC92
integer rate, and reuse calibration evidence; agreement is not independent
validation. See [network fitting](classic-network-fitting.md),
[prediction contract](../docs/classical-prediction.md), and
[SPEC89 track](tracks/spec89.md).

CI95 describes conditional calibration uncertainty, not the prediction error for
an individual historical machine. It excludes benchmark mismatch, unknown
compilers/configurations, timing approximations and date uncertainty. No score
is discarded for a large residual. The chart labels annual maxima only as
navigation aids; all eligible records remain plotted. White label boxes use
colored arrows to the exact observations, whose rings are emphasized. Labels
include the year and full wrapped system name; placement avoids other labels
and highlighted points where possible.

## Dating policy

All current plotted dates are **estimates/proxies for the measured configuration**.
Even a documented model introduction does not establish when a later clock,
FPU option, memory configuration or software combination became available.

1. Explicit reviewed overrides resolve identified conflicts. Optional family
   fallbacks apply only when a model match supplies no year.
2. Selected [reviewed hardware date events](hardware-year-evidence.md) take
   priority over bulk catalogs. Existing curated SPEC89 model dates take priority over bulk approximate years.
3. Longbottom's Whetstone table explicitly defines `Intr Date` as approximate
   first delivery. The source mix tables also contribute model-year evidence,
   but their KIPS scores are not converted by this tool. SPEC92/SPEC95 hardware
   availability fields provide dates for configurations of the matched model.
4. Longbottom's MIPS catalog `Year` is a catalog-year proxy, not verified first
   shipment. It is used only below the preceding evidence priorities.
5. Model matching normalizes existing aliases, the `DEC Alpha` prefix, parenthetic
   configuration text and clock-corroborated suffixes. A match identifies a model
   era, not full configuration equivalence. Prefer same-clock date evidence when
   available at the selected priority.
6. For conflicting years at the same priority, plot the integer-truncated median
   of distinct years and retain the full min/max evidence span. This span is not
   a confidence interval or a guaranteed bound on the actual configuration date.
7. For still-unknown configurations, reviewed CPU-release mappings can provide
   a CPU-era proxy. These are keyed by configuration ID and checked against the
   original system name, CPU field and clock, so differently equipped machines
   sharing a name cannot inherit one another's dates. Existing model dates and
   explicit unresolved conflicts take precedence.
8. Publication/retrieval dates are never substituted for introduction. With no
   defensible year evidence or family proxy, the year remains unknown.

Source corrections include Argus 700G's impossible 1963 entry: the Argus 700
family launch is reported in *Computer Weekly*, 1973-06-14, p.12, via
[TNMOC](https://www.tnmoc.org/notes-from-the-museum/2023/6/1/fifty-years-ago-from-the-pages-of-computer-weekly).
The 700G date is consequently a **1973 family proxy**, not a verified G-model date.
The [Elliott 903 museum record](https://www.computinghistory.org.uk/det/32480/Elliott-903/)
provides 1965 as a family proxy for 903C. Elliott 905 remains unresolved rather
than inheriting the conflicting 1963 table entry.

The [DEC 12-bit timeline](https://archive.computerhistory.org/resources/text/DEC/dec.digital_%28DEC%29_timeline_1957-1997.102630354/12-bit.htm)
provides PDP-8/I (1968) and PDP-8/E (1970) model introductions; the
[16-bit timeline](https://archive.computerhistory.org/resources/text/DEC/dec.digital_%28DEC%29_timeline_1957-1997.102630354/16-bit.htm)
provides PDP-11/10 (1972). Options may be later. DEC Alpha family and explicit
Intel Pentium family fallbacks are separately cited in the rule CSV.

## Current run and validation

The current run contains **1,711 rows**: **1,532 classical configurations/source
rows** and **179 SPEC89 submissions**, supported by **2,665 score observations**.
**1,291 rows** have model/CPU-era estimates spanning **1963–2006**; **420 remain
undated**. Counts are not counts of distinct physical machines. The earliest
plotted years are inherited approximate source dates, not newly verified exact
configuration launches. Extensive undated modern LINPACK records are retained,
so the dated range is not the full age range of the benchmark corpus.

A source-text reconstruction rejoins wrapped LINPACK machine names while keeping
the original numeric row/locator unchanged. Checks cover HP ProLiant BL20p G3 on
physical PDF page 7 and DEC 500/400 on page 24, including compiler-only `ev5`
continuations and explicit processor counts. This is a derived display/identity
repair; raw sources and prior calibration are unchanged. Some missing or ambiguous
source identities still need review.

Tests also cover repeated-score retention, OS/clock separation, dating conflicts,
review overrides and missing dates. The PNG was visually inspected. Interactive
browser preview was blocked by the browser's local-file URL policy; HTML is
provided but browser interaction was not verified in this run.

The [unknown-year expansion](hardware-year-evidence.md#unknown-year-expansion--2026-09-27)
adds dates to 191 rows. All 1,711 input-score, VAXen, CI95 and observation-count
records were compared with the preceding run and remain unchanged.

The subsequent [Wikipedia and museum pass](hardware-year-evidence.md#wikipedia-and-museum-continuation--2026-09-27)
adds 105 further dated rows using 78 new events. Previously dated years and all
1,711 numerical result records remain unchanged.

The [CPU-release fallback](hardware-year-evidence.md#x86-cpu-release-fallback--2026-09-27)
adds 99 further rows. Its method is `reviewed_cpu_release_year_proxy`, explicitly
distinct from a system launch. CPU events also appear in `date-evidence.csv` with
a configuration ID and `fallback_only` priority. Equal low/high years indicate
one adopted CPU-year estimate, not certainty about the complete configuration.
