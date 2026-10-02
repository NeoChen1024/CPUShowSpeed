# System identity resolution

Reviewed: 2026-10-02. Status: **implemented** as step 2b of the
[data schema](../docs/data-schema.md#migration-plan). Rules were designed afresh;
no fitter or timeline consumes them yet.

## Reproduce

```sh
uv run cpushowspeed data extract-mentions   # also writes data/derived/schema/hardware-records.jsonl
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
- **System model** (`spec-system-v1`, SPEC records with a resolved vendor): the
  system name without parenthesised or comma-separated processor/clock/OS/compiler
  prose, without the record's own processor text (word-bounded), clock and cache
  tokens, and without a leading vendor prefix. The key is the case-folded name and
  **excludes the vendor**, so product lines that changed owner stay one model.
  Hand-curated models and exact-text aliases take precedence; none exist yet.
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
| Observations with a system model | 98,539 |
| Observations with a hardware configuration | 94,116 |
| Observations whose processor came from the system name | 74 |
| Derived system models | 3,733 |
| Models seen under several vendor entities | 102 |
| Models in several SPEC suites | 329 |
| Hardware configurations | 37,490 |

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

## Known gaps and residue

- Classical, SPEC89 and instruction-mix records have no vendor field and get no
  system model; their machine names need curated `system_model` rows and aliases.
- Few classical system names contain a resolvable processor (74 observations).
- Residue in derived names: Supermicro "Processor Blade …" product names are kept
  as named; a few names keep a stray "Processor" word or list several models
  ("Escala T430, EPC430 & E230").
- Vendor prefixes are curated for about 35 vendors; others keep their brand word
  in the model name (for example "Camarero …" is stripped of "Tyrone", but
  "ACTINA SOLAR …" keeps its brand).
