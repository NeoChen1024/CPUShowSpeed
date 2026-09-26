# Helman's 1991 SPEC89 worksheet derivative

Reviewed on 2026-09-26 against the supplied original
`comp.benchmarks.mbox.zip`. James Helman's Usenet post
`<JIM.91Mar30161055@baroque.Stanford.EDU>` prints 40 SPEC89 rows for 34
normalized system labels. Its preserved [message](data/spec89/helman-1991/source.txt)
and [row-level CSV](data/spec89/helman-1991/observations.csv) agree line by line.
The post says Helman added clock data and recent HP results to McCalpin's
`spec.sc` worksheet. The original worksheet and individual benchmark run
reports were not in the supplied package.

The [combined CSV](data/spec89/aggregate89-plus-helman.csv) preserves all 381
original source observations and appends these 40 as `R3H0001`–`R3H0040`, for
**421 source observations**. It retains the original 34 system labels, reports
all three printed scores and per-MHz columns, and distinguishes the new rows
with `measurement_type=published_worksheet_derivative` and
`import_batch=helman_1991_supplement`. No model deduplication, score replacement,
or claim of 40 independent tests is made. Normalized system names map to the
existing 160-label vocabulary; the exact printed names remain in `system_raw`.

The original post itself warns that worksheet redundancies remain and clock
numbers may be wrong. Among these 40 source rows, 25 cite note 7 (calculated
from John Mashey's *Your Mileage May Vary*), four mark their clock uncertain,
one is a labeled estimate, and one is a beta system. The source flags are
preserved in both the supplement and the combined CSV. The per-MHz values are
published worksheet calculations, not IPC or new measured timings. The post
date `1991-03-31` is a source publication date, not a test or machine launch
date.

## Verification and reproduction

The supplied mirror-hunt ZIP's 46 payload files matched its SHA-256 manifest.
The preserved Helman message matched the original MBOX bytes at the supplied
offsets and SHA-256. Every one of the 40 `source_row_raw` values matched its
numbered line in that message; the seven displayed numeric fields on each line
matched the CSV. All 11 source-note definitions were present and references
resolved. The relevant preserved files and hashes are in the
[supplement directory](data/spec89/helman-1991/README.md).

```sh
./.venv/bin/cpushowspeed spec89 merge-helman
./.venv/bin/cpushowspeed spec89 merge-helman \
  --mbox-zip /path/to/comp.benchmarks.mbox.zip
```

The first command rebuilds the tracked combined CSV from repository files;
the second also rechecks the message against the original MBOX archive.
The source package described additional mirror leads, but did not contain the
original `spec.sc`, `spec.print`, or Aburto `bench.tar.gz`. This import is the
40-row derivative table, not a recovery of those target files.
