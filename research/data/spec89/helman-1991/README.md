# Helman SPEC89 worksheet derivative (1991-03-31)

This supplement preserves 40 rows published by James Helman in the Usenet post
`<JIM.91Mar30161055@baroque.Stanford.EDU>`, `SPECmarks/MHz (was Re: More
Snake bytes.)`. The post says he added clock frequencies and recently posted
HP scores to McCalpin's `spec.sc` worksheet. The worksheet itself and the
underlying run disclosures were not recovered. These are **source observations
of a published derivative table**, not 40 independent certified SPEC runs.

- `source.txt`: original archived Usenet message bytes, independently compared
  with `comp.benchmarks.mbox.zip` at the offsets in `source-manifest.csv` on
  2026-09-26.
- `observations.csv`: all 40 printed rows, with reported scores and per-MHz
  values at original display precision, line numbers, note references, and
  estimate/beta/uncertain-clock flags.
- `source-notes.csv`: the 11 source notes printed below the table.
- `source-manifest.csv`: original MBOX member, byte offsets, Message-ID, and
  message SHA-256.
- `provenance.json`: SHA-256 of the user-supplied mirror-hunt ZIP from which
  these four files were copied.

The original post warns that worksheet redundancies had not been removed and
some clock numbers could be wrong. Twenty-five rows cite source note 7,
"Calculated from 'Your Mileage May Vary'". One row is an estimate, one is a
beta system, and four have uncertain clock labels. Per-MHz columns are copied
source values, **not** CPU IPC. No test date was supplied.

Regenerate the tracked combined table from this supplement and the immutable
v2.0.0 aggregate:

```sh
./.venv/bin/cpushowspeed spec89 merge-helman
```

To additionally compare the preserved message with the original supplied
MBOX archive:

```sh
./.venv/bin/cpushowspeed spec89 merge-helman \
  --mbox-zip /path/to/comp.benchmarks.mbox.zip
```

The result is [`../aggregate89-plus-helman.csv`](../aggregate89-plus-helman.csv):
381 previous source observations plus these 40, each with its original
`record_id` and provenance. Repeated machines are retained. The original
v2.0.0 snapshot and its checksums remain unchanged.
