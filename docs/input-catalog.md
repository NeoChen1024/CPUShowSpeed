# Shared benchmark input contract

The implemented interchange format is versioned JSONL. Source adapters own parsing;
fitters own matching, exclusions and estimation. Raw source documents are immutable.

## Files

Generate the snapshot with:

    uv run cpushowspeed inputs build

The default directory is data/derived/inputs:

| File | Purpose |
| --- | --- |
| observations.jsonl | benchmark-observation-v1: one positive metric/mode observation, normalized unit, hardware, execution evidence, source and raw record |
| sources.jsonl | benchmark-source-v1: source views needed for identity, grouping and source-specific evidence, including rows without a usable score |
| audit.json | Schema, file digests, adapter code digests, runtime-disclosure fingerprint and observation count |

These are generated files, not new primary measurements. Multiple publications
and source views remain identifiable; concatenating them into a training set would
double-count some evidence. A fitter must select its metric, source view and cohort.

An observation contains:

- Stable observation_id and source_record_id.
- Metric identity (including suite/version/precision), value, unit, track and mode.
- Hardware separately from execution: enabled cores/chips, hardware threads/core,
  legacy CPU count, and the declared benchmark copies/threads vector.
- Explicit missing-status values. Observed worker count remains null.
- Software context, evidence class, source URL/hash/locator, raw record and qualifications.

Original dates remain in source fields at their stated precision. The timeline's
shared chronology layer owns CPU/hardware/publication date selection; this catalog
does not silently select a plotting year or relabel hardware availability as CPU release.

## Consumers

SPEC92–2026 normalization has one owner: spec_inputs.py. Existing imports from
spec_rate_fit, spec92_rate_fit and spec_dual_track are compatibility entry points,
not separate implementations. Fitting and timeline code use the same source
record values and execution-disclosure adapter.

Classical metric extraction has one owner in benchmark_records.py, reusing the
existing LINPACK column parser. Dhrystone versions and Whetstone precision variants
stay separate. Reviewed PDF vectors and Gibson/ADP records use source-specific
adapters into the common envelope. Unit conversion and frequency assumptions are
not part of the generic JSONL reader.

The SPEC fit readers and classical network, mix-network and target-comparison
readers accept a shared frozen snapshot:

    uv run cpushowspeed --input-catalog data/derived/inputs bridge fit-joint-tracks --matching-policy ram-aliases
    uv run cpushowspeed --input-catalog data/derived/inputs classic network-fit
    uv run cpushowspeed --input-catalog data/derived/inputs classic mix-network-fit
    uv run cpushowspeed --input-catalog data/derived/inputs plot timeline

Without --input-catalog, the same adapters read their original cached sources.
The snapshot is hash checked before use. Matching/review tables remain separate
policy inputs; the snapshot is not a replacement for aliases, pairing approvals
or a calibration bundle. Legacy diagnostic commands retain their documented
source-native interfaces; they are not silently redirected by this option.

## Execution-count admission

All shared SPEC pair generation applies
reject-known-uniform-count-conflicts-v1 separately to base and peak:

- Same-track, same-quantity, reported constant counts that disagree:
  confirmed_count_conflict. Preserve scores and the unfiltered ratio; exclude
  only this mode's ratio from fitting.
- Equal reported constant counts: equal_declared_count. This is not a claim
  of complete hardware/software equivalence.
- Missing counts: unverified. Retain provisionally.
- Counts varying across benchmarks: nonuniform_requires_review. Do not compare
  minima/maxima as if they described equivalent workload vectors.
- Different tracks/quantities: no copies-versus-threads equality test.

For joint predictors, compare the older and newer rate inputs; a conflict removes
that mode's tuple from all three predictor fits on the shared cohort. Never divide
or multiply a measured SPEC score by copies or clock frequency.

The runtime fingerprint detects newly collected as well as changed disclosures.
A saved joint model is refused when its input fingerprint is stale. Unknown
execution configurations and software/systematic differences remain outside CI95.

## Migration verification

The initial migration checked exact numeric/identity parity for 53,961 SPEC source
records and 3,794 classical records before enabling the execution guard. The catalog
contains 103,456 positive observations; source views preserve the other context.

Before/after coefficient comparison:

    uv run cpushowspeed inputs compare-factors

[Migration and fitting review](../research/input-unification-fitting-review.md)
owns results, per-model decisions and the coefficient change table.
