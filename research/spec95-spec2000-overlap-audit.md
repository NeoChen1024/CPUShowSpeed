# Why the SPEC95/CPU2000 joint overlap is small

Reviewed: 2026-09-29.

## Finding

The joint bridge is constrained by **three-way configuration coverage**, not a
complete absence of cross-generation scores. Its one-CPU-model baseline combines
strict lexical identity, equal RAM and equal enabled CPU resources. Some losses
are recoverable naming/RAM restrictions; others are real coverage or resource
conflicts, including an officially withdrawn speed result.

Neither the existing rate-to-rate nor speed-to-speed chain is disconnected.
No production matches, coefficients or public timeline values were changed by
this audit. Candidate aliases remain review data; source field agreement is
not certification of identical OS/compiler/cache/run conditions.

## Collection completeness within the cache

The cached CPU95 bulk contains 2,574 result IDs; CPU2000 contains 7,654.
Both agree exactly with the cached quarterly-index manifest: zero missing IDs,
invalid links or duplicate IDs. This checks our cached official collection,
not the existence of unpublished/vendor/third-party measurements elsewhere.
See [index coverage](data/spec/95-2000-audit/index-coverage.json).

The relevant usable populations are 773 CPU95 integer-rate, 1,374 CPU2000
integer-speed and 2,481 CPU2000 integer-rate submissions. Seven speed and twelve
rate rows in CPU2000 have no positive aggregate in the bulk. None of these 19
exclusions is due to an unparsed chip count or missing processor name. Their
original fields and URLs are in [collection exclusions](data/spec/95-2000-audit/collection-exclusions.csv).

## Matching ablations

Counts below are **per mode**; base and peak have the same eligibility in this
slice. A triple contains CPU95 rate, CPU2000 speed and CPU2000 rate. Every side
must satisfy the selected rule. All repeat submissions remain; a triple is not
an independent hardware sample.

| Admission rule | Triples | CPU95 system names | CPU models | CPU/chips/clock configurations |
| --- | ---: | ---: | ---: | ---: |
| Current strict matching | 2 | 1 | 1 | 1 |
| Allow different RAM only | 5 | 4 | 2 | 3 |
| Candidate aliases only; equal RAM | 4 | 3 | 1 | 2 |
| Different RAM + candidate aliases | **10** | **9** | **3** | **5** |
| Ignore platform identity and RAM, retain CPU/clock/resources | 72 | 14 | 3 | 5 |

The last row is a diagnostic, not an admissible cohort: for example, sharing a
CPU does not make an AlphaServer and an AlphaStation the same platform.
Relaxed rules still preserve clock agreement and enabled-resource consistency.
Separate resource-ignoring diagnostics are exported but must not be used as
same-configuration evidence.

The three recovered CPU labels are **21264, 21264A and UltraSPARC II**. They
cover two broad architecture families and only five clock/resource configurations.
The nominal three-model threshold would be met by the candidate cohort, but that
alone would not establish a broadly transportable calibration.

Full [ablation counts](data/spec/95-2000-audit/ablation.csv),
[blocker counts](data/spec/95-2000-audit/blockers.csv) and
[alias candidates](data/spec/95-2000-audit/alias-candidates.csv) are machine-readable.

## 1. Equal RAM removes genuine configuration candidates

At the existing exact-system/CPU/chip candidate boundary:

- CPU95 rate → CPU2000 speed: 15 pairs, seven blocked by RAM and one by clock;
  seven pass the current hardware-near rules.
- CPU95 rate → CPU2000 rate: 25 pairs, eight blocked by RAM and one by clock;
  sixteen pass.

No missing RAM field explains these rejected pairs: the values differ.
Examples with otherwise matching model/CPU/clock/count include:

| System | CPU95 rate RAM | CPU2000 speed RAM | CPU2000 rate RAM |
| --- | ---: | ---: | ---: |
| AlphaServer DS10 6/600, 616 MHz, 1 CPU | 2 GB | 1 GB | 1 GB |
| AlphaServer ES40 6/667, 1 CPU | 4 GB | 4 GB | 16 GB |
| Sun Enterprise 3500/4500, 400 MHz, 1 CPU | 2 GB | 8 GB | 8 GB |

The project previously accepted considering RAM differences. The generic
matcher still enforces equality; this audit exposes that remaining implementation
restriction. RAM relaxation should be an explicit named scenario, retaining
both reported amounts and uncertainty about memory-system effects.

## 2. Names hide available results

Examples of recoverable lexical candidates:

- `AlphaServer GS160 6/731` versus `AlphaServer GS160 Model 6/731`.
- The corresponding GS320 naming difference.
- `Compaq AlphaServer DS20` versus `AlphaServer DS20 Model 6/500`.
- `AlphaServer ES40` versus `AlphaServer ES40 Model 6/500`.
- `Professional Workstation XP1000` versus `AlphaStation XP1000 Model 6/667`.

For the first two, disclosed CPU type, 731 MHz clock, one enabled CPU and 4 GB
RAM agree. The GS160 [CPU95 rate disclosure](https://www.spec.org/cpu95/results/res2000q2/cpu95-20000605-04245.html)
and [CPU2000 speed disclosure](https://www.spec.org/cpu2000/results/res2000q2/cpu2000-20000511-00103.html)
show the extra `Model` token. These records were already present in the bulk.

The audit's candidate normalizer removes `Compaq` and `Model`, removes a trailing
`6/clock` suffix only when its number agrees with the reported clock, and proposes
an XP1000 branding alias. It retains model variants such as DS20 versus DS20E.
The processor alias candidate removes a leading MIPS label from R-series names.
These are explicit diagnostics, not a general fuzzy match or approved alias table.

## 3. Speed and rate often enable different numbers of CPUs

There are 28 exact system-name groups shared between CPU95 rate and at least
one CPU2000 track. Eight have only CPU2000 speed under that name; thirteen have
only CPU2000 rate. Some names themselves include processor counts, so these
categories are not proof of a missing benchmark for the wider product family.
See [system coverage](data/spec/95-2000-audit/system-coverage.csv).

HP N4000 at 552 MHz illustrates a real resource mismatch: CPU2000 speed reports
one enabled CPU; the available CPU2000 rate results have 2, 4 or 8. Its
[speed disclosure](https://www.spec.org/cpu2000/results/res2000q1/cpu2000-20000313-00044.html)
and [two-CPU rate disclosure](https://www.spec.org/cpu2000/results/res2000q1/cpu2000-20000313-00045.html)
confirm the counts. Several IBM system names similarly separate 1-CPU speed
from multi-CPU rate configurations.

Ignoring chip/core differences increases counts but changes the experiment:
it would require an explicit resource-conditioned model, not a same-configuration
bridge. The label `2X` in a machine name does not override the disclosed enabled
CPU count. No unmeasured rate score is synthesized by multiplying speed by CPUs.

## 4. SGI has an unavailable numeric result, not a missed download

The CPU2000 [SGI 2200 2X 400 MHz result](https://www.spec.org/cpu2000/results/res1999q4/cpu2000-19991130-00023.html)
reports two enabled chips but marks both integer aggregates **NC**. SPEC's notice
attributes noncompliance to the three-month availability rule after a system
availability change. The bulk encodes the unavailable aggregates as zero.
Those zeros are not measured performance, and the current page provides no
aggregate to use in the fit.

The later [positive speed result](https://www.spec.org/cpu2000/results/res2000q2/cpu2000-20000509-00095.html)
uses one enabled chip despite the `2X` model title; the
[positive rate result](https://www.spec.org/cpu2000/results/res2000q2/cpu2000-20000509-00097.html)
uses two. CPU labeling (`MIPS R12000` / `R12000`) and RAM also differ across
some records. Fixing those naming/RAM differences cannot by itself resolve
this active-resource conflict. A recovered pre-withdrawal result would need
separate historical qualification, not automatic promotion to a valid submission.

## 5. Clock and CPU descriptions also need preservation

Sun Enterprise 450 candidates include 400 MHz versus 480 MHz, which is a real
frequency mismatch. This audit does not apply a classical-benchmark clock-scaling
assumption to SPEC. IBM 44P-270 also has Power3 versus Power3-II wording; this
requires review and cannot justify merging processor revisions automatically.
Neither factor is solved by removing all punctuation from system names.

## Source verification and reproduction

Forty selected original disclosures were cached and checked. Thirty-nine usable
records agree with the bulk on model, CPU description, clock, chip count and
memory. The remaining disclosure is the SGI NC record. This verifies the
fields that explain the matching losses, not complete runtime equivalence.
[Disclosure checks](data/spec/95-2000-audit/disclosure-checks.csv) retain source
URLs, SHA-256, hardware-table field locators and extracted values.

```sh
uv run --no-sync cpushowspeed bridge audit-95-2000 --fetch-review
uv run --no-sync cpushowspeed spec verify --generation cpu95 --generation cpu2000
```

Omit `--fetch-review` to work with cached documents only; missing documents then
remain explicitly unreviewed. The audit writes versioned small tables under
`research/data/spec/95-2000-audit/` and full candidate/source/triangle exports
under ignored `data/derived/spec/95-2000-audit/`. It does not modify source scores.

## Follow-up implementation

The user authorized broader matching. A relaxed RAM/alias and CPU-clock fitting
study followed; it was removed with the other diagnostic experiments on
2026-10-02. This original admission audit and strict baseline remain. Resource/count conflicts and NC exclusions remain.
The expanded Alpha/Sun cohort is still small and conditional; broader CPU
coverage requires additional measured overlaps.
