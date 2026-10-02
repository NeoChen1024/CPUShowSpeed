# Shared VAXen timeline

**Status 2026-10-03:** `plot timeline` is built on the
[data schema](data-schema.md) database (schema step 5d, `vaxen-timeline-v3`).
The page, pathway explorer and calculator were reworked for it on 2026-10-03;
everything below describes current behavior.

This document owns the combined view's data contract, date handling and
interaction. It consumes saved calibration; it does not fit a model.
[Research results](../research/unified-vaxen-timeline.md) own the checked
population and numerical comparisons.

## Reproduce

```sh
uv run cpushowspeed data extract
uv run cpushowspeed data build
uv run cpushowspeed bridge fit-rate92-anchor
uv run cpushowspeed bridge fit-rate-generations
uv run cpushowspeed bridge bootstrap-rate-chain
uv run cpushowspeed classic spec89-rate-fit
uv run cpushowspeed classic network-fit
uv run cpushowspeed classic mix-network-fit
uv run cpushowspeed bridge fit-speed-predictors
uv run cpushowspeed plot timeline
```

`data extract` and `data build` produce `data/derived/schema/cpushowspeed.sqlite`.
The fitting commands regenerate the saved calibration the timeline reads; they
can be skipped when their outputs are current (see each command's `--help`).
`plot timeline --database PATH --output-dir DIR` reads only the database and
saved calibration files, records their hashes in `audit.json`, and performs no
network collection or fitting. It refuses a mix or predictor bundle fitted on
other database inputs or with changed code.

The population is:

| Route | Rows | Value |
| --- | ---: | --- |
| SPEC92–SPEC2026 integer rate | one per result and base/peak mode | Reported score × saved `same_os` rate-chain factor, with its pointwise CI95 |
| Classical | one per one-processor (or unknown-count) classical result | Saved classical network prediction (`linear_clock / with_spec89`) |
| SPEC89 | one per SPEC89 result in the saved estimates | Saved two-edge bridge estimate |
| Gibson / ADP mix | one per positive rating | Saved [mix network](../research/instruction-mix-network.md) estimate (`plus_pending_links / linear_clock / with_spec89`) |
| Combined mixes | one per source table row | Equal-log-weight combination of the row's available ratings, CI95 from aligned draws |
| SPEC95–2026 speed | one per speed result and mode with a fitted speed predictor | Speed × saved [speed-only predictor](../research/spec-speed-rate-predictors.md) VAXen coefficient |
| SPEC95–2026 speed + rate | one per hardware-near speed/rate pair and mode with a fitted joint predictor | `sqrt(speed × rate)` × saved joint predictor coefficient |

The first three routes are the **baseline** (`estimate_kind = baseline`); the
others are model estimates (`mix`, `mix_combined`, `speed`, `joint`), correlated
with the baseline routes and never counted as extra evidence. On 2026-10-02 this
gave 115,335 records: 58,813 SPEC rate, 1,641 classical, 179 SPEC89, 360 mix,
186 combined mix, 37,117 speed and 17,039 joint. CPU2000 has no speed or joint
rows because its predictor boundary has one processor model.

## Static website export

The default export uses Zstd level 3 Parquet (implemented 2026-09-29). Run the existing
`plot timeline` command, then serve the repository root with a static HTTP server
such as darkhttpd. This also keeps the relative research/method-note links usable.
Open `data/derived/figures/timeline/vaxen-timeline.html` through that server. No application
server, npm install, frontend build, or external CDN is required.

Initialize the pinned decoder once after cloning:

```sh
git submodule update --init third-party/hyparquet third-party/fzstd
uv run cpushowspeed plot timeline
darkhttpd . --addr 127.0.0.1 --port 8080 --hide-dotfiles
# Open http://127.0.0.1:8080/data/derived/figures/timeline/vaxen-timeline.html
```

Outputs under `data/derived/figures/timeline/`:

- `vaxen-timeline.html`: the sole interactive page, containing CSS, UI code and
  the bundled Worker/decoder with MIT notices; no benchmark datasets are embedded.
- `manifest.json`: `vaxen-web-parquet-v1`, artifact schemas, row counts, byte sizes,
  SHA-256 hashes (including inline code), decoder revisions and small lineage/calculator configuration.
- `data/records.parquet`: complete shared research records, retaining the logical
  `vaxen-timeline-v3` contract and all provenance.
- `data/timeline.parquet`: the display projection used by the page.
- Other `data/*.parquet`: large lineage/fit arrays and aligned calibration draws.
- `audit.json`: population, date/mode/route counts, input/code hashes and the
  exported manifest hash.

JSONL/CSV text exports are no longer written. Large derived outputs stay outside Git.

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

The browser fetches and decodes the display datasets in a Blob Web Worker,
checks byte size and row count, and verifies SHA-256 where Web Crypto is available
(including localhost). Loading failures remain visible, without showing partial
results. It does not fetch the full research-record export. This first migration
loads the entire display projection, fit arrays and calculator draws before
mounting the page; it retains the existing in-memory filtering/sorting behavior.
It does not yet implement row-group range requests, lazy detail loading or SQL.
An ordinary static server is sufficient; HTTP Range support is not required yet.
All frontend code and styles are embedded in HTML; the Worker is constructed
from the embedded source using a Blob URL, which is revoked on completion/error.
There are no separate JS/CSS, type declarations, package manifests or library
source files in the export. Serving only the output directory renders the
visualization, but repository-relative method-note links require the repository
root to be available. A host applying CSP must permit the inline script/style
and Blob Worker (or supply appropriate hashes/policy).

When upgrading an old export, unchanged files listed in its `assets_sha256`
manifest are removed and empty asset directories pruned. Modified or unrelated
files are retained.

The decoder is `third-party/hyparquet`, pinned to v1.31.2, commit
`460fb574870606a67eccaf59f7d7c08b46ec551e`. Export verifies the revision and a clean
submodule. Zstd decoding uses fzstd
0.1.1, with its source submodule pinned to the npm release's exact gitHead
`807a854cac2c5766ef030832cc5b66482dc7ca8a`. Its upstream source is TypeScript;
`third-party/fzstd-browser` holds the official published ES module (renamed from
`.mjs` to `.js` for static-server MIME compatibility), license and provenance.
The release archive was verified against npm's SHA-512 integrity; export checks
the release files' SHA-256 hashes. `third-party/timeline-decoder` contains the
prebuilt esbuild 0.25.12 bundle of the required runtime exports, with unused code
removed. Its provenance checks every build input and the final bundle. The
complete upstream MIT notices remain inside the embedded decoder. Building this
bundle is a dependency-maintenance step; daily Python export needs no npm,
TypeScript or esbuild. Only the ZSTD codec is registered with hyparquet. Updating
either decoder requires rebuilding the bundle and rerunning the cross-language
checks; see its README.


The earlier annual-rate PNG/SVG reports and their hardware-year statistical
summaries remain reproducible snapshots. The shared timeline is the new
interactive entry point; it does not silently reinterpret those earlier annual
boxplot cohorts as CPU-year cohorts.

## Shared record contract

Every record has `schema_version`, a unique `record_id`, `result_id` (the
database result) and `system_id` (the resolved system, when known). SPEC IDs are
`spec:{generation}:{result}:{mode}`; base and peak are separate rows. Different
submissions are never deduplicated merely because system, CPU, year or scores agree.

| Fields | Meaning |
| --- | --- |
| `route`, `generation`, `mode` | Source/calibration route and original suite; historical estimates use `peak_proxy`, not an asserted peak measurement |
| `system`, `cpu`, `clock_mhz`, `os`, `configuration` | Source identity; unknown fields remain empty |
| `scores`, `reported_score`, `benchmark_id` | Original input scores; classical composites have no single reported score |
| `vaxen`, `ci95_low`, `ci95_high` | Saved estimate and conditional calibration interval, without per-core normalization |
| `calibration_route`, `calibration_scenario`, `uncertainty_scope` | How the estimate was obtained and what its interval covers |
| `source_record_ids`, `benchmark_sources`, `source_url` | Contributing observations and source links |
| `observation_count`, `evidence_class` | Population meaning and evidence status |
| `measurement_scope`, `chips`, `cores`, `threads_per_core`, `copies_min`, `copies_max`, `nodes` | Distinct reported quantities; unknown counts remain empty, never inferred from one another |
| `year`, `year_low`, `year_high`, `date_kind`, `date_method`, `date_sources`, `date_candidates` | Copied from `result_chronology`; unknown years are empty strings |
| `hardware_date`, `submission_date`, `test_date` | SPEC source months as reported, for display only |
| `estimate_kind` | `baseline`, `mix`, `mix_combined`, `speed` or `joint` |
| `reported_unit`, `mix_combination`, `estimated_specint92_rate`, `speed_system` | Estimate-specific: input unit, mix combination, predicted SPEC92 rate, the speed input's system name |
| `limitation` | Route-specific caveats, including sparse CPU2026 calibration |

No benchmark score is changed when a date changes.

## Date selection

The timeline selects no dates itself. Each row copies its result's
`result_chronology` row from the database; the [data schema](data-schema.md)
owns the precedence (reviewed CPU release, then hardware availability, then a
reviewed fallback, then publication) and the [data contract](data-contract.md)
owns date interpretation. `date_kind` is `cpu`, `hardware`, `fallback` or
`unknown`; `date_method` is the chronology `basis`; `date_candidates` keeps every
candidate event; and `date_sources` lists the URLs of the candidate events'
sources. The year range is the evidence span, not a statistical interval.

On 2026-10-02: 44,899 rows were dated by CPU, 14,964 by hardware, 17 by a
reviewed fallback and 753 were unknown. Unknown rows are concentrated in
classical sources without model-year evidence (Netlib LINPACK alone has 573
of its 815 rows unknown) and in SPEC89; they stay in the list but are not plotted.
The former per-pass date tables are archived in
[`research/data/archive/legacy-dates/`](../research/data/archive/legacy-dates/README.md).

## Measurement scope and uncertainty

The research target is single-node / documented-system throughput, not single
core. Preserve measured chip, core and copy counts separately. A historical
one-processor calibration proxy does not turn into a newly measured multi-core
result. Classical results with a reported CPU count above one are excluded;
the classical network is calibrated on one-processor targets.

Some SPEC records name clusters. They remain included and source-linked; missing
node counts are not guessed and these rows are not certified as single-node
measurements. No division by cores/chips/copies is performed.

Each route retains its own CI95. CPU92 uses a defined reference scale; later
SPEC modes use the corresponding saved chain interval. Classical and SPEC89
proxies use their saved intervals, both targeting the peak rate anchor.
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
snapping, mode/route filters and time navigation (`tests/timeline_interaction.js`,
run by the unit tests on a synthetic page). The full-population check loads the
generated page's actual Parquet through the pinned JavaScript decoder:

```sh
node tests/timeline_interaction.js data/derived/figures/timeline/vaxen-timeline.html full
```

It asserts the 2026-10-03 population (115,335 rows by estimate kind), estimate
filters, related rows, predictor scatterplots, lineage traces, pagination, and that
the calculator reproduces timeline rows (a reported CPU2017 rate, a CPU2026
speed/rate pair, a Gibson rating, a two-rating combined mix) to 1e-6 or better.
Its counts change whenever the data does.

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

### Estimate filters and related rows

The **Estimates** checkboxes select by `estimate_kind`: reported rate /
historical baseline (●) and combined mixes (■) are on by default; single mix
ratings (■), speed (▲) and speed + rate (◆) are optional. Route checkboxes
default on for every route. A status line counts model estimates beside
baseline rows, which they are correlated with rather than independent of.

There is one cross-generation policy, `hardware_near` over resolved identity, so
records carry no per-policy variants and the page has no matching selector
(Strict / RAM + aliases / CPU + clock were removed with the name-matched
experiments). A joint row exists for every hardware-near speed/rate pair; its
date follows the rate input. Mix record IDs are the database result IDs
(`mix:longbottom-cpumix:…`); combined rows append `:combined`.

A pinned point lists rows **from the same source results**: rows sharing a
`source_record_ids` entry (base/peak of one result, a speed or rate result and
its joint rows, a single rating and its combined row). These are connected on the
plot. A collapsed **Same resolved system** list adds other rows with the same
`system_id`, other routes first. Neither list is a validation.

Submission-era compatibility reviews were removed in step 5d: the review table
is archived and reviewed fallbacks enter through the database chronology.

### Score selection and list navigation

Scores uses independent SPEC Base, SPEC Peak and Historical estimates
checkboxes, initially all selected. Clearing all three shows an empty view.
Changes reset list pagination to the first page.

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
intervals, SPEC89 bridge summaries, the classical and mix network coefficients
and the speed/rate predictor summary supply numerical details. Input hashes are recorded in the timeline audit.
The layout is fixed and scrolls horizontally on narrow screens; the information
card moves below the graph. Arrow widths do not represent precision or sample
size. Nodes/arrows support mouse clicks and Enter/Space activation.

The SPEC rate chain displays the saved rate-chain edges, with the `same_os`
constraint for CPU95→92. The second SPEC89 edge already outputs
VAXen (including rate normalization); no extra normalization is added visually.
Classical calibration is one network block; it is not depicted as an
independent multiplier chain. Gibson/ADP ratings feed a separate classical + mix
joint model node (the timeline run, `plus_pending_links / linear_clock /
with_spec89`), which the classical scores also feed. Each SPEC suite with a
fitted predictor (CPU95, 2006, 2017, 2026; CPU2000 has too few tuples) has a
speed node whose arrow enters the older suite's rate; its card lists speed-only,
rate-only and joint local factors, CI95 and model-held-out P95 by mode.

**Compare predictor fits** plots the hardware-near tuples of one boundary and
mode (older rate against speed, rate or `sqrt(speed × rate)`) with the saved
local factor and CI95, or the SPEC89→92 source pairs. Tracing a speed or joint
row opens it on that row's boundary and inputs.

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

Validation covers complete-page route tracing for CPU2026, SPEC89, classical,
combined-mix and joint records, metadata edge identities, path reset,
existing timeline controls, and standalone SVG rendering. This is not a claim
of full browser visual interaction verification.

### Copy and color hierarchy

Use solid backgrounds throughout: white page/cards, a light-gray pathway panel,
and pale purple/teal model/unit nodes. Avoid gradients. The unit definition and
calibration-CI explanation live inside **How scores become VAXen**, above the
graph. The VAXen node holds plural, SI-prefix and speed-versus-rate details.
The main page keeps short scope, chronology and interaction hints; individual
record qualifications remain in the tooltip and path details.

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
  `classic predict-rate`. Adding a mix input selects the mix network's timeline
  run (`plus_pending_links / linear_clock / with_spec89`) for **all** supplied
  historical metrics.
- Available families receive equal weights, and variants share their family's
  weight. Gibson and ADP form one InstructionMix family. The point estimate is
  the weighted geometric mean of individually calibrated scores.
- CI95 combines matching rows of saved joint log-coefficient draws before taking
  the 2.5/97.5 percentiles. Marginal interval endpoints are never averaged.
  All draws are embedded, with full precision; no independent resampling occurs.
- SPEC accepts one generation and one base/peak mode at a time. SPEC95–2026
  rate alone uses the saved `same_os` rate chain (as the timeline's rate rows);
  speed alone uses the speed-only predictor and both use the equal-geometric
  predictor, each with its saved VAXen coefficient and CI95. CPU2000 speed has no
  predictor and produces an explicit error.
- SPEC89 accepts native integer speed only. SPEC92 rate uses its defined factor;
  the native/peak speed bridge remains historical. Supplying both CPU92 inputs
  returns separate estimates, because a joint coefficient is not calibrated.
- Inputs must describe the same machine/configuration. Blank means absent;
  zero, negative and non-finite values are rejected. No input clock scaling occurs.
  Changing inputs clears the prior result.
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

Editing inputs, changing the calculator mode, or an invalid
calculation removes the previous marker. **Reset** clears score/year inputs,
results and markers, and restores source-data axis bounds while keeping the
timeline's search, route and score filters. A blank year calculates values without
placing a marker.

### Resource disclosures

Tooltips distinguish enabled hardware from rate copies and speed benchmark threads.
Cached disclosures provide mode ranges; runtime_resources retains benchmark-level
values and source hashes. Missing details are labeled explicitly. Speed and
joint rows show the enabled hardware of their speed or rate input but no runtime
threads or copies; their `runtime_resources` are not exported yet. Raw cache/memory/compiler/
pointer/parallel context is expandable. CPU92 uses a legacy CPU-count label.
Topology conflicts are flagged without changing numbers. See the
[source audit](../research/spec-resource-field-audit.md).

### Shared inputs

SPEC and classical rows read the built database (`observation_store`,
`classical_store`); the former input-catalog snapshot option was removed. Source
values are not rescaled.

Unparsed runtime declarations are displayed as their escaped source values
(e.g. `64i`), rather than inferred integers or a missing-download label. The
[data contract](data-contract.md#unparsed-runtime-declarations) defines these
statuses and their conservative fitting treatment.
