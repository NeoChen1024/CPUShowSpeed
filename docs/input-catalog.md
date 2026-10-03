# Shared benchmark input contract

Source adapters (`input_catalog.records`) own parsing into one observation
envelope, `benchmark-observation-v2`; fitters own matching, exclusions and
estimation. Raw source documents are immutable.

## Files

`cpushowspeed data extract` runs every adapter and writes the extracted
observations, which `data build` loads into the database `observation` table.
The [data schema](data-schema.md) owns that table and the built database. The
former standalone snapshot (`inputs build`, `observations.jsonl`/`sources.jsonl`
under `data/derived/inputs` and the global `--input-catalog` option) was removed
on 2026-10-02 (schema step 5d).

Extracted observations are generated data, not new primary measurements. Multiple publications
and source views remain identifiable; concatenating them into a training set would
double-count some evidence. A fitter must select its metric, source view and cohort.

An observation contains:

- Stable observation_id and source_record_id.
- Metric identity (including suite/version/precision), value, unit, track and mode.
- Hardware separately from execution: enabled cores/chips, hardware threads/core,
  legacy CPU count, and the declared benchmark copies/threads vector.
- Explicit missing-status values. Observed worker count remains null.
- Software context, evidence class, source URL/hash/locator, raw record and qualifications.

Original dates remain in source fields at their stated precision. The database
`result_chronology` view owns CPU/hardware/publication date selection; adapters
do not select a plotting year or relabel hardware availability as CPU release.

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

The SPEC and classical fitters read the built database (`observation_store`,
`classical_store`), not the adapters directly. Matching/review tables remain
separate policy inputs in `data/curated/`.

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

Never divide or multiply a measured SPEC score by copies or clock frequency.
Unknown execution configurations and software/systematic differences remain
outside CI95.

## Migration verification

Historical record (2026-09): the initial migration checked exact numeric/identity parity for 53,961 SPEC source
records and 3,794 classical records before enabling the execution guard. The catalog
contains 103,456 positive observations; source views preserve the other context.

Before/after coefficient comparison:

    uv run cpushowspeed inputs compare-factors

It writes `factor-changes.csv` and `model-review.csv` under
`data/derived/input-unification/`, outside Git. The one-time migration review that compared factors before and after
unification is in Git history.
