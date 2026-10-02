# Date events and chronology selection

Reviewed: 2026-10-02. Status: **implemented** as step 3 of the
[data schema](../docs/data-schema.md#migration-plan). The selection replaces the
timeline's private date code but is not yet consumed by any page; the former
timeline (built before the 2026-10-02 removals) serves as the comparison.

## Reproduce

```sh
uv run cpushowspeed data extract-mentions   # also result-records.jsonl and model-years.jsonl
uv run cpushowspeed data build              # result_chronology and consistency_finding
```

`data import-dates` performed the one-time conversion into `date_event.jsonl`
(and the entities, aliases and sources it needs); it refuses to overwrite curated
events without `--force`.

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
| CPU release | 74,513 |
| Hardware | 27,302 |
| Fallback proxy | 86 |
| Unknown | 1,555 |

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

## Known gaps

- CPU92 **speed** results in the input catalogue carry no date fields (139 results
  unknown); the adapter dropped them.
- LINPACK, Dhrystone, SPEC89 and DEC-report rows without a dated model stay unknown.
- The Elliott 905 rule rejects a compilation year rather than giving one; it waits
  for the step-4 `review` table and is not applied.
- Catalogue spelling variants need exact-text aliases to recover the 161 losses.
