# Classic benchmark source collection

Implemented on 2026-09-26. Classical, SPEC89 and mix routes are calibrated to
speed-VAXen (SPECint92 speed = 1; user decision 2026-10-03); this collector preserves broader historical evidence without declaring benchmarks
interchangeable or importing normalized scores.

## Pipeline

Collectors and parsers (`classic collect`, `extract`, `extract-pdf-tables`,
`overlap-spec`, `mix-inventory`) write derived records; `data extract` and
`data build` load them into the built database. The fitters
(`classic composite-fit`, `spec89-fit`, `network-fit`, `mix-network-fit`, `mix-bridge`)
read only that database and pair classical with SPEC results by resolved
`system_id` (schema step 5c, 2026-10-02). The former `prepare-pairs` /
`prepare-sources` name-matching stage and the earlier diagnostic fitting commands
were removed; they remain in Git history.

## Reading and reproduction order

For the research interpretation, start with the [classical fits](../research/classical-fits.md).

| Task | Commands / section |
| --- | --- |
| Acquire source snapshots | `classic collect`, `classic extract` below |
| Extract reviewed PDF tables | [Selected tables](#selected-historical-pdf-tables) |
| Parse records and build the database | `classic overlap-spec`, `classic mix-inventory`, then `data extract`, `data build` |
| Fit current direct speed models | [Primary speed fitting](#primary-classical-speed-fitting) |
| Add the SPEC89 estimated-target route | `classic spec89-fit` in the primary fitting section |

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

The [first acquisition audit](../research/historical-sources.md#acquired-classical-sources)
records current coverage. Raw bodies, archives and extracted reading data stay
outside Git. The compact acquisition CSV is a provenance inventory; it does
not replace a future reviewed per-result dataset.

## Hardware overlap discovery

Run `.venv/bin/cpushowspeed classic overlap-spec` from the repository root.
It parses acquired sources and existing SPEC archives into records, requires
Poppler's `pdftotext`, and does not download sources, pair records or calculate
conversion factors. Pairing happens over resolved systems in the database.

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

The `model_key`/`relaxed_key` name helpers remain only for the legacy
timeline's date lookup (removed in schema step 5d); they no longer pair records. Clocks are taken from the source's MHz field and
never inferred from model suffixes.

Outputs in `data/derived/classic/overlap-spec/`:

| File | Meaning |
| --- | --- |
| `classical-records.jsonl`, `spec-records.jsonl` | Raw fields and provenance; read by `data extract` |
| `source-coverage.csv` | Parsed sources/sections and unparsed material |
| `rejected-rows.jsonl` | Supported-layout rows whose values could not be interpreted |
| `audit.json` | Source/derived/parser hashes and PDF extraction version/hash |

Generic CPU labels and unparsed sources cannot establish absence of overlap.
See the [overlap report](../research/classical-fits.md#hardware-overlap) for resolved-system
pairing counts.

## Selected historical PDF tables

`uv run cpushowspeed classic extract-pdf-tables` extracts the acquired DEC,
SSCL and Tomari/Hiraki table sets using source-specific, reviewed recipes.
`--acquisition`, `--recipes`, `--corrections` and `--output` select inputs and
destination; source BLAKE3, correction preconditions and expected row counts
are checked. Embedded text is a parsing aid, checked against rendered PDFs.
See [extraction findings](../research/historical-sources.md#three-source-pdf-extraction) and the
[table data contract](../research/data/classic/pdf-extraction/README.md).

The extracted tables stay literal and are not fitting inputs. The DEC N3909
report columns are transcribed separately as
[curated observations](data-schema.md#curated_observation) whose
`reviewed_reading` records each cell's reviewed unit or magnitude (printed KWIPS
read as MWIPS; bare Dhrystone counts read as thousands; the VAX 4000/200 and
4000/300 Whetstone columns read at one tenth). `data extract` emits them as
`reviewed-vector:dec-n3909-1994` results.

### Primary classical speed fitting

`uv run cpushowspeed classic composite-fit` fits two/three-family geometric
composites directly to speed-VAXen (SPECint92 / SPECbase_int92 speed, defined
as 1 for the VAX-11/780), with separate base and peak cohorts and matched
single-score baselines, in `same_result` and `same_system` cohorts.
`--database`, `--output`, `--research-dir`, `--bootstrap` and `--seed` control
inputs, outputs and resampling. SPECint89 targets are excluded. See [results and
validation](../research/classical-fits.md#direct-composites).

`uv run cpushowspeed classic spec89-fit` estimates the one-edge SPECint89 →
SPECint92 speed bridge from hardware-near overlap, writes SPEC89 speed-VAXen
estimates, and evaluates joint classical models. `--database`, `--output`,
`--research-dir`, `--bootstrap` and `--seed` select inputs and settings. See
[bridge findings](../research/spec89.md) for the peak-only scope and the
separation of observed-target validation from agreement with estimated targets.

### Sparse per-benchmark calibration

`uv run cpushowspeed classic network-fit` estimates individual benchmark
coefficients jointly from anchor observations and unanchored co-measurements.
It runs reported/linear-clock scenarios and `spec92_only`/SPEC89-enabled cohorts,
with availability-masked whole-system holdouts. See [network methods and
results](../research/classical-fits.md#sparse-network) for weighting, eligibility,
identifiability and conditional CI95. Targets are SPECint92 speed (speed-VAXen);
the SPEC chains are not changed.

`classic predict-speed` consumes the saved network calibration and accepts any
nonempty score subset. See [input units, examples and CI95 semantics](classical-prediction.md).

## Instruction-mix preparation

`uv run cpushowspeed classic mix-inventory` inventories the cached CCTA/TSU
Gibson and ADP tables. It independently checks the cached HTML rows, records missing scores, validates operation weights, and preserves
source/configuration/metric identities. Default outputs live in
`data/derived/classic/mix-study/`; `--output-dir` selects another directory.
It writes `mix-records.csv`, `mix-weights.csv` and an audit; it no longer
pairs mixes with classical rows. The
[research report](../research/instruction-mix.md) owns the checked counts,
configuration risks and next experiment design.

`uv run cpushowspeed classic mix-evidence` screens the eight instruction-mix
OCR selections for benchmark terms, including canonical table-cell text. It
writes unverified page excerpts and a manifest with input hashes, page counts
and missing-document flags under `data/derived/documents/mix-evidence/`.
It only reads published DocIR; it does not publish incomplete staged documents
or turn keyword hits into calibrated scores. Original-page review and curated
SC-3/DINKIAC CSVs are described in the same research report.

`uv run cpushowspeed classic mix-bridge` pairs mix results with classical results
of the same resolved system (`resolved_system`), and separately adds the system
links a review leaves open (`plus_pending_links`); it fits them with the shared
geometric-ratio policy and audits direct SPEC89/SPEC92 overlap on the database. It preserves metric
identities and reports missing cells separately. Outputs include source-score
inventories, coverage, conditional fit summaries and PNG/SVG scatterplots under
`data/derived/classic/mix-bridge/`. No production VAXen coefficient is updated.
