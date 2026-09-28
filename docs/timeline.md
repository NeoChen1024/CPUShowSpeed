# Shared VAXen timeline

Implemented on 2026-09-27. This document owns the combined view's data contract,
date selection and interaction. It consumes saved calibration; it does not fit
a new model. [Research results](../research/unified-vaxen-timeline.md) own the
checked population and numerical comparisons.

## Reproduce

```sh
uv run cpushowspeed classic historical-timeline
uv run cpushowspeed classic mix-network-fit
uv run cpushowspeed plot timeline
```

The first command regenerates the historical input from existing collected
records and the saved classical prediction bundle. The second fits the separate
mix experiment; it can be skipped when its saved inputs and outputs are current.
The timeline command validates the
historical input hashes and modern factor provenance, imports the current
SPEC92–SPEC2026 rate submissions, and applies saved `same_os` rate factors and
pointwise calibration intervals. The timeline command performs no network
collection or fitting.

Outputs under `data/derived/figures/timeline/`:

- `records.jsonl`: canonical shared records, schema `vaxen-timeline-v1`.
- `records.csv`: equivalent flattened export; nested values are JSON cells.
- `vaxen-timeline.html`: combined offline view.
- `audit.json`: population, date/mode/route counts, input and code hashes.

`vaxen-timeline.html` is the sole generated interactive page. Use its route and
mode filters to view historical or SPEC-only subsets. Historical and annual-rate
commands no longer generate separate HTML pages. The page is self-contained;
full provenance remains in JSONL/CSV and the audit metadata. Large outputs stay
outside Git.

The earlier annual-rate PNG/SVG reports and their hardware-year statistical
summaries remain reproducible snapshots. The shared timeline is the new
interactive entry point; it does not silently reinterpret those earlier annual
boxplot cohorts as CPU-year cohorts.

## Shared record contract

Every record has `schema_version`, a unique `record_id`, and its original
`configuration_id`. Modern IDs include generation, source result ID and mode;
base and peak are separate rows. Different submissions are never deduplicated
merely because system, CPU, year or scores agree.

| Fields | Meaning |
| --- | --- |
| `route`, `generation`, `mode` | Source/calibration route and original suite; historical estimates use `peak_proxy`, not an asserted peak measurement |
| `system`, `cpu`, `clock_mhz`, `os`, `configuration` | Source identity; unknown fields remain empty |
| `scores`, `reported_score`, `benchmark_id` | Original input scores; `scores` is an object in JSONL; historical composites have no single reported score |
| `vaxen`, `ci95_low`, `ci95_high` | Existing estimate and conditional calibration interval, without per-core normalization |
| `calibration_route`, `calibration_scenario`, `uncertainty_scope` | How the estimate was obtained and what its interval covers |
| `source_record_ids`, `benchmark_sources`, `source_url` | Original contributors and source links; historical repeated observations remain in their existing aggregation |
| `observation_count`, `evidence_class` | Population meaning and evidence status |
| `measurement_scope`, `chips`, `cores`, `threads_per_core`, `copies_min`, `copies_max`, `nodes` | Distinct reported quantities; unknown counts remain empty, never inferred from one another |
| `date_candidates` | Array of typed CPU, hardware and result-publication chronology evidence, retaining date precision, source, method and notes |
| `year`, `year_low`, `year_high`, `date_kind`, `date_method`, `date_sources`, `date_notes` | Selected display chronology and evidence span; unknown years are empty strings |
| `limitation` | Route-specific caveats, including sparse CPU2026 calibration |

Some source-specific metadata fields are optional. Modern input-container hashes
are retained; historical observations are recoverable from the original
`observations.csv`, included in the unified audit's hashes. No benchmark score is
changed when the date changes.

## CPU-first date selection

Selected research rule, 2026-09-27:

1. Reviewed CPU release year.
2. Hardware model/configuration year if no CPU year is available.
3. Submission-era year if neither is available **and it has not been rejected
   as incompatible with the hardware's approximate era**. Current SPEC exports provide
   result **publication** dates, which are explicitly marked as the proxy;
   these are not claimed to be submission receipt dates.
4. Unknown when none is supported.

Keep every candidate, including the lower-priority hardware and publication
alternatives. Within the selected kind, conflicting years retain their full
range and use the integer-truncated median of distinct years for the display
point. This range is not a statistical CI or a guaranteed configuration bound.
A benchmark test date, article date, OCR date or download date does not silently
become a submission date.

The reviewed CPU mapping is currently limited to the existing 99 configuration
proxies and conservative exact CPU-text/clock matches from them. This establishes
the precedence rule, not complete CPU chronology coverage. Unidentified CPU
variants fall back to hardware/year evidence. Future reviewed entries can extend
the mapping without modifying the scores or fitting.

## Measurement scope and uncertainty

The research target is single-node / documented-system throughput, not single
core. Preserve measured chip, core and copy counts separately. A historical
one-processor calibration proxy does not turn into a newly measured multi-core
result. The historical adapter retains its existing eligibility population;
previously excluded multi-processor classical observations are not synthesized
by this view.

Some SPEC records name clusters. They remain included and source-linked; missing
node counts are not guessed and these rows are not certified as single-node
measurements. No division by cores/chips/copies is performed.

Each route retains its own CI95. CPU92 uses a defined reference scale; later
SPEC modes use the corresponding saved chain interval. Classical and SPEC89
proxies retain their saved intervals, both targeting the peak rate anchor.
They appear when **Historical estimates** is selected, independently of the
**SPEC Base** and **SPEC Peak** selections. All three score checkboxes default on.
Intervals are not pooled across routes or advertised as machine prediction
intervals. CPU2026 remains explicitly exploratory.

## Interaction and testing

- Route checkboxes, score checkboxes and text search select the displayed records.
- Year, VAXen and name sorts affect the list; unknown years stay last in year sorts.
- The list uses pages of 200 records, retaining all eligible records in memory.
- Wheel zoom anchors on the cursor; drag pans; +/- buttons, presets and overview
  range handles provide alternative controls. Only time changes; the log VAXen
  axis stays fixed. Unknown years remain in the list regardless of time window.
- All visible observations contribute marker geometry; batching per route reduces
  DOM elements without aggregating or deleting points. The overview is a navigation
  histogram of yearly record counts for the selected routes/mode/search, across
  the full time extent. Its bar height uses a labelled square-root scale; it is
  not an additional performance metric.
- A screen-space index finds point centers within 12 CSS pixels. Nearby centers
  within 6 pixels can be cycled after pinning. Markers and intervals highlight;
  clicking outside, Close or Escape dismisses the selection.

Offline JavaScript tests cover state transitions, sorting, scale-independent
snapping, mode/route filters and time navigation. Full-population tests use the
actual generated 61,070-row page. Browser visual verification remains unavailable
because the browser tool blocks local-file navigation; no alternate browser
workaround was used.

### Layout, numbers and overview brush

The main plot and 80-pixel overview together occupy at most 75svh (75vh fallback).
The centered chart width is capped at 1440px and reduced to preserve the main
SVG aspect ratio within that height budget; no non-uniform main-plot stretching
is used. A wide monitor therefore cannot grow the graph beyond the viewport.

Tooltip and table VAXen/CI95 use SI prefixes with exactly three decimal places,
including milli/micro for early machines. Rounding across a prefix boundary
promotes the prefix (999999.9 becomes 1.000 MVAXen). Numerical exports and sorting
still use the full original values.

Inspired by the overview selector visible in
[pvvx GraphMemo](https://pvvx.github.io/ATC_MiThermometer/GraphMemo.html), the count
overview itself owns the selection window and its two draggable handles. Drag a
handle to resize, drag the window to pan, or drag outside it to create a range.
Handles cannot cross and preserve the one-year minimum span. Keyboard focus
remains on the handles while drawing; arrow keys adjust them by one year.
The former separate From/To range inputs have been removed. The implementation
is local SVG/JavaScript; no pvvx script or external chart library is required.

### Submission-era compatibility reviews

`research/data/historical/submission-date-reviews.csv` records per-result date
reviews. Required fields are `record_id`, the exact `submission_date` being
reviewed, `decision` (`accept`/`reject`), `reason`, evidence `source_url`, and
`reviewed_on`. A stale date/identity or missing justification stops generation.
A rejected submission candidate remains in `date_candidates` with `eligible=false`
and its review; it cannot supply the plotted year. CPU and hardware dates retain
priority. If no other date is usable, the result remains in the table as Unknown;
its scores and calibration intervals are not removed or changed.

No universal age-gap threshold has been selected. The veto is evidence-based
and manually curated: e.g. a modern retrospective test cannot establish the
introduction year of a machine known to belong to the 1960s. An absent review
means unreviewed, not independently proven era compatibility. The initial review
table is empty; this change introduces the gate without inventing exclusions.


## Instruction-mix records

The shared page also includes 360 positive CCTA/TSU source cells: 177 Gibson
and 183 ADP. Each cell remains an individual comparison record with its original source ID; the
routes `Gibson mix` and `ADP mix` can be independently filtered. Both use
`generation=instruction_mix`, `mode=peak_proxy` and the saved
`linear_clock/with_spec89` joint calibration. Other mix variants are not silently
converted with these factors. Rebuilding the page does not fit a model.

`reported_score`/`reported_unit` retain KIPS, `scores` identifies the exact metric,
`mix_variant` identifies CCTA/TSU, and `estimated_specint92_rate` is explicitly a
prediction. The usual VAXen/CI95, source, configuration and evidence fields use
the shared contract. Word size, memory capacity and memory cycle are displayed
as configuration details; memory-cycle time is not a CPU clock. Unknown CPU,
processor count and software fields remain empty. Tooltip details identify the
mix variant and conditional calibration; SI formatting applies to VAXen only.

The adapter verifies upstream input hashes, exact source-score coverage and each
prediction against the saved coefficient and joint draw intervals. It includes
only one scenario, avoiding four copies of each observation. The original
classical, SPEC89 and modern SPEC populations remain intact; mix estimates are
correlated with the classical route and do not count as independent validation.

CPU chronology keeps first priority. Reviewed matching hardware evidence and
existing year overrides take precedence over the source's approximate model
year. Superseded source dates remain in `date_candidates` with `eligible=false`;
a reviewed unresolved-date rule does not silently restore that source year.
There is no submission-date fallback for these source mix ratings. The current
addition has 289 dated and 71 undated records, with earliest displayed year 1954.


### Combined mix display (2026-09-28)

The default visible mix route is `Combined mixes`: 186 source table rows,
including 174 with both Gibson and ADP and 12 with only one positive rating.
The individual Gibson/ADP routes remain available but are unchecked initially.
Grouping uses source snapshot hash, source URL and original table-row identity,
not machine name, so repeated model labels/configurations are not collapsed.

For a two-mix row, `V = sqrt(k_G * G * k_A * A)`. Each aligned joint bootstrap
replicate applies the same equal-log-weight formula, and its quantiles provide
CI95. Independent resampling or multiplying marginal interval endpoints would
lose the coefficient dependence and is not used. A single available rating
passes through its original estimate and interval. This is display aggregation
of the saved joint model, not another fit.

Combined records retain both input scores and source IDs, `reported_score=null`
and `mix_combination` describing the operation/fallback. There are 61,070 total
exported view records: 60,524 original records, 360 individual mix views and 186
combined views. With individual mix comparison routes disabled, 60,710 records
are visible with all three score categories selected by default. These are
view-record counts, not independent experiment counts. The combined route has
149 dated and 37 undated rows.


### Score selection and list navigation

Scores uses independent SPEC Base, SPEC Peak and Historical estimates
checkboxes, initially all selected. Clearing all three shows an empty view.
Changes reset list pagination to the first page. Benchmark route defaults are
unchanged: combined mixes on, individual mix comparison routes off.

Both ends of the list use one List Browsing template and one shared event
binding function. Each includes Sort list, Previous/Next, page/row counts and
Goto Page. Sort and page state are synchronized in both directions. Each Goto
Page field accepts a whole page number from 1 through the filtered page count;
Enter or Go submits. Invalid/out-of-range values do not
navigate. Empty lists disable the jump controls and both paging directions.


Clock frequency is displayed with the configuration details in both table rows
and tooltips (`clock: N MHz`). Missing clock values omit that item entirely;
no orphan MHz label is emitted. CPU identity remains beside the system name.
Memory-cycle timing stays a separate source field and is not converted into
an assumed CPU clock.
