# Classical and SPEC89 historical VAXen timeline

Reviewed: 2026-09-27. Status: **retired 2026-10-02** (schema step 5d). The
`classic historical-timeline` command and its name-merged configurations were
removed; `plot timeline` now emits one row per classical database result and
takes dates from `result_chronology` (see the [timeline contract](../docs/timeline.md)).
The dating evidence described here was converted into date events. Below is the
2026-09-27 record of the former plot.

## Former reproduction

The former command required the existing classical overlap records, source vectors, LINPACK text,
SPEC89 bridge estimates, SPEC92/SPEC95 availability records and the verified
`classic network-fit` prediction bundle. It performs no downloads or refitting.
The output directory defaults to `data/derived/classic/historical-timeline/`.

- `historical-vaxen.png` / `.svg`: large logarithmic timeline, with unresolved
  years retained in a separate panel on the same vertical scale.
- `configurations.csv`: one aggregated classical source/configuration or one
  SPEC89 source submission per row; estimated values and dating fields.
- `observations.csv`: all contributing score observations, source IDs, locators
  and provenance, including repeated measurements.
- `date-evidence.csv`: model-year evidence candidates, original date precision,
  source URL, locator, interpretation and priority.
- `undated.csv`: explicit year-review queue; these results remain in the output.
- `audit.json`: counts, exclusions, complete input hashes and local code hashes.

Interactive exploration now uses only the [unified timeline](../docs/timeline.md),
generated with `cpushowspeed plot timeline`.

Large outputs remain ignored. The small, reviewed dating rules are versioned in
[timeline-year-overrides.csv](data/archive/legacy-dates/historical/timeline-year-overrides.csv) (archived).

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

The current precedence is **CPU release → hardware model/configuration →
submission-era → unknown**, as defined by the [shared timeline contract](../docs/timeline.md).
The historical generator uses the shared CPU/hardware selector; the combined
adapter can additionally use explicit result-publication metadata. All candidate
dates remain recorded. Earlier CPU-fallback audits below are snapshots of the
preceding rule, not the current priority. Conflict/model overrides remain part
of the hardware candidate calculation, and do not override a reviewed CPU date.

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

## Offline HTML interaction

The list can sort by year in either direction (unknown years always last), by
numeric VAXen in either direction, or by system name. Search retains the selected
sort; sorting does not change plot coordinates or observations.

Hover selects the nearest point center within 12 CSS screen pixels, independently
of SVG scaling and the logarithmic value axis. Its marker is enlarged, brought
above the other points, and ringed; the corresponding uncertainty spans darken.
Spans themselves do not attract selection. Leaving the radius clears the hover.
Click pins the selection. Candidates within 6 screen pixels of the nearest center
and within the 12-pixel cursor radius are available through Previous/Next controls,
including coincident observations. Escape, Close, or an outside click dismisses;
search resets selection. Tooltip placement is clamped to the viewport.

The page remains self-contained with no remote JavaScript dependency. HTML
rendering is owned by the shared `timeline_html.py`. Offline JavaScript tests check
sorting, search, snapping at two SVG scales, overlap cycling, highlighting and
pin/dismissal state. Direct browser verification was blocked by the browser
local-file URL policy on 2026-09-27; actual visual interaction was not verified.

For the shared record schema, mode filters, pagination and time navigation, see
[Shared VAXen timeline](../docs/timeline.md). `plot timeline` also updates this
page's historical HTML entry point from the common records.
