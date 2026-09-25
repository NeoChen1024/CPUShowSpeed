# Data contract

This document defines interpretation requirements. The physical storage schema
and serialization format are not yet selected.

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
threads, configured or requested benchmark threads, concurrently run copies,
and any independently observed worker/process count. An absent observed count
stays unknown. In particular, a `SPECspeed` result with one copy is not
necessarily one-thread performance, and a reported `Threads` value describes
the requested/allowed setting rather than an exact runtime worker census.

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

Never substitute one date for another. A historical plot must state which date
is on its horizontal axis. A manual reconstruction of an older machine is not
a measurement made in its introduction year.

## Values and validity

Retain raw scores in their original unit and benchmark variant. Use explicit
missing values, exclusions, and uncertainty rather than zero or fabricated
coverage. Record non-compliance or withdrawals when the source discloses them.
Matching the same processor name alone does not prove that two scores describe
the same tested system.
