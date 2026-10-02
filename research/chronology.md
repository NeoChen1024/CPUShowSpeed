# Date events and chronology selection

Reviewed: 2026-10-02. Status: **implemented** as step 3 of the
[data schema](../docs/data-schema.md#migration-plan). The selection replaced the
timeline's private date code; `plot timeline` reads it since schema step 5d. The
former timeline (built before the 2026-10-02 removals) serves as the comparison.

## Reproduce

```sh
uv run cpushowspeed data extract   # observations, result-records.jsonl and model-years.jsonl
uv run cpushowspeed data build              # result_chronology and consistency_finding
```

`data import-dates` performed the one-time conversion into `date_event.jsonl`
(and the entities, aliases and sources it needs). The command was removed on
2026-10-02 (schema step 5d) and its inputs archived in
[`data/archive/legacy-dates/`](data/archive/legacy-dates/README.md).

## Date events

2,109 curated events, each with one source, locator, verification and legacy ID:

| Origin | Events | Subject |
| --- | ---: | --- |
| CPU SKU catalogue (Wikipedia) | 1,423 | processor SKU; 31 future or current-quarter dates are `announced_future` and excluded |
| Hardware date evidence | 593 | system model keyed from the machine name; 139 former `use_for_timeline=false` rows are `excluded` |
| CPU release proxies | 34 | 23 new x86 SKUs and 16 families at the granularity reviewed (Pentium 75, "Intel-compatible 486DX2") |
| Year overrides | 33 | the system models each regex selected, or Pentium II/III/Pro/4 families |
| SPEC89 hardware introductions | 26 | system model; processor-introduction rows are `inferred_proxy` |

The former configuration proxies became aliases: a CPU text plus clock, or (when
no CPU text existed) the system name, links a record to the reviewed processor.
A clock constraint rules an alias out only for a known, different clock.

## Selection

For each of 58,356 benchmark results: (1) CPU release of its processor entity,
else of its SKU's family; (2) hardware, taking the first non-empty tier: the
result's own reported availability, primary model events, the result's own
compilation year, then model-level dates found elsewhere (other results' table
years or SPEC availability, Longbottom catalogue years, matched to a clock
variant when needed); (3) reviewed family fallbacks; (4) publication. Within the
chosen kind conflicting years give a range and midpoint. Unconfirmed claims and
excluded events never select.

| Selected kind | Observations |
| --- | ---: |
| CPU release | 74,551 |
| Hardware | 27,420 |
| Fallback proxy | 104 |
| Unknown | 1,044 |

Counts are after the 2026-10-02 CPU92 speed adapter rewrite, the step-4 reviews and
the catalogue spelling aliases (all below).

## Comparison with the former timeline

**SPEC rate (58,813 records):** 50,298 keep their year; 44,754 move from hardware
to CPU dating, mostly one year earlier (7,635 by −1, 521 by −2). Larger moves are
old CPUs tested years later (Xeon E5-2620 in 2019 systems), as intended. Four
records formerly dated by publication now use a model-level hardware date.
A first run let a reviewed Pentium 4 family proxy (2000) override 2005 hardware
availability; fallbacks were then ranked below all evidenced hardware dates.

**Classical and SPEC89 (1,711 former configurations, matched by system text):**
898 are dated in both (16 with a different year), 7 are newly dated, 294 are
undated in both, and 161 lose a year. 351 former configurations used rejoined or
altered names and could not be matched. The losses come from catalogue spellings
the keys do not unify ("DECSTN 5000/200", "IBM 370/165 Fast Mult", "Amdahl 470 V/6");
the former code used looser per-row matching.

## Consistency findings

Reported, never resolved:

- 298 results whose CPU release year is later than their own reported hardware
  availability (for example Cascade Lake Refresh SKUs in systems listed as
  available in 2019).
- 8 subjects whose primary event years are more than one year apart (Opteron 1xx
  revisions; Amdahl 5870/5880 announcement versus delivery).

## CPU92 speed adapter rewrite (2026-10-02)

The first selection left all 139 CPU92 speed results undated because the speed
adapter kept only scores and a few hardware fields. Speed and rate disclosures now
share one parser that keeps every labelled field and the issue month
([SPEC collection](../docs/spec-collection.md#recovered-netlib-cpu92-integer-rate-results)).
Scores, identities and benchmark rows are unchanged (305 speed results; 274 rate
records whose benchmark and exclusion CSVs are byte-identical); 18 speed and 11 rate
compiler fields gained their second line.

After rebuilding, all 139 results have a year (hardware tier); 28 speed results that
had borrowed a model-level date now use their own reported availability (HP 9000
735/125: 1992 from the 735 → 1994); 15 SPEC89, Netlib SPEC92 and Dhrystone results
moved one year as model-level ranges gained the speed dates, and 5 Dhrystone/LINPACK
results became dated. Where a speed and a rate disclosure name the same vendor,
system and processor, 104 availability months agree and 8 differ: two rate pages
print `######` and six are disclosures that state different months (Bull Escala
1994-12 versus 1995-04).

## Reviews

Step 4 moved four date decisions into `data/curated/review.jsonl`:

| Result | Rejected date | Now selected |
| --- | --- | --- |
| SPEC CPU2017 speed `res2021q4/cpu2017-20211025-29885` (Supermicro A+ Server 2124BT-HTR, EPYC 7313) | hardware availability 2019-08 | CPU release 2021 |
| Longbottom Whetstone "Ferranti Argus 700G swf" | table year 1963 | model event 1973 (unchanged) |
| Longbottom Whetstone "GEC Elliott 903C" | table year 1963 | model event 1965 (unchanged) |
| Longbottom Whetstone "GEC Elliott 905" | table year 1963 | unknown (was 1963) |
| SPEC CPU2017 rate `res2021q4/cpu2017-20211025-29879` (same EPYC 7313 system), added 2026-10-02 | hardware availability 2019-08 | CPU release 2021 (unchanged) |

The EPYC 7313 exclusion cited AMD's launch date (2021-03-15); that date is now a
release event of a new `sku:amd-epyc-7313`, which moves all 26 EPYC 7313 results
(52 observations) from hardware to CPU dating. 24 of them reported 2021
availability and keep their year; the two that reported 2019-08 move to 2021.
Rejecting the hardware date alone would have left 2019: other configurations of
the same system model carry Rome processors available in 2019. The second 2019-08
result, the rate result of the same submission (`cpu2017-20211025-29879`), was not
in the exclusion file. CPU dating already outranked its reported date, so its
year was 2021 either way, but the 2019-08 month still entered model-level dates and
the result's reported fields. A review now rejects it too (SPEC disclosure re-read
2026-10-02: "Hardware Availability: Aug-2019"), with the same AMD source. The
annual hardware-year figure, which reads reported availability without reviews
([annual rate](annual-rate-vaxen.md#interpretation-limits)), is unchanged.

### CDC Cyber 73 and 74 (2026-10-02)

Longbottom's Whetstone table labels two rows "Control Data 6400 (Cyber73)" and
"Control Data 6600 (Cyber74)" with the year 1964. The system key dropped the
parenthesis and merged them into the 6400 and 6600. They are now exact-text
aliases of the separate models `sys:cyber73` and `sys:cyber74`. The
[Datapro Cyber 70 report](https://bitsavers.org/pdf/datapro/datapro_reports_70s-90s/CDC/70C-263-11_7107_CDC_Cyber_70.pdf)
(July 1971, PDF page 1, re-read 2026-10-02) says the Cyber 70 systems were
"Introduced in March 1971" with deliveries scheduled for early 1972, and that
Models 72, 73 and 74 are improved versions of the 6200, 6400 and 6600.
[Museum Waalsdorp](https://www.museumwaalsdorp.nl/en/museum-waalsdorp-2/history/comphistory/computer-history-the-period-1978-1983/comp781e/)
likewise calls the Cyber 74 a modern version of the 6600.

The six results (Cyber 73: 2; Cyber 74: 4) move from 1964 to 1971 via the existing
Datapro introduction events. Their 1964 table years are rejected in `review`, and
the mix "CDC 6600" ↔ "6600 (Cyber74)" candidate link is rejected.

### Catalogue spelling aliases (2026-10-02)

Longbottom's MIPS catalogue spells many models differently from the benchmark
tables ("DECSTN 5000/200", "IBM RS/6000 320", "DEC Alpha 3000/500S"), so their
catalogue years reached no result. 97 reviewed exact-text `system_model` aliases
(source `src:longbottom-mips`) now link them, accepting only the same model
designation in another spelling; a different suffix (S, E, J, VF, X, L) is a
different model unless both sides carry it. Two forms are used:

- **Identity merges (35 aliases).** Where the catalogue spelling already resolves
  to a system with its own records, the variant record texts join that system
  ("IBM RISC Sys/6000-320" and "IBM RS/6000 Model 320" → `sys:rs/6000320`;
  "DEC VAX 11/780" in SPEC89 → `sys:vax11/780`; "MIPS 3230" and "MIPS Magnum
  (RC3230)" → `sys:rc3230`). 34 duplicate system IDs disappear, and the merged
  results also pair with each other in the fits.
- **Catalogue aliases (62 aliases).** Otherwise the catalogue text points at the
  benchmark system ("DECSTN 5000/200" → `sys:decstation5000/200`). Catalogue
  years now resolve exact-text aliases before the system key; they date the model
  only.

167 previously undated results (312 observations) gained a hardware-tier year:
62 SPEC89-era results (54 SPEC89, 3 bridge, 4 throughput, 1 DEC SPEC92), 60
LINPACK, 32 Dhrystone and 13 DEC-report results. No previously dated result changed. The candidate list
came from a token match of undated systems against the catalogue; each accepted
pair was checked by name, not against an independent source.

## Known gaps

- LINPACK, Dhrystone, SPEC89 and DEC-report rows without a dated model stay unknown
  (834 results). Of SPEC89's 106 undated results, most name a model the Longbottom
  catalogue lists only as a variant (SPARCstation 330 vs SparcSERVER 330,
  HP 9000/425s vs 425T, DEC 3000/400S vs 3000/400) or not at all; the former
  processor-family proxies (for example "Intel 486/25") are not restored.
- Variant-suffix and option matches (3090-180E VF, 5860 HSFPF, 4D/310 vs 4D/310S)
  and ambiguous ones (SGI Indigo vs Indigo R4000, DEC 7000-610 as VAX or Alpha)
  were left unaliased.
