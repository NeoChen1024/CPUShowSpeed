# Classic benchmark source collection

Implemented on 2026-09-26. The active VAXen series remains integer rate; this
collector preserves broader historical evidence without declaring benchmarks
interchangeable or importing normalized scores.

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
