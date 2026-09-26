# Classic benchmark source collection

Implemented on 2026-09-26. The active VAXen series remains integer rate; this
collector preserves broader historical evidence without declaring benchmarks
interchangeable or importing normalized scores.

## Reading and reproduction order

For the research interpretation, start with the [classical track](../research/tracks/classical.md).
Commands below retain their historical experiments; they do not all produce
interchangeable targets.

| Task | Commands / section |
| --- | --- |
| Acquire source snapshots | `classic collect`, `classic extract` below |
| Extract reviewed PDF tables | [Selected tables](#selected-historical-pdf-tables) |
| Build source vectors and candidate pairs | [Source-column experiments](#source-column-pair-experiments) |
| Fit current direct rate models | [Primary rate fitting](#primary-classical-rate-fitting) |
| Add the SPEC89 estimated-target route | `classic spec89-rate-fit` in the primary fitting section |
| Reproduce earlier controls | `fit-spec92`, `composite-fit`, `pair-fit`, `pooled-fit`, `environment-fit` |

The [model registry](../research/model-registry.json) distinguishes each target,
input dataset and dependency. Acquisition preserves source values; fitting uses
explicit derived interpretations and keeps reported/inferred targets separate.

## Commands

Use the repository-root uv-managed environment:

```sh
.venv/bin/cpushowspeed classic collect \
  --sources docs/data/classic-benchmark-sources.csv
.venv/bin/cpushowspeed classic extract \
  data/raw/classic/manifests/REPLACE_WITH_RETURNED_MANIFEST.jsonl
```

`collect` reads an explicit CSV, uses two download workers by default, and fetches
only those URLs. It does not recursively crawl the site or execute downloaded
programs. Spaces in historical URLs are percent-encoded. HTTP is supported
because the Longbottom and some Netlib sources were reachable that way when
HTTPS failed. A run returns its manifest path as JSON on stdout; source progress
is on stderr. `--timeout`, `--workers` and `--max-mib` bound requests and payloads.
A failed request is recorded; the command exits nonzero after recording the run.
Retry with a smaller source list or an explicitly chosen alternate URL.

Each successful response is saved under `data/raw/classic/blobs/` by BLAKE3.
Writes are atomic and never overwrite different bytes. Each run has a unique
immutable JSONL manifest recording requested/final URL, retrieval date, HTTP
status/content type, size, hash, local path and source metadata. A new collection
run re-fetches the selected URLs and creates a new manifest; identical payloads
reuse the same blob. Previous failed attempts are retained.

`extract` checks blob hashes and writes derived JSON under
`data/derived/classic/`. HTML extraction uses BeautifulSoup's `html.parser`:

- Save full decoded text and links (including separate fragment identifiers).
- Preserve top-level table HTML; nested tables stay with their parent.
- Convert eligible tables into the existing rich table v2 representation.
- Preserve every `pre` block's whitespace for fixed-column result listings.
- Retain explicit table-conversion failures alongside the HTML and full text.
- Inventory ZIP members without unpacking or running anything; other file
  formats, including PDF, PostScript and source code, remain raw.

The saved table fragment is BeautifulSoup's serialization; the immutable blob
is the exact downloaded HTML. HTML repair/decoding and table conversion are
reading projections. They do not verify row meanings or classify layout tables
as benchmark result tables. Some PRE blocks contain programs, not results;
nested PRE/table representations must not become duplicate observations.

## Provenance and independence

The [source list](data/classic-benchmark-sources.csv) separates provider,
benchmark family, role and a provisional `lineage` label. A lineage describes
a source relationship, not proven independence of every contained measurement.
In particular:

- Longbottom's website and his ResearchGate copies are not separate experiments.
- Netlib hosts contributions from multiple origins; hosting alone does not
  establish either sameness or independence.
- A benchmark program and its report can share a lineage while describing
  different kinds of evidence.
- One article may reprint results, report new measurements and change the
  algorithm. Separate those at result level before matching machines.
- Historical commercial MIPS claims, instruction-mix KIPS, executed benchmark
  rates, scalar/vector results and parallel results retain their own semantics.

The [first acquisition audit](../research/classic-benchmark-collection.md)
records current coverage. Raw bodies, archives and extracted reading data stay
outside Git. The compact acquisition CSV is a provenance inventory; it does
not replace a future reviewed per-result dataset.

## Hardware overlap discovery

Run `.venv/bin/cpushowspeed classic overlap-spec` from the repository root.
It uses acquired sources and existing SPEC archives, requires Poppler's
`pdftotext`, and does not download more sources or calculate conversion factors.

Implemented readers:

- Netlib Dhrystone PRE rows: system/OS/CPU columns followed by a whitespace
  numeric tail, avoiding truncated decimal clocks and starred scores. All
  328 numbered rows in the acquired snapshot are retained.
- Longbottom Whetstone history: PRE 2's historical supplier table, stopping
  at the separately formatted PC section. Preserve supplier, language,
  optimization and introduction-year text. The CPU/precision field is not
  necessarily a processor model.
- Gibson/ADP: eight-column HTML rows, one record per mix and source row.
  Missing scores remain explicit listings, not invented measurements.
- Later PC Whetstone/Dhrystone/LINPACK/Livermore: CPU-labelled PRE rows with
  uninterpreted score columns; they do not enter whole-system matching.
- Netlib LINPACK PDF: Table 1 machine lines with a separated numeric result.
  Preserve physical page/line, original text and processor-count annotations.
  The partial reader does not reconstruct wrapped rows, interpret the n=100,
  n=1000 or theoretical-peak columns, or pool later tables with Table 1.

SPEC inputs are the combined SPEC89 aggregate archive, the separately labelled
SPEC89 throughput archive, Netlib SPEC92 rate records and the rate-only DEC
manufacturer supplement. Hardware discovery does not restore a speed-to-rate fit.

Model keys normalize vendor prefixes, spelling and `Model`/`AXP` syntax while
preserving variant letters, grouped numeric model labels and `+` distinctions.
FPA/EAE and explicit CPU-count qualifiers can be omitted from a model key but
remain in the source record: a key is a model group, not a configuration.
Trailing HP `/clock` or numeric parentheses are removed only when corroborated
by the source's MHz field. Clocks are never inferred from model suffixes.
Clocks within 1% are labelled compatible; conflicts and unknowns remain in the
outputs. RAM is not an exclusion rule.

Outputs in `data/derived/classic/overlap-spec/`:

| File | Meaning |
| --- | --- |
| `classical-records.jsonl`, `spec-records.jsonl` | Raw fields/provenance and derived matching fields |
| `candidate-pairs.csv` | Every candidate pair, including repeated submissions and clock conflicts |
| `summary.csv`, `model-summary.csv` | Counts by benchmark/cohort and model group |
| `source-coverage.csv` | Parsed sources/sections and unparsed material |
| `rejected-rows.jsonl` | Supported-layout rows whose values could not be interpreted |
| `audit.json` | Source/derived/parser hashes and PDF extraction version/hash |

No pair is configuration-verified or fitting-eligible. Processor implementation,
FPU/options, concurrency, compiler, OS and source independence require review.
Generic CPU labels and unparsed sources cannot establish absence of overlap.
See the [first overlap audit](../research/classic-spec-overlap.md).

## Exploratory score fitting

```sh
uv run cpushowspeed classic fit-spec92
```

Consumes the overlap records/pairs and the preserved `pdftotext -layout` output
`data/derived/classic/netlib-linpack-report.txt` generated by `overlap-spec`.
The fitter interprets only the LINPACK Table 1 n=100 column using each physical
page's header alignment; blank n=100 cells stay missing. It does not interpret
TPP or theoretical peak as n=100 performance. Other supported scores are
Dhrystone 1.1/2.1 DMIPS and historical Fortran Whetstone main/DP MWIPS.

`data/derived/classic/fit-spec92/` contains `pairs.csv` (all SPEC92 candidate
metric/scenario rows, including exclusions and source locators), `summary.csv`,
`audit.json`, and base/peak PNG/SVG scatterplots. The audit hashes inputs,
implementation and output CSVs. `--bootstrap` and `--seed` control deterministic
model-cluster resampling. This command selects exploratory cohorts; it does
not change the discovery records' `fit_eligible=False` or approve a match.

See [methods](methods.md#classical-workload-association-diagnostics) and the
[first fitting results](../research/classic-spec92-fitting.md) for selection,
uncertainty and limitations. Existing rate-chain conversion is unchanged.

### Composite intersection audit

`uv run cpushowspeed classic composite-overlap` checks complete Dhrystone 1.1,
Whetstone native/DP and LINPACK n=100 vectors against separate SPEC89 aggregate
and SPEC92 rate targets. Outputs live in `data/derived/classic/composite-overlap/`.
It compares known-clock, unknown-clock and explicit Dhrystone/Whetstone linear
clock-normalization scenarios, retaining original values and adjustment factors.
It audits feasibility and does not estimate geometric-mean weights. See the
[intersection findings and selection rules](../research/classic-composite-overlap.md).

`uv run cpushowspeed classic composite-fit` consumes that audit's `vectors.csv`
and compares fixed equal weights with single-score baselines on identical
held-out models. `--bootstrap` and `--seed` control conditional factor intervals.
Outputs in `data/derived/classic/composite-fit/` include summaries, model folds,
source-ID-linked tuple predictions, error PNG/SVG and hash audit. See
[equal-weight validation](../research/classic-composite-fitting.md) and
[statistical definitions](methods.md#fixed-equal-weight-composite-validation).

### Two-family fitting

`uv run cpushowspeed classic pair-fit` tests Dhrystone + Whetstone,
Dhrystone + LINPACK, and Whetstone + LINPACK independently. Dhrystone 1.1/2.1
and Whetstone native/DP remain separate variants. It reads overlap records and
LINPACK layout text, with no third-score requirement, and emits equal-weight
fits plus matched single-score baselines. Same-row Dhrystone version statistics
are also generated. `--bootstrap` and `--seed` retain the existing defaults.
See [two-family findings](../research/classic-pair-fitting.md) for selection,
clock normalization, output contracts, and version-pooling limits.

## Selected historical PDF tables

`uv run cpushowspeed classic extract-pdf-tables` extracts the acquired DEC,
SSCL and Tomari/Hiraki table sets using source-specific, reviewed recipes.
`--acquisition`, `--recipes`, `--corrections` and `--output` select inputs and
destination; source BLAKE3, correction preconditions and expected row counts
are checked. Embedded text is a parsing aid, checked against rendered PDFs.
See [extraction findings](../research/classic-pdf-extraction.md) and the
[table data contract](../research/data/classic/pdf-extraction/README.md).

The PDF extractor also emits `dec-interpreted.csv` using the source-bound
`interpretation-policy.json`: DEC Whetstone numeric values are interpreted as MWIPS despite printed KWIPS; omitted
Dhrystone K suffixes use the explicit user-selected thousands interpretation.
Original observations stay literal. The source-pair and subsequent fitting
commands consume the reviewed interpretation policy.

### Source-column pair experiments

`uv run cpushowspeed classic source-pair-fit` aggregates reviewed DEC columns,
consumes the declared unit interpretation, and compares source-only pair fits
with prior and newly matched cross-source extensions. Inputs are selected by
`--pdf-root`, `--legacy-pairs`, `--spec-records`; sibling `classical-records.jsonl`
is read for the DP scale audit. `--bootstrap`, `--seed`, and `--output` control
resampling and outputs. It does not reclassify unknown active CPU counts as one,
change units to improve a fit, or update the conversion chain. See
[source-pair findings](../research/classic-source-pair-fitting.md) for cohorts,
exclusions, target definitions, and the corrected unit interpretation and cross-source comparisons.

`uv run cpushowspeed classic source-diagnostics` examines the SPEC92 integer-rate
peak source experiment with fixed common models, signed residuals, reciprocal
cohort transfers, matched-OS controls and full outlier ranking. `--input-root`
and `--output` select derived artifacts; reviewed PDF tables and archive SPEC
metadata supply OS labels. No score or residual threshold removes observations.
See [diagnostic findings](../research/classic-source-diagnostics.md) and its
source-linked outlier review for the four checks and their limitations.

`uv run cpushowspeed classic environment-fit` compares pooled, environment-grouped
and partially pooled multipliers using fixed two-family composites. `--input-root`
and `--output` select source-pair inputs and output location. All machine folds
use nested training-only selection of shrinkage strength; environment/origin
holdouts expose unseen-group behavior. See the [environment model closeout](../research/classic-environment-models.md)
for weighting, the distinction from previous model-center P95 statistics, and
limits on historical extrapolation. No SIMH reconstruction runs in this command.

`uv run cpushowspeed classic pooled-fit` fits two- and three-family composites
against pooled native SPECint89/92 scores. `--pairs` and `--bridges` select the
source-pair dataset and source-paired integer bridge; `--output`, `--bootstrap`
and `--seed` control outputs. It compares aligned, 1:1, single-generation and
common-model cohorts, with single-component baselines. See [pooled findings](../research/classic-pooled-fitting.md)
for joint bootstrap semantics and the distinction from production rate-VAXen.

### Primary classical rate fitting

`uv run cpushowspeed classic rate-composite-fit` fits two/three-family geometric
composites directly to SPEC92 integer-rate VAXen, with separate base and peak
cohorts and matched single-score baselines. `--pairs`, `--output`, `--bootstrap`
and `--seed` control inputs and resampling. It reuses the input's existing rate
normalization once and excludes ordinary SPECint89/92 targets. See [results and
validation](../research/classic-rate-composite-fitting.md). The native `pooled-fit`
command is retained as an auxiliary experiment.

`uv run cpushowspeed classic spec89-rate-fit` audits direct SPECint89/rate hardware
overlap, fits the observed two-edge native-integer/rate path, and evaluates joint
classical models. `--input-root`, `--spec-records`, `--native-bridge`, `--output`,
`--bootstrap` and `--seed` select inputs and settings. See [bridge findings](../research/spec89-rate-bridge.md)
for the absence of direct pairs, peak-only scope and separation of observed-rate
validation from agreement with estimated targets.
