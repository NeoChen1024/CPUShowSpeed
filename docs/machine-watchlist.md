# Priority machine watchlist

These machines are explicit research priorities, including their named variants.
They are targets for source discovery and evaluation, not claims that usable
benchmark or instruction-timing results have been extracted. Candidate paths
below were found in the [bitsavers file inventory](sources.md#local-pdf-mirror-and-discovery-inventory);
filenames alone do not establish document contents or applicable model revisions.

## DEC PDP-8: original, PDP-8/I, PDP-8/E

Keep results and timing assumptions separate for each implementation, and record
optional arithmetic and memory-extension hardware. The common architecture does
not establish equal execution time.

- Original: `pdf/dec/pdp8/pdp8/F-85_PDP-8_Users_Handbook_May66.pdf`
- PDP-8/I: `pdf/dec/pdp8/pdp8i/DEC-8I-HR1A-D_8Imaint_Mar70.pdf`
- PDP-8/E: `pdf/dec/pdp8/pdp8e/DEC-8E-HMM1A-D-D_PDP-8e_Maintenance_Manual_Volume_1_Processor_Sep73.pdf`

## LINC

For the original LINC, start with
`pdf/washingtonUniversity/linc/LINC_Reference_Manuals/LINC_Logic_Drawings_and_Timing_Diagrams.pdf`
and `pdf/washingtonUniversity/linc/LINC_Reference_Manuals/LINC_Vol_16_Section_2_Programming_the_LINC_Jun65.pdf`.
The `pdf/dec/linc/LINC_Brochure_May65.pdf` is a secondary lead. LINC-8 and
PDP-12 materials are related, but are not substitutes for an original LINC
measurement. Check which LINC revision each document covers.

## IBM 1401

Prioritize `pdf/ibm/1401/A24-6447-0_1401_1460_Instruction_and_Timing_Summary.pdf`.
Account for variable-length fields, word marks, and operand-dependent timing
before mapping an instruction mix.

## LGP-30

Look under `pdf/generalPrecision/LGP-30/`, starting with
`LGP-30_Programming_Manual_195704.pdf` and `LGP-30_Operations_Manual.pdf`.
A drum-based timing model must state assumptions about instruction and operand
placement.

## DEC PDP-7

Start with `pdf/dec/pdp7/PDP7_Instruction_list.pdf`; find model-specific timing
and a stronger architecture reference. Include the machine's UNIX connection as
a reason for priority, while keeping historical significance separate from a
performance estimate.

## DEC PDP-10: KA10, KI10, KL10, KS10

Treat each processor implementation as a separate target. The inventory offers:

- KA10: `pdf/dec/pdp10/KA10/DEC-10-HGAA-D_PDP-10_System_Reference_Manual_196805.pdf`
- KI10: `pdf/dec/pdp10/KI10/A_Document_On_The_KI10_Apr73.pdf`
- KL10: `pdf/dec/pdp10/KL10/EK-EBOX-UD-003_EBOX_Instruction_Execution_Unit_Unit_Description_Dec76.pdf`
- KS10: `pdf/dec/pdp10/KS10/EK-0KS10-TM-001_KS10_Tech_Oct78.pdf`

Do not assign one undifferentiated PDP-10 score to all four implementations.

## Honeywell 6180

Prioritize the Multics processor configuration. The inventory includes
`pdf/honeywell/large_systems/multics/AL39-0_MULTICS_Processor_Manual_Draft_Oct75.pdf`
and `pdf/honeywell/large_systems/multics/swenson/7307.6180-debuggers-handbook.PDF`.
Check which hardware revision each document describes; later Multics processor
manuals must not automatically be treated as 6180 timing sources.

## OCR reading batch

The [machine-readable OCR file list](../inventories/watchlist-ocr.txt) contains
all 16 explicitly named PDF leads above, ordered so short instruction and
timing references are processed before longer manuals; the secondary LINC
brochure is last. All 16 paths had `ok` inventory records on 2026-09-26,
totaling 2,213 pages. OCR generated DocIR for all 16 documents on
2026-09-26. This selects documents for reading and does not verify
that their contents describe the required machine revision or contain usable
timing evidence. OCR text and model-generated diagrams still require checks
against the original PDF pages.

## Evidence needed for each target

Find the exact processor and configuration, original instruction semantics,
timing conditions, any required software emulation, and independent published
performance where possible. Cite document pages. Keep measured results, manual
reconstructions, and normalized estimates separate under the
[data contract](data-contract.md).
