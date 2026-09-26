# Classic collection and overlap snapshots

`acquisition.csv` inventories downloaded sources and hashes, not measurements.

`overlap-summary.csv`, `overlap-models.csv`, `overlap-coverage.csv` and
`overlap-audit.json` are compact outputs of `cpushowspeed classic overlap-spec`.
Full records and pairs remain in the ignored derived output directory. After
a reviewed rerun, copy `summary.csv`, `model-summary.csv`, `source-coverage.csv`
and `audit.json` to these four snapshot filenames respectively.

All model matches remain candidates. Keep conflicting/missing-clock pairs
and repeated source rows; they are not automatically independent experiments.
See the [overlap audit](../../classic-spec-overlap.md) for coverage limits.
