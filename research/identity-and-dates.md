# Identity resolution and dates

Reviewed: 2026-09-27 to 2026-10-02. This report owns the results of resolving
processors and systems and of dating benchmark results: steps 2, 2b and 3 of the
[data schema](../docs/data-schema.md#migration-plan), whose rules were designed
afresh (user decision 2026-10-02). The schema owns the tables; the
[timeline contract](../docs/timeline.md) owns how selected dates are shown. All
fitters pair over these identities, and the timeline reads the selected dates.

```sh
uv run cpushowspeed data extract   # observations, processor mentions, hardware records, result records
uv run cpushowspeed data build     # resolution tables, result_chronology and consistency_finding
```

## Processor identity

- **SKUs**: 1,352 Xeon, Opteron and EPYC models from the parsed Wikipedia tables
  (see [CPU SKU catalogue](#cpu-sku-catalogue)), each with its `sku-key-v1` key,
  every listed base clock, the table heading path and its source revision.
- **Families**: the most specific processor line a text identifies. 105
  chip-model lines (POWER*, RS64, PowerPC, UltraSPARC, SPARC64/SPARC, PA-RISC,
  Alpha, MIPS R-series, Itanium, Pentium Pro/II/III/4 and Pentium II/III Xeon)
  were seeded from observed texts and have no catalogue source yet.
- **Resolution order**: exact-text alias, then `sku-key-v1` with a 2% nominal
  clock constraint, then family patterns. A failed SKU rule keeps its reason
  (`no_single_sku`, `sku_not_in_catalog`, `clock_conflict`); overlapping family
  patterns are reported as `ambiguous_family_patterns`, not resolved by order.
  Patterns match after removing (R)/(TM)/®/™; UltraSPARC suffixes are
  case-sensitive ("IIi" versus "III").

Coverage over 103,119 input observations (3,868 distinct mentions, recounted
2026-10-02): **74,344 SKU (72.1%), 20,711 family (20.1%), 5,528 unresolved and
2,536 without processor text**.

| Scope | Observations | SKU | Family | Unresolved | Missing text |
| --- | ---: | ---: | ---: | ---: | ---: |
| `spec:cpu2006` | 47,553 | 43,506 | 911 | 3,136 | 0 |
| `spec:cpu2017` | 40,075 | 27,824 | 11,851 | 400 | 0 |
| `spec:cpu2000` | 7,402 | 2,695 | 4,166 | 541 | 0 |
| `spec:cpu95` | 2,619 | 0 | 2,499 | 120 | 0 |
| `spec:cpu92` | 989 | 0 | 752 | 237 | 0 |
| `classical:longbottom-whetstone-history` | 862 | 0 | 84 | 746 | 32 |
| `classical:netlib-linpack-report` | 815 | 0 | 0 | 0 | 815 |
| `reviewed-vector:dec-n3909-1994` | 661 | 0 | 0 | 0 | 661 |
| `historical-spec:spec89` | 653 | 7 | 53 | 90 | 503 |
| `classical:netlib-dhrystone-results` | 542 | 107 | 195 | 240 | 0 |
| `spec:cpu2026` | 423 | 205 | 200 | 18 | 0 |
| `mix:longbottom-cpumix` | 360 | 0 | 0 | 0 | 360 |
| `historical-spec:spec89-bridge` | 136 | 0 | 0 | 0 | 136 |
| `historical-spec:spec89-throughput` | 20 | 0 | 0 | 0 | 20 |
| `historical-spec:spec92-dec` | 9 | 0 | 0 | 0 | 9 |

Against the former `spec_overlap._processor_key` (99,061 SPEC observations): no
old key merged two catalogued SKUs; nine SKUs had been split by "Dual"/"Quad"
prefixes (Xeon 5160 under three keys); clock-only texts ("291 Mhz") had shared an
empty key and are now unresolved.

Known gaps: LINPACK, the DEC report vectors, the mix table and most SPEC89 rows
have no processor field, so their CPU must come from the system name;
Longbottom's Whetstone table yields internal codes ("P1") and run modes
("Scalar") as processor text. Sapphire/Emerald/Granite Rapids and EPYC Milan
resolve only to family; Intel Core and desktop Pentium have no catalogue and stay
unresolved (a brand-level family would mix products a decade apart), except
`alias:pattern/intel-pentium-p5` for the exact form `NNMHz Pentium Processor`
(195 observations). Ordering variants such as "100MHz 604 PowerPC" do not match.

## System identity

- **Hardware record**: one distinct (scope, vendor text, system text, processor
  text, clock, chips, cores, threads/core, memory) tuple: 43,743 records over
  103,456 observations.
- **Vendor**: 122 organisations from 160 SPEC spellings; only spellings of one
  legal entity are merged. HP and HPE, Huawei and xFusion, IBM and Lenovo stay
  separate. Vendors may list `model_prefixes` that system names repeat.
- **System model**: `spec-system-v1` (SPEC records with a resolved vendor) removes
  that vendor's prefixes; `name-system-v1` (all others) removes any known brand
  word. Both drop processor/clock/OS/compiler prose, the record's own processor
  text, clock and cache tokens and hardware options (FPA, w/68882, moved to the
  configuration). The key **excludes the vendor**, so product lines that changed
  owner stay one model. Key-only equivalences include "Model" ↔ "/", a trailing
  "AXP" and "HP 9000 Series 700 Model 720" ↔ "9000/720"; IDs drop spaces and
  hyphens (all 44 such merges reviewed). A key without letters gets its brand
  back ("CDC 7600", "HP 9000/730").
- **Curated models**: 70 canonical names for the most cited classical machines;
  26 texts are rejected as non-machine names.
- **Hardware configuration**: equal tuples of model, processor entity, clock,
  chips, cores, threads/core and memory share one `hw:` ID; unknown values are
  values.

| Measure | Value |
| --- | ---: |
| Observations with a resolved vendor | 98,545 |
| Observations with a system model | 103,377 |
| Non-SPEC observations with a system model | 4,332 of 4,395 |
| Observations with a hardware configuration | 95,151 |
| System models | 5,237 (70 curated names) |
| Models in several SPEC suites | 351 |
| Models shared by classical sources and SPEC rate suites | 39 |
| Models shared by classical sources and SPEC89 | 57 |
| Hardware configurations | 37,816 |

The 25 largest multi-vendor models are all ownership continuations (Huawei →
xFusion, IBM System x → Lenovo, HP → HPE ProLiant), supporting the vendor-free
key. Netlib SPEC92 and SPEC CPU92 are two transcriptions of one result set, not
independent evidence. Gaps: spelling variants rules do not unify need exact-text
aliases; "HP 9000/735" and "9000 Series 700 Model 735/125" stay apart (different
clock variants); vendor prefixes are curated for about 35 vendors.

### Catalogue spelling aliases

Longbottom's MIPS catalogue spells many models differently from the benchmark
tables ("DECSTN 5000/200", "IBM RS/6000 320"). 97 reviewed exact-text
`system_model` aliases (source `src:longbottom-mips`, 2026-10-02) accept only the
same model designation in another spelling; a different suffix (S, E, J, VF, X,
L) is a different model unless both sides carry it.

- **Identity merges (35 aliases)**: the variant record texts join an existing
  system ("IBM RISC Sys/6000-320" and "IBM RS/6000 Model 320" → `sys:rs/6000320`;
  "DEC VAX 11/780" → `sys:vax11/780`; "MIPS Magnum (RC3230)" → `sys:rc3230`).
  34 duplicate system IDs disappeared and the merged results pair in the fits.
- **Catalogue aliases (62)**: the catalogue text points at the benchmark system
  and dates the model only.

167 undated results gained a hardware-tier year and no dated result changed.
Each pair was checked by name, not against an independent source. Later merges by
user decision: "CDC CYBER 4680" into the CDC 4680; Richardson's "DEC 11/780" and
"DEC VAX 780" into the VAX-11/780; Longbottom's "DEC VAX 6310/6410" into the VAX
6000 Model 310/410, after the October 1989 Datapro VAX 6000 report (PDF page 12)
and its August 1991 edition (PDF page 16) list order codes 63AMx/64AMx under both
names.

## Date events

2,109 curated events, each with one source, locator, verification and legacy ID:

| Origin | Events | Subject |
| --- | ---: | --- |
| CPU SKU catalogue (Wikipedia) | 1,423 | processor SKU; 31 future or current-quarter dates are `announced_future` and excluded |
| Hardware date evidence | 593 | system model; 139 rows not used for the timeline are `excluded` |
| CPU release proxies | 34 | 23 x86 SKUs and 16 families at the reviewed granularity (Pentium 75, "Intel-compatible 486DX2") |
| Year overrides | 33 | the models a reviewed rule selected, or Pentium II/III/Pro/4 families |
| SPEC89 hardware introductions | 26 | system model; processor-introduction rows are `inferred_proxy` |

### Selection

For each benchmark result: (1) CPU release of its processor entity, else of its
SKU's family; (2) hardware, taking the first non-empty tier: the result's own
reported availability, primary model events, the result's own compilation year,
then model-level dates found elsewhere (other results' years or SPEC
availability, Longbottom catalogue years); (3) reviewed family fallbacks;
(4) publication. Within the chosen kind conflicting years give a range and
midpoint. Unconfirmed claims and excluded events never select.

| Selected kind | Observations |
| --- | ---: |
| CPU release | 74,551 |
| Hardware | 27,420 |
| Fallback proxy | 104 |
| Unknown | 1,044 |

Against the former timeline (2026-10-02), 50,298 of 58,813 SPEC rate records kept
their year; 44,754 moved from hardware to CPU dating, mostly one year earlier.
Larger moves are old CPUs tested years later (Xeon E5-2620 in 2019 systems), as
intended. A reviewed Pentium 4 family proxy once overrode 2005 hardware
availability; fallbacks were then ranked below all evidenced hardware dates.

Consistency findings are reported, never resolved: 298 results whose CPU release
is later than their own reported availability (Cascade Lake Refresh SKUs in 2019
systems), and 8 subjects whose primary event years are more than a year apart
(Opteron 1xx revisions; Amdahl 5870/5880 announcement versus delivery).

The CPU92 speed and rate disclosures share one parser that keeps every labelled
field and the issue month, so all 139 CPU92 speed results have their own
reported availability. Where a speed and a rate disclosure name the same system,
104 availability months agree and 8 differ (two rate pages print `######`; Bull
Escala 1994-12 versus 1995-04).

### Date reviews

| Result | Rejected date | Now selected |
| --- | --- | --- |
| SPEC CPU2017 speed `res2021q4/cpu2017-20211025-29885` and rate `-29879` (Supermicro A+ Server 2124BT-HTR, EPYC 7313) | hardware availability 2019-08 | CPU release 2021 |
| Longbottom Whetstone "Ferranti Argus 700G swf" | table year 1963 | model event 1973 |
| Longbottom Whetstone "GEC Elliott 903C" | table year 1963 | model event 1965 |
| Longbottom Whetstone "GEC Elliott 905" | table year 1963 | unknown |

[AMD dates the EPYC 7313 launch to 2021-03-15](https://www.amd.com/en/products/processors/server/epyc/7003-series/amd-epyc-7313.html);
that date is a release event of `sku:amd-epyc-7313`, which moves all 26 EPYC 7313
results to CPU dating (24 already reported 2021). Rejecting the hardware date
alone would have left 2019, because other configurations of the same system
carry Rome processors available in 2019. The annual rate view, which reads
reported availability, is unchanged. The Argus 700 family launch is reported in
*Computer Weekly*, 1973-06-14, p. 12, via
[TNMOC](https://www.tnmoc.org/notes-from-the-museum/2023/6/1/fifty-years-ago-from-the-pages-of-computer-weekly)
(a family proxy for the 700G); the [Elliott 903 museum record](https://www.computinghistory.org.uk/det/32480/Elliott-903/)
gives 1965 as a family proxy for 903C.

### CDC Cyber 73 and 74

Longbottom's Whetstone table labels "Control Data 6400 (Cyber73)" and "Control
Data 6600 (Cyber74)" with 1964. They are exact-text aliases of the separate
models `sys:cyber73` and `sys:cyber74`. The
[Datapro Cyber 70 report](https://bitsavers.org/pdf/datapro/datapro_reports_70s-90s/CDC/70C-263-11_7107_CDC_Cyber_70.pdf)
(July 1971, PDF page 1) says the Cyber 70 systems were introduced in March 1971
and that Models 72, 73 and 74 are improved versions of the 6200, 6400 and 6600;
[Museum Waalsdorp](https://www.museumwaalsdorp.nl/en/museum-waalsdorp-2/history/comphistory/computer-history-the-period-1978-1983/comp781e/)
agrees. The six results move from 1964 to 1971, their table years are rejected,
and the mix "CDC 6600" ↔ "6600 (Cyber74)" link is rejected.

### Known gaps

LINPACK, Dhrystone, SPEC89 and DEC-report rows without a dated model stay
unknown. Most of SPEC89's undated results name a model the Longbottom catalogue
lists only as a variant (SPARCstation 330 vs SparcSERVER 330, HP 9000/425s vs
425T, DEC 3000/400S vs 3000/400) or not at all. Variant and option matches (3090-180E
VF, 5860 HSFPF, 4D/310 vs 4D/310S) and ambiguous ones (SGI Indigo vs Indigo
R4000, DEC 7000-610 as VAX or Alpha) are left unaliased.

## CPU SKU catalogue

22 Wikipedia pages (cached with revision ID and SHA-256) gave 1,423 rows and
1,352 SKU keys for Intel Xeon, AMD Opteron and AMD EPYC, which cover 52,571 of
58,813 SPEC92–2026 integer-rate records. Wikipedia is an accepted secondary
source for model dates under the
[hardware chronology policy](../docs/sources.md#hardware-chronology-sources);
rows are parsed, not individually reviewed. Each row keeps the table's date at
its precision (quarters keep only the year) and the raw cell. Gaps: P6, Yonah and
most NetBurst Xeons (tables identify parts by clock), Sapphire/Emerald/Granite
Rapids (no per-SKU date) and EPYC Milan (no date column). Family launch dates are
not substituted. 30 SKU keys have release years more than a year apart (Opteron
model numbers sold in several revisions); all dates are retained.

`sku-key-v1` matches only text naming exactly one SKU after removing trademarks,
"processor" and every parenthetical; attached Opteron suffixes ("2220SE") are
split; tier words are part of the key (Xeon 5120 of 2006 is not Xeon Gold 5120
of 2017); "7443 (P)" yields two SKUs. When both sides give a clock, the record's
nominal clock must lie within 2% of a catalogue base clock; inspected conflicts
were overclocked runs (X5680 at 4.2–4.5 GHz), clock typos (E5-2640 v4 at 3.4 GHz)
and FSB rounding (E5310 at 1666 MHz).

Checks: Intel ARK launch quarters agree for Xeon X5670 (2010-03-16, read directly),
E5405, E5-2690 and Gold 6130, and by year for E5-2620 v4; every raw date cell
matches a recognized pattern. Two parser defects (a "Release price" column taken
as the date, "$2010" read as a year; a missed "Released" header that dropped 309
Opteron rows) were found only by comparing the timeline before and after a trial
integration, and were fixed before the catalogue was imported.

## Hardware-year evidence

The 593 hardware events come from archive and web passes completed 2026-09-27.
The first batch selected 80 PDFs (947 OCR pages) from 625 candidates in the
local bitsavers mirror (Datapro reports and brochures across DEC, IBM, HP,
Apollo, Sun, Amdahl, CDC, Unisys, Prime, Cray, SGI, Pyramid and ICL); all pages
were text-screened and 145 original pages visually checked, giving events from 54
documents and explicit non-event dispositions for 26. A broader text search of
the other 545 candidates, a Wikipedia and museum pass (92 URLs, 54 adopted) and
a reviewed x86 CPU-release fallback followed. Candidate lists are in
[`inventories/`](../inventories/); per-pass logs remain in Git history.

Interpretation rules carried into the date events:

- Dates keep their precision; quarters are year plus a separate quarter.
- Announcement, introduction, first delivery, installation, demonstration and
  option events stay distinct. A prospective delivery, or one inconsistent with
  its own announcement, is kept but not selected.
- Selected events are **model-era proxies**, not dates for every tested clock,
  CPU count, FPU, memory or software configuration. Publication years and
  customer orders are not introduction dates. Repeated reports are not
  independent samples.
- The CPU-release fallback dates an identifiable x86 CPU (method
  `reviewed_cpu_release_year_proxy`) without relabeling it as system
  availability; Pentium clock grades are dated separately (60/66 MHz 1993,
  75/90/100 1994, 120/133 1995, 166 1996).

Conflicts kept rather than repaired: Amdahl 5860 (1982 versus 1983 passages) and
5867 (delivery before its own announcement); the 1987 Amdahl PDF's appended
1988-07 pages (5990 announced 1988-05-03); MicroPDP-11/53 (1988 versus 1991
tables); VAX 6000/310 and /410 (1989-07 and 1990-10); HP 3000 announcement,
reannouncement and series events; Sperry 1100/90 forecasts against delivery in
1983-12; UNIVAC 1100/80 delivery 1977-03 against introduction 1980-05; Apple
7500/8500 months within 1995. Configuration boundaries kept: Cyber 810A/830A is
not 810/830; DECsystems are not DECstations; CRAY-2S is not CRAY-2. Unresolved
examples: Power Macintosh 8100/100 revision order, MicroVAX 3100/90 (1993-10-12
in Wikipedia but discussed in 1992), AlphaStation 200 4/233 and 500/400, and
MIPS RC3230 versus RS3230.
