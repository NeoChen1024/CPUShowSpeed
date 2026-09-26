# Chandra sample: *A General-Purpose Time-Sharing System*

Reviewed 2026-09-26. This is a targeted OCR quality check, not a measured
corpus-wide error rate or a validation of the whole document.

## Materials

- Original: local `~/misc/ocr-test/inputs/A GENERAL-PURPOSE TIME-SHARING SYSTEM.pdf`,
  BLAKE3 `fe20d295f31d6c2b6fe30168da0a4b0e60a8ffa43919f7c76d474dbdcb6ef7d8`.
- OCR output: local `~/misc/ocr-test/chandra-outputs/A GENERAL-PURPOSE TIME-SHARING SYSTEM/`
  Markdown, HTML, metadata, and WebP files. The exact model and run parameters
  for this output were not independently established. The CLI metadata reports
  16 pages, 195 chunks, and 3 images.

## Checked observations

- Figure 1, original PDF page 1, printed page 397: the source diagram shows
  Q-32 pointing to Displays and Displays pointing to PDP-1. The OCR HTML
  contains a `graph TD` Mermaid fragment, but its
  `PDP1 <--> D[Displays]` edge changes those relationships. Structured code
  is useful for retrieval, but its edges are not source-verified.
- Figure 2, original PDF page 2, printed page 398: the hardware block diagram
  is present in the source. The current OCR HTML contains its prose reference
  and caption, but no corresponding diagram code or image element on that
  page. Captioning only emitted images cannot recover this omission.
- The current OCR HTML references three WebP images; each has a generated
  `alt` description, including two graphs and one computer-room photograph.
  The output directory also contains three unreferenced WebP files. Pool
  ingestion should follow references in the current completed result rather
  than glob every file in the directory.
- Two HTML tables in the OCR HTML converted to structured rows and Markdown
  with the local table parser. Table I uses `<math>\mu</math>` for the
  microsecond unit; the parser now preserves it as `$\mu$` in the Markdown
  reading view. This checks conversion mechanics, not the accuracy of every
  table value. The OCR text visibly spells one row label `Inut/Output`;
  the parser must not silently correct it.

## Consequence for OCR routing

Existing Mermaid code and image `alt` text can reduce routine second-model
caption work, but neither proves that a figure was transcribed correctly or
that every figure was emitted. Retain source-page access and prioritize
important relationship diagrams, numeric charts, and suspected missing
figures for visual review.
