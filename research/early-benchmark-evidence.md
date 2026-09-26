# First local early-benchmark evidence pass

Review date: 2026-09-26. This is a bounded first extraction, not a complete
review of every page in the local corpus. Canonical values and source hashes
are in [historical observations](data/historical/observations.jsonl), with the
[record contract](data/historical/README.md).

## Source-checked findings

### Honeywell 300

Source: [Programmers Reference Manual](https://bitsavers.org/pdf/honeywell/h300/Honeywell_300_Programmers_Reference_Manual_Aug64.pdf),
physical PDF page 10, printed page 2, central-processor summary.

- Gibson mix rating: 180,000 instructions/s without memory interlace and
  236,000 with interlace. Keep these as two configurations.
- Main-memory cycle: 1.75 microseconds; fixed-point accumulator add:
  3.5 microseconds.
- The summary does not establish Gibson weights, arithmetic options used for
  the rating, or measured-versus-calculated provenance. It cannot yet be treated
  as the same mix variant as the CCTA compilation or converted to rate-VAXen.

Physical page 24, printed page 19, additionally defines execution timing as
including instruction retrieval, execution and result storage. Indexed
addressing adds at most half a memory cycle; indirect addressing adds one cycle
per iteration. A single stated timing formula applies with or without interlace.
These rules must accompany individual instruction times to avoid double counting
or losing addressing costs. Appendix G at physical pages 105-107 is an OCR-located
instruction timing summary; its individual rows still require visual review.

### Original PDP-8

Source: [User's Handbook](https://bitsavers.org/pdf/dec/pdp8/pdp8/F-85_PDP-8_Users_Handbook_May66.pdf),
physical PDF page 25, printed page 10, memory and processor instructions.

The memory cycle is 1.5 microseconds. Indirect addressing adds 1.5 microseconds
to memory-reference execution. AND is explicitly listed as 3.0 microseconds
direct and 4.5 indirect. These are source timing inputs, not a reconstructed
benchmark score, and do not establish timings for PDP-8/I or PDP-8/E.

### DEC programming-benchmark memo

Source: [Programming Benchmarks](https://bitsavers.org/pdf/dec/pdp11/memos/700325_Programming_Benchmarks.pdf),
physical PDF pages 3-4 (Introduction; Purpose of this Memo).

The memo explicitly says its coded programs have not actually been run. It
compares instruction sets using program words, instruction counts and memory
cycles under assumptions, excluding differences in memory cycle times and
adjustments for complex-instruction execution times. Preserve it as analytical
ISA/workload evidence, not measured machine throughput. Page 4 points back to
PM18-3 by John Cohen and Larry McGowan, dated 1968-05-31; recovery of that
original problem set remains a source-discovery task.

### LGP-30

Source: [Programming Manual](https://bitsavers.org/pdf/generalPrecision/LGP-30/manuals/LGP-30_Programming_Manual_195704.pdf),
physical PDF page 11, printed page 8, Memory and Recirculating Registers.

The text states a 17-millisecond drum revolution and approximately
0.26-millisecond recirculating-register sector access. These describe distinct
storage paths; neither is a universal instruction time. A future reconstruction
must account for placement and drum phase. These values were found by expanding
the first keyword pass to drum/revolution/millisecond terminology, illustrating
why zero hits in the initial index do not prove missing timing information.

## Reading and verification performed

The existing 16-document watchlist DocIR was searched across text, table cells,
captions and diagram code for benchmark names and timing terms. The first pass
found 461 candidate blocks; keyword absence does not establish absence of
relevant evidence. The ignored search manifest records its pattern and file
hashes. Candidate excerpts are separate from the fifteen curated observations.

The new PDFs' existing text layers were used only to locate candidate pages
while Chandra was unavailable. Honeywell pages 10 and 24, DEC pages 3-4, and original
PDP-8 page 25 and LGP-30 page 11 were rendered and visually checked. Live BLAKE3
hashes of these four PDFs matched the inventory. No full-document verification
is claimed.

## Structured-table exceptions and recovery

All new OCR pages have explicit physical-page records. The first conversion
recorded nine Honeywell failures: physical page/block (zero-based block) 51/5, 52/3,
55/5, 57/2, 63/2, 64/5, 72/2, 83/2 and 89/4. The converter reports nested or
multiple tables, text outside the table, or image cells requiring asset mapping.
Original HTML remains in raw JSONL. The v2 table migration on 2026-09-26
recovered all nine structures and migrated 58 table blocks across the two
documents. These recovered tables remain unreviewed OCR, not verified numeric
data. The DEC memo has no table-conversion failures. No curated observation
above depends on these newly recovered table transcriptions.

Checks confirmed unchanged raw hashes, page/block positions, non-table content
and existing table metadata. A repeat migration changed zero blocks. The nine
failure fixtures preserve all source text/numeric token multiplicities. Twelve
inline images have only unresolved references/alt text; these are separately
reported and are not part of the completed Image Pool caption count.
`data/derived/documents/evidence/honeywell-tables-v2.md` provides simplified
reading views for the nine recovered blocks.

## Completed processing and discovery coverage

Both PDFs in `inventories/early-benchmark-ocr.txt` completed the existing
pipeline on 2026-09-26: 125/125 OCR pages, 118 successful image captions and
four structured skips, with zero failed or pending caption items. OCR resumed
30 saved pages with `--inflight-pages 64 --jobs 2`; captioning used
`--inflight-images 64`. Both stages used the existing configured local/LAN
services. Raw headers and the caption catalog retain model provenance.

DocIR backfill updated two documents and 118 caption occurrences. Hash checks
confirmed raw JSONL was unchanged, and comparing normalized page objects with
caption keys removed confirmed every non-caption field was unchanged. A second
backfill updated zero documents/captions.

After backfill, the expanded search covered all 18 documents / 2,338 pages and
found 1,736 candidate blocks, including 129 in Honeywell and six in the DEC
memo. The expanded pattern includes timing, cycles and drum terminology.
`data/derived/documents/evidence/combined-search.json` preserves search fields,
pattern, per-document counts/hashes and table exceptions;
`combined-hits.jsonl` contains the unreviewed page/block excerpts. Failed table
HTML is not searched by this pass. Caption matches remain model-generated
leads until checked against the PDF. The 15 curated records are a first review
of six physical pages across four sources, not validation of all candidates.
After v2 migration the index was rebuilt with recursive text, table and inline
image-alt traversal and refreshed hashes: it now contains 1,737 candidate
blocks. The earlier search counts describe the pre-migration pass.
