# Three-source PDF extraction completed

Review date: 2026-09-26. Scope: DEC EC-N3909-10 Section 7, SSCL-375 numerical
Tables 1–7/B-1/C-1/D-1/E-1, and Tomari/Hiraki Appendix Tables 1–2.
Other PDF figures, DEC executive-summary ratios, and prose are not claimed as
extracted observations. CERN's modern suite remains an execution-tool lead,
not an acquired public results corpus. Searching for further sources is deferred
to the next research round.

| Source | Table page-parts | Table rows | Numeric cells |
| --- | ---: | ---: | ---: |
| DEC, 1994-12 | 7 | 163 metric rows over 88 machine/OS columns | 1,210 |
| SSCL, 1991-09 | 11 | 99 | 316 |
| Tomari/Hiraki, 2011 | 5 | 70 hardware + 70 results | 572 |

Total: 2,098 numeric cells, including hardware metadata. The long-form output
has 3,082 records including missing and qualified cells. These are not counts
of independent benchmark measurements. Originals are immutable hashed blobs;
57 checked corrections preserve both OCR and reviewed cell strings.

## Independent outcome check

The Tomari/Hiraki table yields 28 Dhrystone/CINT2006 pairs. Recomputing Pearson
correlation from the extracted values gives **0.9859865321170843**, matching the
paper's **0.986** at its reported precision (Section 3.2, printed page 221).
This checks extraction of that subset, not predictive validity or rate linkage.
The audit stores the arithmetic and sample count in machine-readable form.

## Findings affecting future fitting

DEC now supplies within-document benchmark columns rather than loose model-only
joins. The user-selected unit policy now interprets the printed Whetstone KWIPS values as MWIPS and
interprets bare Dhrystone numbers as omitted-K values. Original cells remain
unchanged; [interpreted values](data/classic/pdf-extraction/dec-interpreted.csv)
carry the rule and assumption metadata.
SSCL adds non-DEC comparisons but mixes industry ratings with separate n=300
experiments. Tomari provides a directly checked modern comparison subset.
No new scores have been substituted into the existing fitting inputs in this
round; source semantics and evidence identities have been retained for review.

## Outputs

- [Table evidence and schema](data/classic/pdf-extraction/README.md)
- [Structured table snapshot](data/classic/pdf-extraction/tables.jsonl)
- [Tomari joined configurations/results](data/classic/pdf-extraction/tomari-configurations.csv)
- [Counts](data/classic/pdf-extraction/summary.csv) and [audit](data/classic/pdf-extraction/audit.json)

The reproducible long-form CSV/JSONL and Markdown reading aid are in
`data/derived/classic/pdf-tables/`. Run `uv run cpushowspeed classic
extract-pdf-tables` with the matching acquired sources. Parser tests cover
independent printed examples, sparse columns, correction preconditions and
unparsed qualifiers. All selected table pages were rendered for visual review;
layout checks and spot checks are not an assertion of exhaustive numeric review.
