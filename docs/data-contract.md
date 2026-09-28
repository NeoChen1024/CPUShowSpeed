# Data contract

This document defines interpretation requirements. Specific implemented formats are owned by the historical-observation contract
and the [shared timeline schema](timeline.md#shared-record-contract).

Source-checked values and other observations recovered from historical documents
should be stored in a form scripts can read and process. Select the concrete
schema and serialization format when historical PDF and KIPS extraction starts;
CSV, JSONL, and JSON remain candidates. Until then, the fields below describe
information to preserve, not a prescribed file layout. Existing checked examples
in research notes should be migrated into the chosen format at that point.

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
