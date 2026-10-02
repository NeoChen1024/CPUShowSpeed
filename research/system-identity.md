# System identity resolution

Reviewed: 2026-10-02. Status: **implemented** as step 2b of the
[data schema](../docs/data-schema.md#migration-plan). Rules were designed afresh;
no fitter or timeline consumes them yet.

## Reproduce

```sh
uv run cpushowspeed data extract   # also writes data/derived/schema/hardware-records.jsonl
uv run cpushowspeed data build              # hardware_record, system_model_derived, hardware_config
```

`data import-vendors` performed the one-time seed of `vendor.jsonl`, an empty
curated `system_model.jsonl` and vendor aliases; it refuses to overwrite them
without `--force`.

## Model

- **Hardware record**: one distinct (scope, vendor text, system text, processor
  text, nominal clock, chips, cores, threads/core, memory) tuple from the input
  catalogue: 43,743 records over 103,456 observations.
- **Vendor**: 122 organisations from 160 SPEC vendor spellings. Only spellings of
  one legal entity are merged (case, punctuation, corporate suffixes, Dell Computer
  Corporation / Dell Inc., GIGA-BYTE / Gigabyte). HP and HPE, Huawei and xFusion,
  IBM and Lenovo stay separate. Each vendor may list `model_prefixes` that system
  names repeat ("HPE", "Dell").
- **System model**: two rules share one key space. `spec-system-v1` (SPEC records
  with a resolved vendor) removes that vendor's prefixes; `name-system-v1` (every
  other record) removes any known brand word. Both drop parenthesised or
  comma-separated processor/clock/OS/compiler prose, the record's own processor
  text (bounded by letters, digits and hyphens, so "SPARC T3-1" survives "SPARC
  T3"), clock and cache tokens, and hardware options (FPA, no FPA, w/68882), which
  move to the configuration. The key **excludes the vendor**, so product lines that
  changed owner stay one model. Key-only equivalences: "Model"/"Models" ↔ "/",
  spaces around "/", a trailing "AXP", "HP 9000 Series 700 Model 720" ↔ "9000/720";
  IDs drop spaces and hyphens ("UCS C240 M5" = "UCS C240M5", "VAX-11/780" =
  "VAX 11/780"; all 44 such merges were reviewed). A key without letters gets its
  canonical brand back ("CDC 7600", "HP 9000/730", "DEC 3000/400"); without any brand
  it resolves to nothing.
- **Curated models**: 70 canonical names with vendors for the most cited classical
  machines (VAX, DECstation, DEC 3000/4000/7000/10000 AXP, early SPARCstations,
  HP 9000/7xx, RS/6000, MIPS, Amdahl 470/V7, CDC 6600/7600, IBM 360/65 and others);
  their IDs equal the rule keys, so records merge. 26 texts are rejected as
  non-machine names (vendor names, generic PC classes, processor names in the
  system field). Seven classical vendors were added.
- **Processor**: the step-2 [processor resolution](processor-identity.md); when the
  processor field resolves to nothing, the system name is tried and the record is
  marked `system_text`.
- **Hardware configuration**: equal tuples of system model, processor entity,
  nominal clock, chips, cores, threads/core and memory share one `hw:` ID. Unknown
  values are values: a record without a core count never equals one with it.

## Results

| Measure | Value |
| --- | ---: |
| Observations with a resolved vendor | 98,545 |
| Observations with a system model | 103,377 |
| Non-SPEC observations with a system model | 4,332 of 4,395 (55 rejected, 8 empty or unbranded numbers) |
| Observations with a hardware configuration | 95,151 |
| Observations whose processor came from the system name | 74 |
| System models | 5,237 (70 curated names) |
| Models seen under several vendor entities | 102 |
| Models in several SPEC suites | 351 |
| Models shared by classical sources and SPEC rate suites | 39 |
| Models shared by classical sources and SPEC89 | 57 |
| Models shared by several classical sources | 60 |
| Hardware configurations | 37,816 |

The 25 largest multi-vendor models are all ownership continuations of one line
(Huawei → xFusion, IBM System x → Lenovo, HP → HPE ProLiant, Inspur → IEIT,
H3C spellings), supporting the vendor-free key. They are listed for review, not
merged or split automatically.

### Cross-suite links

Earlier suites do not report every count: CPU92 records have no chip, core or
thread counts, and CPU95/2000 no threads per core. Equality-based configurations
therefore link only CPU95→2000 (33), CPU2006→2017 (1,349) and CPU2017→2026 (141).
A pairing policy that requires equal known values and lets unknown values pass
(memory ignored, clocks within 1%) yields:

| Adjacent suites | Compatible configuration pairs | System + processor groups |
| --- | ---: | ---: |
| CPU92 → CPU95 | 64 | 40 |
| CPU95 → CPU2000 | 48 | 28 |
| CPU2000 → CPU2006 | 295 | 206 |
| CPU2006 → CPU2017 | 1,651 | 921 |
| CPU2017 → CPU2026 | 154 | 97 |

The previous rate fits used 28, 16, 74, 860 and 154 pairings on these edges after
their own execution and resource filters, so the counts are not directly
comparable. Pairing policy belongs to the fitters (step 5); the identity layer
only states which facts are equal or unknown.

For example, DEC 7000 Model 610 AXP now joins Longbottom's Whetstone table, the
Netlib Dhrystone table, SPEC89 and its throughput results, DEC's SPEC92 brief, the
Netlib SPEC92 list, DEC's comparison report and SPEC CPU92 rate disclosures.
Netlib SPEC92 and SPEC CPU92 are two transcriptions of one result set and are not
independent evidence.

## Known gaps and residue

- Spelling variants that rules do not unify still need exact-text aliases; only the
  most cited classical machines have curated names.
- Names such as "HP 9000/735" and "9000 Series 700 Model 735/125" are kept apart:
  the suffix denotes a different clock variant.
- Few classical system names contain a resolvable processor (74 observations).
- Residue in derived names: Supermicro "Processor Blade …" product names are kept
  as named; a few names keep a stray "Processor" word or list several models
  ("Escala T430, EPC430 & E230").
- Vendor prefixes are curated for about 35 vendors; others keep their brand word
  in the model name (for example "Camarero …" is stripped of "Tyrone", but
  "ACTINA SOLAR …" keeps its brand).
