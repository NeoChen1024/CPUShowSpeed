# Data contract

This document defines interpretation requirements. Specific implemented formats are owned by the historical-observation contract
and the [shared timeline schema](timeline.md#shared-record-contract). The [data schema](data-schema.md)
design defines where these interpretations will be stored as migration proceeds.

The shared script input is the versioned JSONL [input catalog](input-catalog.md).
Source-specific extraction formats remain provenance-bearing adapter inputs; they
are not competing fitting contracts. Historical numerical observations also retain
their source-owned observation format. No raw source is overwritten by normalization.

## Result identity

A result needs a stable source reference and an identifier within that source,
the original system and processor names, benchmark and version, metric name,
numeric value, unit, and evidence class. Preserve the reported text alongside
normalized identifiers. Record available configuration details that affect
comparability: processor count, active cores, threads or copies, clock, memory,
operating system, compiler, tuning, floating-point precision, and scalar/vector
mode. Unknown details remain unknown; they are not inferred from model names.

For parallelism, keep distinct fields for enabled hardware cores and SMT
threads, concurrently run benchmark copies, requested software threads, and
any independently observed worker/process count. An absent observed count
stays unknown. A rate copy count is not a core count or a measured worker census.

Source references must be precise enough to revisit the value: result URL or
document citation, page/table or result ID, and retrieval or transcription
details where relevant. Derived values additionally link to every input result,
the method version, and the assumptions used.

## Dates

Keep these separate when known:

- **Hardware introduction:** when the specified machine or processor became
  available, with the source and any date uncertainty.
- **Test date:** when the benchmark was run or the input timings were measured.
- **Publication date:** when the cited result appeared.
- **Reconstruction date:** when a later calculation was performed.

Write known full dates in ISO 8601 calendar form, `YYYY-MM-DD` (`%Y-%m-%d`),
including inventory and retrieval dates. If a source gives only a year or month,
retain that original precision and leave the full date unknown; do not invent a
day or month to satisfy the format.

Never silently substitute one event definition for another. The current shared
chronological view selects **CPU release → hardware availability/introduction →
era-compatible submission-era → unknown**, while preserving each candidate and its provenance.
SPEC result-publication date is an explicitly labelled submission-era proxy,
not a known submission receipt date. Reject its use for chronology when
source evidence places the hardware in a substantially different era; retain
the benchmark record and the exclusion reason. Test, document and retrieval dates remain
separate. Earlier annual reports grouped by hardware availability; those are
snapshots of the earlier policy, not retroactively CPU-year statistics.

Hardware availability in SPEC means when the last required hardware component
became available; it can be later than the CPU or system model introduction.
See the [shared timeline contract](timeline.md#cpu-first-date-selection) for
matching, uncertainty and fallback details.

[SPEC's hardware-availability field definition](https://www.spec.org/cpu2026/Docs/result-fields.html)
and [run rule](https://www.spec.org/cpu2026/docs/runrules.html#section4.2.3)
explain why availability is a configuration-level date.

## Values and validity

Historical PDF extraction now has an initial
[JSONL observation contract](../research/data/historical/README.md).
Keep reviewed values and methodological statements there; unreviewed DocIR
search hits remain in derived storage. This does not make historical ratings
eligible for the active integer-rate calibration.

Retain raw scores in their original unit and benchmark variant. Use explicit
missing values, exclusions, and uncertainty rather than zero or fabricated
coverage. Record non-compliance or withdrawals when the source discloses them.
Matching the same processor name alone does not prove that two scores describe
the same tested system. A bootstrap interval for one benchmark-generation edge
may be recorded and used as a **conditional sample margin**; it is not the
error interval of a multi-edge VAXen chain or a guarantee for one machine.
When an estimated VAXen value is exported, preserve its original reported
score, benchmark mode, factor source, evidence class, and the scope of any
interval. Mark unquantified upstream uncertainty explicitly.

## Experimental speed outputs

The dual-track experiments identify `track` (`speed` or `rate`) independently
of base/peak. Classical speed outputs use `target_unit=SPECint92_equivalent`;
rate outputs use `rate_VAXen`. Shared network nodes distinguish `observed_speed`,
`observed_rate`, `estimated_89` and `unanchored`. Mixed observed speed/rate anchors
are rejected by the shared fitter. Existing rate schemas retain their meaning.

Generation-chain speed coefficients are older-speed/newer-speed, with separate
base and peak fits (base terminates at SPECbase_int92). Cross-track diagnostic
ratios are native rate/native speed, never implicit VAXen or processor counts.
See the [experiment](../research/spec-dual-track.md) for output paths and limits.

## Joint-predictor experiment

Joint tables retain `method`, fixed `speed_weight`, `old_generation`,
`new_generation`, and `mode`. `coefficient_older_rate` maps the declared native
predictor to the older suite; `coefficient_vaxen` includes an explicit upstream
rate prefix. Held-out `observed_target_vaxen` is populated only for actual CPU92
rate targets. Other observed targets remain native older-suite rate values.
Masked-input predictions use independently fitted single-input coefficients.
See the [joint experiment](../research/spec-joint-tracks.md) for uncertainty and
insufficient-model policy.

Joint-refit rows now include `matching_scenario` and `local_matching_policy`.
Relaxed pair tiers (`platform_alias_ram_relaxed`, `cpu_clock_resources`) are
distinct from `hardware_near`; source values and `matching_blockers` /
`relaxed_fields` remain visible. Scenario-specific coefficients must not be
combined with another scenario's uncertainty arrays.

## Enabled hardware and benchmark concurrency

Enabled cores/chips, chip capacity, hardware threads/core, rate copies and speed
benchmark threads are separate quantities. Enabled counts below chip capacity are
not automatically errors. CPU92 CPU count remains a legacy matching proxy with
unverified chip equivalence. Runtime records retain mode, benchmark, quantity,
raw value, locator and source hash. Uncollected details and missing parsed fields
are distinct statuses. The [audit](../research/spec-resource-field-audit.md)
records ambiguities; metadata enrichment does not silently change fitting cohorts.

## Timeline storage

The shared timeline retains its logical `vaxen-timeline-v2` record semantics.
Its default website export uses Zstd level 3 Parquet, with explicit codecs preserving
null, empty strings, absent keys and nested evidence. JSONL/CSV are optional
exports. [Timeline storage](timeline.md#static-website-export) owns the physical
layout, browser loading, decoder pin and round-trip guarantees.

### Unparsed runtime declarations

The detail adapter preserves non-integer copies/threads tokens in
`execution_issues` and per-mode `unparsed_values`. A mode with only such values is
`unparsed_reported_value`; a mode containing both numeric and unparsed values is
`partially_parsed`. Neither supplies a verified constant count for fitting.
These differ from `not_collected` (no cached disclosure) and
`not_reported_in_parsed_table` (no usable count in the parsed result table).
Do not strip a suffix or substitute a hardware count to create a measurement.
CSV result-table headers stop at the aggregate/metadata boundary; later compiler
sections must not be read as execution data.
