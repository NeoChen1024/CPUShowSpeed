# CPU SKU release chronology catalog

Reviewed: 2026-10-02. Status: **catalog built and audited; converted into
`processor_sku` and `date_event` rows** of the [data schema](../docs/data-schema.md)
(steps 2–3), through which the timeline now selects CPU release years. The
generating command and its output files were retired on 2026-10-02 (step 5d);
the sections below describe the catalog as built.

## Purpose

The shared timeline selects CPU release before hardware availability, but its
reviewed CPU mapping covers only 99 historical configurations. Every modern SPEC
record therefore uses hardware availability. This catalog supplies SKU-level
release dates for Intel Xeon, AMD Opteron and AMD Epyc, which together cover
52,571 of the 58,813 SPEC92–2026 integer-rate records.

## Reproduce

The former `research cpu-chronology` command (removed 2026-10-02) fetched pages once through the Wikipedia API and cached with revision ID
and SHA-256 under `data/derived/documents/cpu-chronology/`; reruns parse the
cache. `--refresh` refetched. It wrote the
[catalog](data/archive/legacy-dates/historical/cpu-sku-chronology.csv),
[source revisions](data/archive/legacy-dates/historical/cpu-sku-sources.json) and
[audit](data/archive/legacy-dates/historical/cpu-sku-audit.json), now archived. Field definitions are in the
[archive README](data/archive/legacy-dates/README.md).

Wikipedia is an accepted secondary source for model dates under the
[hardware chronology policy](../docs/sources.md#hardware-chronology-sources).
Rows are parsed, not individually reviewed.

## Catalog

22 pages; 1,423 rows; 1,352 SKU keys. Each row keeps the table's date at its
stated precision (day, month or year; quarters keep only the year) and the raw
cell text. Gaps:

| Generation | Reason |
| --- | --- |
| P6, Yonah, most NetBurst Xeons | Tables identify parts by clock ("Xeon 2.8"), not model number |
| Sapphire, Emerald, Granite Rapids | Tables have no per-SKU release date |
| Epyc Milan | Table has no release date column |

Family launch dates from page prose were not substituted for missing SKU dates.
30 SKU keys have release years more than one year apart, mostly Opteron model
numbers sold in several revisions (for example 130 nm and 90 nm parts); all
dates are retained.

## Matching rule (`sku-key-v1`)

Refined on 2026-10-02 before first use (all parentheticals removed, attached
Opteron suffixes split); current coverage is reported by the resolution table in
[processor identity](processor-identity.md). The coverage table below predates it.

A processor string matches only when it names exactly one Xeon, Opteron or
Epyc SKU after removing trademarks, "processor" and clock/bus parentheticals.
Tier words are part of the key: Xeon 5120 (2006) and Xeon Gold 5120 (2017) are
different SKUs. Multi-SKU text and family-only text ("Intel Xeon (533 MHz
system bus)") do not match. Table cells such as "7443 (P)" yield two SKUs.

When both sides give a clock, the record's nominal clock must lie within 2% of
a catalog base frequency; otherwise the SKU date is not used.

## SPEC coverage (2026-10-02, before the rule refinement)

This table was produced by the since-removed `--coverage` audit.

| Generation | Matched | Not a single SKU | SKU not in catalog | Clock conflict |
| --- | ---: | ---: | ---: | ---: |
| CPU92 | 0 | 473 | 0 | 0 |
| CPU95 | 0 | 1,543 | 0 | 0 |
| CPU2000 | 1,904 | 2,649 | 228 | 6 |
| CPU2006 | 26,906 | 2,263 | 29 | 75 |
| CPU2017 | 15,640 | 257 | 6,547 | 0 |
| CPU2026 | 143 | 13 | 137 | 0 |
| **Total** | **44,593** | **7,198** | **6,941** | **81** |

CPU2017/2026 gaps are dominated by Sapphire/Emerald/Granite Rapids and Milan.
CPU92/95 and non-x86 processors (SPARC, POWER, PA-RISC, Itanium, Alpha) are
outside this catalog.

The 81 clock conflicts were inspected. They include overclocked runs (Xeon X5680
at 4.2 and 4.5 GHz against a 3.33 GHz base), apparent clock typos (E5-2640 v4 at
3.4 GHz) and FSB rounding (E5310 at 1666 against 1600 MHz). All fall back to
hardware dates.

## Checks performed

- **Independent spot check** against Intel ARK launch quarters. Only X5670 was
  read directly from its ARK page; the others are from search summaries of ARK
  pages.

  | SKU | Catalog | ARK | Agreement |
  | --- | --- | --- | --- |
  | Xeon X5670 | 2010-03-16 | Q1'10 | yes |
  | Xeon E5405 | 2007-11-11 | Q4'07 | yes |
  | Xeon E5-2690 | 2012-03-06 | Q1'12 | yes |
  | Xeon Gold 6130 | 2017-07-11 | Q3'17 | yes |
  | Xeon E5-2620 v4 | 2016-04 | Q1'16 | year only |

- **Date-cell audit**: every raw cell matches a recognized date pattern; no cell
  contains a price.
- **Parser defects found and fixed during this review**: a "Release price"
  column was once taken as the date column, and a bare-year fallback read "$2010"
  as a year (Epyc 7443 dated 2010); an "Released" header was missed after a first
  fix (309 Opteron rows lost, then restored). These were found only by comparing
  the timeline before and after a trial integration.

## Trial integration (not adopted)

A trial wiring into `CPUChronology`, using an earlier catalog that still had the
price defect, changed no VAXen value and moved 93,005 of 121,365 timeline records
from hardware to CPU dates; 20,814 changed year. Most moved one year earlier.
Two patterns need rules before adoption:

- SKU release **after** the record's hardware availability (for example Cascade
  Lake Refresh "R" SKUs released 2020-02-24 in systems with 2019-04
  availability; Opteron 2220 at 2007-02 versus 2006-10). These are source
  conflicts to report, not to resolve silently.
- Old SKUs tested years later (Xeon E5-2620 in a 2019 CPU2017 system) move many
  years earlier. This is the intended CPU-first behavior and should be visible.

The trial was reverted; the planned `consistency_findings` view in the
[data schema](../docs/data-schema.md#built-views-and-consistency-checks) defines
where these conflicts will be reported.
