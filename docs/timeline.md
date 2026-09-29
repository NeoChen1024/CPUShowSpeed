# Shared VAXen timeline

Implemented on 2026-09-27. This document owns the combined view's data contract,
date selection and interaction. It consumes saved calibration; it does not fit
a new model. [Research results](../research/unified-vaxen-timeline.md) own the
checked population and numerical comparisons.

## Reproduce

```sh
uv run cpushowspeed classic historical-timeline
uv run cpushowspeed classic mix-network-fit
uv run cpushowspeed bridge fit-joint-tracks
uv run cpushowspeed bridge fit-joint-tracks --matching-policy ram-aliases
uv run cpushowspeed bridge fit-joint-tracks --matching-policy cpu-clock
uv run cpushowspeed bridge refit-95-2000
uv run cpushowspeed plot timeline
```

The first command regenerates the historical input from existing collected
records and the saved classical prediction bundle. The second fits the separate
mix experiment; it can be skipped when its saved inputs and outputs are current.
Saved fitting bundles can be reused until their inputs or model code change.
The timeline command validates the
historical input hashes and modern factor provenance, imports the current
SPEC92–SPEC2026 rate submissions, and applies saved `same_os` rate factors and
pointwise calibration intervals. The timeline command performs no network
collection or fitting.

## Static website export

The default export uses Zstd level 3 Parquet (implemented 2026-09-29). Run the existing
`plot timeline` command, then serve the repository root with a static HTTP server
such as darkhttpd. This also keeps the relative research/method-note links usable.
Open `data/derived/figures/timeline/vaxen-timeline.html` through that server. No application
server, npm install, frontend build, or external CDN is required.

Initialize the pinned decoder once after cloning:

```sh
git submodule update --init third-party/hyparquet third-party/fzstd
uv run cpushowspeed --input-catalog data/derived/inputs plot timeline
darkhttpd . --addr 127.0.0.1 --port 8080 --hide-dotfiles
# Open http://127.0.0.1:8080/data/derived/figures/timeline/vaxen-timeline.html
```

Outputs under `data/derived/figures/timeline/`:

- `vaxen-timeline.html`: the sole interactive page, with no embedded datasets.
- `assets/`: CSS, ES modules, the Web Worker and the pinned decoder source/license.
- `manifest.json`: `vaxen-web-parquet-v1`, artifact schemas, row counts, byte sizes,
  SHA-256 hashes, decoder revision and small lineage/calculator configuration.
- `data/records.parquet`: complete shared research records, retaining the logical
  `vaxen-timeline-v2` contract and all provenance.
- `data/timeline.parquet`: the display projection used by the page.
- Other `data/*.parquet`: large lineage/fit arrays and aligned calibration draws.
- `audit.json`: population, date/mode/route counts, input/code hashes and the
  exported manifest hash.

`--text-exports` additionally writes the legacy `records.jsonl` and `records.csv`.
Without this flag, these two legacy files are removed from the output directory
after a successful page export. Other research pipelines and immutable raw source
JSON files are unchanged. Large derived outputs stay outside Git.

### Parquet representation and loading

Scalars are stored in native columns. Float64 preserves the existing prediction
precision; values are not rounded for storage. Empty strings, nulls and absent keys
remain distinct using codec metadata and auxiliary columns. Numeric columns with
empty-string missing values retain native numeric storage plus an empty marker.
Heterogeneous/nested provenance remains explicitly marked JSON cells inside
Parquet; no full dataset is packed into one JSON cell. Draw tables have one metric
per column, preserving the original shared bootstrap row order.

Each file stores its reversible codec in `cpushowspeed.codec` Parquet metadata;
the manifest also supplies it to the browser. `timeline_storage.read_table(path)`
reconstructs the complete logical records in Python. Generic Parquet tools can
inspect native columns directly; auxiliary presence/empty markers and JSON-cell
metadata must be honored for an exact logical round trip.

The browser fetches and decodes the display datasets in a module Web Worker,
checks byte size and row count, and verifies SHA-256 where Web Crypto is available
(including localhost). Loading failures remain visible, without showing partial
results. It does not fetch the full research-record export. This first migration
loads the entire display projection, fit arrays and calculator draws before
mounting the page; it retains the existing in-memory filtering/sorting behavior.
It does not yet implement row-group range requests, lazy detail loading or SQL.
An ordinary static server is sufficient; HTTP Range support is not required yet.
Exported ES modules use `.js` so darkhttpd serves the correct MIME type without
extra configuration. `assets/package.json` only declares the module format for
Node-based tests; it has no dependencies or build scripts. Serving only the output
directory also renders the visualization, but repository-relative method-note
links require the repository root to be available.

The decoder is `third-party/hyparquet`, pinned to v1.31.2, commit
`460fb574870606a67eccaf59f7d7c08b46ec551e`. Export verifies the revision and a clean
submodule, and copies its ES modules and MIT license. Zstd decoding uses fzstd
0.1.1, with its source submodule pinned to the npm release's exact gitHead
`807a854cac2c5766ef030832cc5b66482dc7ca8a`. Its upstream source is TypeScript;
`third-party/fzstd-browser` holds the official published ES module (renamed from
`.mjs` to `.js` for static-server MIME compatibility), license and provenance.
The release archive was verified against npm's SHA-512 integrity; export checks
the copied files' SHA-256 hashes. No npm or TypeScript build is needed during
export. Only the ZSTD codec is registered with hyparquet. Updating either decoder
requires updating its pin/provenance and rerunning the cross-language checks.


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
snapping, mode/route filters and time navigation. Full-population tests load actual Parquet through the pinned JavaScript decoder,
including the 121,385-row display projection and unchanged 61,070-row baseline
population. The 2026-09-29 migration was checked against the prior HTML payload,
lineage and calculator values, and all complete records against the prior JSONL.
The HTTP page was also loaded in the browser: the plot and 200-row first list page
rendered successfully after Worker decoding.

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

## Calibration pathway explorer

The collapsed **How scores become VAXen** section contains an offline SVG graph
and a details card. Nodes and edges use the model registry; saved rate edge
intervals, SPEC89 bridge summaries and the two classical/mix coefficient bundles
supply numerical details. Input hashes are recorded in the timeline audit.
The layout is fixed and scrolls horizontally on narrow screens; the information
card moves below the graph. Arrow widths do not represent precision or sample
size. Nodes/arrows support mouse clicks and Enter/Space activation.

The SPEC rate chain displays the selected hardware-matching policy across all
generations, with an additional `same_os` constraint for CPU95→92. The second SPEC89 edge already outputs
VAXen (including rate normalization); no extra normalization is added visually.
Classical and mix calibration occupy distinct joint-model blocks with shared
classical inputs; they are not depicted as independent multiplier chains.

Pin a timeline point, then choose **View calibration path**. Its route is
highlighted, unrelated nodes fade, and the card shows the original input scores,
saved VAXen/CI95 and calibration qualifications. Clicking a highlighted arrow
shows its model details; rate rows select that point's base/peak mode. Clicking empty space in the pathway graph clears the trace and resets its
information card; clicking a node or edge still opens its details. This does
not change the main timeline filters, zoom or pagination. Unestablished connections remain documented in the
research report and are not shown in the explorer.

Factor CI95 and held-out error are separately labelled. The legacy rate-edge
relative-error field is multiplied by 100 for percentage display. Joint-model
component intervals are not multiplied to reconstruct a record's interval;
the trace shows the record's existing joint/chain interval. Research links are
relative local paths; the explorer itself needs no network or external library.

Validation covers complete-page route tracing for CPU2026, SPEC89, classical
and combined mixes, metadata edge identities, path reset,
existing timeline controls, and standalone SVG rendering. This is not a claim
of full browser visual interaction verification.

### Copy and color hierarchy

Use solid backgrounds throughout: white page/cards, a light-gray pathway panel,
and pale purple/teal model/unit nodes. Avoid gradients. The unit definition and
calibration-CI explanation live inside **How scores become VAXen**, above the
graph. The VAXen node holds plural, SI-prefix and speed-versus-rate details.
The main page keeps short scope, chronology and interaction hints; individual
record qualifications remain in the tooltip and path details.

## Selectable model estimates and matching (2026-09-29)

The page has Estimates checkboxes: Rate baseline / historical (default),
From speed, and From speed + rate. Matching is single-select: RAM + aliases
(default), Strict, or CPU + clock (cross-platform). It applies across all five
adjacent generation boundaries and within-generation predictor matching.
RAM capacity may differ; reviewed lexical aliases are admitted without inventing
new hardware equivalences. CPU + clock also permits different platforms at near-equal
clocks; none of these policies scales scores by frequency. CPU/chip count, clock
and known enabled-resource compatibility checks remain in force.
The CPU92/95 rate backbone retains its same-OS admission rule. CPU92's defined
scale and historical calibrations remain unchanged. Modern rate baselines use
the saved whole-CPU-model bootstrap backbone for every policy. Full-route factors
and CI95 change together. No fitting happens during timeline generation.

All displayed values target rate-VAXen. From speed uses the throughput predictor,
not the independent speed-to-speed SPECint92-equivalent series. Speed inputs
cover available positive SPEC95–2026 published speed submissions; transfer beyond matched
hardware remains unvalidated. Joint inputs are the admitted calibration-overlap
speed/rate pairs, not every conceivable same-generation pair. Unsupported
policy/generation combinations are hidden with an explicit unavailable count;
there is no cross-policy fallback in the UI.

Schema v2 adds `estimate_kind`, `variants` (policy to value/CI95 triple),
`comparison_keys`, and, for joint estimates, `matched_rate_variants` and
`input_configurations`. `value_scenario` identifies which saved variant supplies
the exported scalar value: RAM + aliases when supported, otherwise an explicitly
named available policy. The UI never falls back from an unavailable selection. Policies are alternative views of one record,
not duplicate observations. All source IDs and raw scores remain available.

A joint record is unique by speed source URL, rate source URL and base/peak mode.
Multiple older calibration targets do not duplicate that record. Its date follows
the rate input; both input configurations and dates remain in JSONL. Cross-platform
pairs show both system names. The page separately counts unique source records,
paired estimates and displayed points; the overview counts displayed points.

Color retains the benchmark route. Circles indicate baseline, triangles speed
predictions and diamonds joint predictions. Hover/pin shows related input
estimates and highlights visible counterparts with connecting lines. The tooltip
separately labels Rate-only — matched cohort, whose factor can differ from the
full rate baseline. The compact tooltip lists up to eight related rows and
reports when more exist; all observations remain available through the list.

How scores become VAXen includes a generation-fit selector covering all five
adjacent SPEC92–2026 bridges and the recovered SPEC89 → SPEC92 speed bridge.
Modern views show the saved joint-experiment tuples with base/peak and predictor
controls (speed, rate on the matched cohort, or their geometric mean), coefficient
CI95, CPU/configuration counts and model-held-out P95. These matched-cohort plots
are distinct from the full independent rate-chain fits shown in calibration details.
SPEC89 uses its native integer-speed pairs and disables the inapplicable mode and
predictor controls. Axes identify the actual native scores, not VAXen.
Matching applies to every modern generation view. Coincident score tuples share
a plotted mark with multiplicity in its title; source tuples remain in the raw
evidence CSV and count toward the displayed tuple total. Unsupported fits retain their points without a fitted line.
Selecting a generation arrow opens its comparison. Tracing speed/joint predictions
also selects the corresponding generation, score mode and predictor, and highlights
the local speed/joint node and its upstream rate path. The diagram includes a
modern predictor row; the local input panel shows which speed/rate inputs are
used, the local coefficient, and the full-route coefficient. Solid colors remain.

Saved joint bundles must match their code, input and CSV hashes. `fit-joint-tracks`
now exports `backbone-summary.csv` and coherent backbone draws for timeline use.
Regenerate strict, RAM/alias and CPU-clock joint bundles before
`plot timeline` when model code changes. Research scope and limits remain owned
by [joint fitting](../research/spec-joint-tracks.md) and
[relaxed fitting](../research/spec95-spec2000-relaxed-fitting.md).

## Offline VAXen calculator (2026-09-29)

The calculator sits after the timeline and before the list. Its form uses two
columns with labels above controls, switching to one column when the calculator
container is at most 36rem wide. The form is capped at 64rem; controls may shrink
without overflowing their grid cells. It performs no
network requests and never fits a model in the browser.

- Historical inputs accept any nonempty subset of Gibson/ADP KIPS, Dhrystone
  1.1/2.1 DMIPS, Whetstone SP/DP/Native MWIPS and LINPACK n=100 MFLOPS.
  Only the listed calibrated definitions are supported, not arbitrary versions.
- Classical-only input uses the same `linear_clock / with_spec89` bundle as
  `classic predict-rate`. Adding a mix input selects the existing mix+classical
  joint bundle for **all** supplied historical metrics.
- Available families receive equal weights, and variants share their family's
  weight. Gibson and ADP form one InstructionMix family. The point estimate is
  the weighted geometric mean of individually calibrated scores.
- CI95 combines matching rows of saved joint log-coefficient draws before taking
  the 2.5/97.5 percentiles. Marginal interval endpoints are never averaged.
  All draws are embedded, with full precision; no independent resampling occurs.
- SPEC accepts one generation and one base/peak mode at a time. SPEC95–2026
  speed alone uses the speed predictor, rate alone uses the full rate backbone,
  and both use the saved equal-geometric joint predictor. Matching is shared with
  the timeline. Unsupported coefficients produce an explicit error.
- SPEC89 accepts native integer speed only. SPEC92 rate uses its defined factor;
  the native/peak speed bridge remains historical. Supplying both CPU92 inputs
  returns separate estimates, because a joint coefficient is not calibrated.
- Inputs must describe the same machine/configuration. Blank means absent;
  zero, negative and non-finite values are rejected. No input clock scaling occurs.
  Changing inputs or matching clears the prior result.
- Historical and SPEC modes produce separate predictions; no uncalibrated pooled
  estimate or cross-bundle CI is constructed.

The build records hashes for embedded coefficients, draws, metadata and legacy
bridge summaries. The calculation panel reports SI-formatted VAXen, calibration
CI95, the selected route and historical component weights.

### Personal prediction marker

The calculator accepts an optional whole-number year (1–9999). A successful
calculation with a year adds an orange **You are here** point, a CI95 whisker,
and a label with year and SI-formatted VAXen. The point is an overlay: it never
enters source records, the list, counts, fitting or exports. If a legacy request
returns two independent estimates, both receive labeled markers.

Calculation reveals the supplied year in the current time window and extends
the chart bounds when necessary to include the point and interval. Normal zoom,
pan and hover preserve the overlay; panning away hides it until its year is visible
again. Year alone is not used by the prediction model.

Editing inputs, changing the calculator mode or matching policy, or an invalid
calculation removes the previous marker. **Reset** clears score/year inputs,
results and markers, and restores source-data axis bounds while keeping the
timeline's search, route and score filters. A blank year calculates values without
placing a marker.

### Resource disclosures

Tooltips distinguish enabled hardware from rate copies and speed benchmark threads.
Cached disclosures provide mode ranges; runtime_resources retains benchmark-level
values and source hashes. Missing details are labeled explicitly. Joint points
show each input's resources through input_configurations. Raw cache/memory/compiler/
pointer/parallel context is expandable. CPU92 uses a legacy CPU-count label.
Topology conflicts are flagged without changing numbers. See the
[source audit](../research/spec-resource-field-audit.md).

### Shared inputs and execution guard

SPEC observations now use the shared input adapter or --input-catalog snapshot.
The current fits exclude confirmed same-track constant-count conflicts by mode;
unknown or nonuniform counts remain provisional. Source values are not rescaled.
The resource-audit report describes the pre-guard snapshot; the
[input/fitting review](../research/input-unification-fitting-review.md) owns active
coefficient changes. Whole-route factors and intervals are regenerated together.
