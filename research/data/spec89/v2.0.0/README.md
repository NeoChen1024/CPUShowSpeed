# SPEC89 recovered observations, curated v2.0.0 snapshot

Snapshot date: 2026-09-26. This is a versioned, source-linked subset of the
user-provided `SPEC89_consolidated_2026-09-26` research package. It preserves
reported values, record IDs, source citations, and caution flags. It is **not**
an official SPEC result archive or a claim that every historical report has
been found or independently rechecked.

## Contents

- `csv/`: all 25 UTF-8-with-BOM tables from the supplied consolidated package.
  Start with `aggregate89.csv`, `components89.csv`, `bridges89_92.csv`,
  `sources.csv`, `source_manifest.csv`, and `dictionary.csv`.
- `inputs/`: compact, immutable inputs and the manifest of the two earlier
  research packages. The original ZIP files are not included.
- `sources/`: 37 saved Usenet message texts. Their original Message-IDs,
  archive URLs, byte offsets, and hashes are in `csv/source_manifest.csv`.
- `archive_manifest.json`: hashes and sizes of the three external MBOX ZIPs.
- `summary.json`, `validation_report.json`, and `SHA256SUMS.txt`: supplied
  counts and validation evidence plus checksums for this curated snapshot.

The package contained 381 source-observation rows, including two records with
only benchmark components. These are observations of published material, **not**
381 independent executions. `measurement_type`, `verification`, `review_flags`,
and `source_id` must accompany any analysis. The quarantine, noncompliant
CPU-time approximations, throughput, simulations, later reruns, and original
speed results are separate tables or flagged rows. Do not fill missing original
scores from calculated QA fields.

`bridges89_92.csv` has 34 source-paired rows: 17 contain both `SPECint89` and
`SPECint92`, while 17 contain `SPECmark89` and CPU92 scores without a reported
`SPECint89`. Several rows reprint the same system and score vector. Retain all
source observations; account for source dependence when estimating a bridge.
The pairing alone does not prove identical hardware and software run settings.
See [the research findings](../../../spec-sources.md#early-spec-result-archives) and the project's
[bridge method](../../../../docs/methods.md) before fitting a factor.

## Rebuild and verification

Use the repository's uv-managed `.venv` and Click CLI. Rebuilding writes only
under ignored `data/derived/spec89/` by default:

```sh
./.venv/bin/cpushowspeed spec89 verify
./.venv/bin/cpushowspeed spec89 rebuild
```

`verify` checks every tracked snapshot file against `SHA256SUMS.txt`, validates
the saved message hashes and result links, then reconstructs all 25 CSV tables
and `summary.json` byte-for-byte in a temporary directory. The supplied
`validation_report.json` contains one additional historical check that
re-extracted all 37 messages from the original MBOX ZIPs. That check is
preserved as provenance and cannot be rerun from this subset alone.

With the three external ZIPs available, their 37 messages can be re-extracted
and checked against the byte ranges and SHA-256 values in `source_manifest.csv`:

```sh
./.venv/bin/cpushowspeed spec89 recover-sources --archive-dir /path/to/mbox-zips
```

The dataset builder is `python-src/cpushowspeed/spec89/build.py`; source recovery
is `python-src/cpushowspeed/spec89/usenet_sources.py`. Both are called via the
`spec89` CLI group. The older standalone merger, archive scanners, and XLSX
builder remain only in the local input package. This subset excludes the
4.4 MB broad keyword index, redundant 3.1 MB JSON aggregate, XLSX workbook,
older README snapshots, and full MBOX ZIPs. Their omission does not turn
reported scores into independently verified benchmark runs.

Some rows still have pending PDF visual checks, unavailable original PDFs, or
historical provenance uncertainty. The supplied validation checks confirm
internal consistency and saved message identity; they do not newly verify
all external PDF, web, or historical performance claims.
