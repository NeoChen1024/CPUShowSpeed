# Track 2 — SPEC92 through SPEC2026 speed and rate

The [rate fitting report](../spec95-spec2026-rate-fitting.md) owns the current
five adjacent-suite fits and full-chain uncertainty. The filename predates the
CPU92 expansion; its contents cover CPU92 through CPU2026.

- Input: original integer-rate base/peak submissions; copies and configuration
  metadata remain distinct from processor/core counts.
- Fit direction: older score = k × newer score, with no intercept and grouped
  geometric log-ratio estimation. The chain converts later scores to CPU92.
- Normalization: the defined CPU92 factor then yields VAXen.
- Status: implemented conditional estimates; CPU2026 overlap remains sparse.

[Collection commands](../../docs/spec-collection.md) own reproduction details.
[CPU92 recovery](../spec92-archive-expansion.md) owns the early rate archive.
[Annual results](../annual-rate-vaxen.md) own distributions, leaders and pointwise
uncertainty. Their year is tested-configuration hardware availability, not
necessarily CPU launch or submission year. No unmeasured years are filled in.

Supporting numerical snapshots live under `research/data/spec/`; full generated
submissions and plots live under `data/derived/spec/`. Registry model and dataset
IDs connect these artifacts to the classical/historical extensions.

The [independent speed experiment](../spec-dual-track.md) is implemented alongside
this rate series. It exports SPECint92-equivalent points, separate from rate-VAXen.
