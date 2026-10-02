# Why Xeon Platinum 8280 is absent from the annual speed leader list
> Archived speed-era research, retained for its source-checked observations.
> Its fitting and plotting commands are retired; it is excluded from the active rate analysis.
> Present-tense descriptions below refer to the original 2026-09-26 research snapshot.

Checked on 2026-09-26 against four original SPEC CPU2017 disclosures. The
[machine-readable comparison](data/spec/cpu2017-8280-e2278g-comparison.csv)
retains each mode's reported score, enabled hardware, requested threads or
copies, availability/test dates, and original source URL. These are two named
ASUS systems; the speed and rate disclosures use different benchmark workloads
and different parallelism settings, so their raw scores are not interchangeable.

| System | SPECspeed2017_int base / peak | Speed threads requested | SPECrate2017_int base / peak | Rate copies | Enabled hardware |
| --- | ---: | ---: | ---: | ---: | --- |
| [ASUS ESC8000 G4, Xeon Platinum 8280](https://www.spec.org/cpu2017/results/res2020q3/cpu2017-20200915-23985.html) | 12.1 / 12.3 | 56 | [391 / 407](https://www.spec.org/cpu2017/results/res2020q3/cpu2017-20200915-23984.pdf) | 112 | 2 chips, 56 cores |
| [ASUS RS300-E10, Xeon E-2278G](https://www.spec.org/cpu2017/results/res2019q4/cpu2017-20191209-20287.html) | 12.4 / 12.7 | 8 | [61.4 / 64.6](https://www.spec.org/cpu2017/results/res2019q4/cpu2017-20191209-20286.pdf) | 16 | 1 chip, 8 cores |

The 8280 system is **6.37×** higher in base rate (`391 / 61.4`) and **6.30×**
in peak rate (`407 / 64.6`). Its speed score is slightly lower: the E-2278G
system's base/peak are **2.48% / 3.25%** above the 8280 system's. SPEC's
[CPU2017 overview](https://www.spec.org/cpu2017/Docs/overview.html) defines
speed as the time for one benchmark copy, with optional OpenMP threads, and
rate as throughput from multiple concurrent copies. The submitted thread and
copy counts demonstrate that the annual speed chart did not silently reduce
the 8280 to one core. They do **not** prove which microarchitectural or software
factor caused the small speed difference. The systems have different CPU clock,
chip count, SMT setting across run modes, memory, compiler/tuning, and test
date; individual subtests have different scaling.

The current annual figure and VAXen chain cover **integer speed**, because that
is the project's one-workload completion-time track. For the user's notion of
whole-machine capacity, a **separate integer-rate track** is needed. Never put
SPECrate scores on the existing speed-to-VAXen axis without a new rate-specific
reference and cross-generation calibration. CPU2006/2017/2026 rate copies and
runtime configuration would also need their own parser and review.

## Hardware-date contradiction found during the leader audit

The [SPEC CPU2017 result](https://www.spec.org/cpu2017/results/res2021q4/cpu2017-20211025-29885.html)
for a Supermicro system with AMD EPYC 7313 reports `HW Avail = Aug-2019`, but
[AMD dates the EPYC 7313 launch to 2021-03-15](https://www.amd.com/en/products/processors/server/epyc/7003-series/amd-epyc-7313.html).
The tested configuration cannot have been generally available before its CPU.
The [date audit row](data/archive/legacy-dates/spec/hardware-date-exclusions.csv)
(archived 2026-10-02; now a `result_date` review) preserves both
sources. The original SPEC scores and date remain in the derived per-result
record CSV, marked `hardware_date_conflict`; that result is excluded from
annual hardware-year boxes and leaders pending clarification. No replacement
year was invented. Its base score `12.4` had been tied with E-2278G and
E-2288G, but the previous deterministic URL tie-break selected the misdated
submission as the single displayed 2019 leader. The updated statistics and
leader CSV report tie counts and tied processor names. After the exclusion,
E-2278G and E-2288G are tied at base `12.4` and peak `12.7` for 2019.

The 8280 was still competitive: among the included 2019 integer-speed
submissions, its best base `12.1` and peak `12.3` each have only six submitted
results with a higher reported score. The annotated figure shows only the
annual maximum, so a near-leading machine need not appear by name.
