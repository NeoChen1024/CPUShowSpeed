# Classical speed-VAXen prediction

The timeline and its offline calculator predict **peak SPECint92 speed** from any
nonempty subset of six classical metrics. Peak SPECint92 is speed-VAXen by
definition (VAX-11/780 = 1, the SPEC92 reference machine), and each prediction
carries a conditional calibration CI95. Classical routes are anchored to speed,
not rate (user decision 2026-10-03); see the
[SPEC integer-speed chain](../research/spec-chains.md#speed-chain). Prediction reads
an existing calibration bundle and performs no fitting or network access. The
[network experiment](../research/classical-fits.md#sparse-network) owns coefficient
estimation and empirical limitations. The command-line calculators
(`predict classical`, `predict spec-rate`, `classic predict-speed` and
`convert-rate`) were removed on 2026-10-03; the
[calculator tab](timeline.md#offline-vaxen-calculator-2026-09-29) replaces them.

## Inputs

| Metric | Unit |
| --- | --- |
| Dhrystone 1.1 | DMIPS |
| Dhrystone 2.1 | DMIPS |
| Whetstone single precision | MWIPS |
| Whetstone double precision | MWIPS |
| Whetstone source-native precision | MWIPS |
| LINPACK n=100 | MFLOPS |

All supplied measurements should describe the same target machine/configuration
and frequency. Values must be finite and positive. Missing values are omitted,
not represented as zero. Native Whetstone remains distinct from SP. No implicit
KIPS/KWIPS or Dhrystones-per-second conversion is performed.

## Calculation and uncertainty

Each score gives `V_b = A_b * score_b^beta_f`: a power law (Dhrystone versions share an
exponent; each Whetstone precision has its own), whose intercept places the VAX-11/780's measured score at 1
speed-VAXen. Give available benchmark families equal
weight and split a family's weight equally across its supplied versions. The
combined speed-VAXen estimate is the weighted geometric mean of `V_b`. For example,
Dhrystone 1.1 + Dhrystone 2.1 + LINPACK get weights 1/4, 1/4 and 1/2.

For CI95, apply those same weights to each **joint** bootstrap replicate of
intercepts and exponents and take the linear 2.5/97.5 percentiles of the final estimates. Do
not geometrically combine marginal interval endpoints or treat coefficients
as independent. The interval describes conditional calibration uncertainty,
not an individual-machine prediction interval, source-score error or unknown
architecture/compiler bias. Output is explicitly a model prediction, not a
reported SPEC result. Base (SPECbase_int92) prediction is not supplied by this model.

## Calibration selection and portability

The timeline uses the `linear_clock` scenario and `with_spec89` cohort; the
bundle also holds `reported_clock` and `spec92_only` runs. Scenario selects the
training/calibration experiment; **supplied scores are not frequency-scaled
again**. The original linear-clock fit applied its qualified CPU-identity rule.

Bundle directory: `data/derived/classic/network-fit/`. The three required files are:

- `coefficients.csv` — exponents, speed-VAXen at unit score and score units.
- `coefficient-log-draws.npz` — correlated intercept and exponent draws.
- `prediction-calibration.json` — schema (version 3), form, target metric, normalization, ordered
  metric columns for each scenario/cohort, and SHA-256 hashes of the two files.

The coefficient CSV alone is insufficient for an exact joint bootstrap CI95.
A missing or mismatched bundle fails with an actionable error rather than
silently dropping uncertainty or guessing column order. To generate it using
the locally prepared experiment inputs:

```sh
uv run --no-sync cpushowspeed classic network-fit
```

All 63 nonempty subsets are exercised by tests. Additional tests check family
weights, cancellation of perfectly anticorrelated calibration errors, the
speed-VAXen output contract, invalid values and stale calibration files.

## Batch historical plot

`cpushowspeed plot timeline` applies this prediction contract to every
one-processor classical result in the built database and adds the saved SPEC89
bridge speed-VAXen estimates; see the [timeline contract](timeline.md). The former
`classic historical-timeline` command was removed on 2026-10-02.
