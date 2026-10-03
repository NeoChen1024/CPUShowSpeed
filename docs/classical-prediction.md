# Predict speed-VAXen from classical scores

`cpushowspeed classic predict-speed` accepts any nonempty subset of six metrics
and predicts **peak SPECint92 speed**, which is speed-VAXen by definition
(VAX-11/780 = 1, the SPEC92 reference machine), with conditional calibration
CI95. Classical routes are anchored to speed, not rate (user decision 2026-10-03);
see the [SPEC integer-speed chain](../research/spec-speed-chain.md). It reads an existing calibration bundle; prediction performs no fitting
or network access. The [network experiment](../research/classic-network-fitting.md)
owns coefficient estimation and empirical limitations.

## Common prediction entry point

`cpushowspeed predict classical` exposes the same classical prediction command.
`cpushowspeed predict spec-rate GENERATION MODE SCORE` exposes the existing SPEC
integer-rate converter, supporting 92, 95, 2000, 2006, 2017 and 2026, with
`base` or `peak` and `--format json|text`; it returns rate-VAXen. Both paths read
saved calibration and return their own quantity plus conditional CI95. SPEC speed
conversion (speed-VAXen) is currently available in the timeline and its offline
calculator, not as a CLI command. For example:

```sh
uv run cpushowspeed predict spec-rate 2017 base 11800 --format text
uv run cpushowspeed predict classical --dhrystone-1-1 10 --format text
```

`convert-rate` remains an alias of `predict spec-rate`; `classic predict-speed`
replaced `classic predict-rate` on 2026-10-03. SPEC speed, FP and SPEC89 scores
are not rate inputs. SPEC2026 retains the sparse-calibration limitations
described in the rate-chain research. The classical path targets peak SPECint92
speed; the SPEC path retains the supplied base/peak mode. Speed-VAXen and
rate-VAXen are parallel quantities and are never converted into each other. Their JSON output schemas and calibration-scenario
options remain route-specific. These commands do not combine SPEC and classical
measurements into an additional joint prediction.

## Inputs

| Option | Metric | Unit |
| --- | --- | --- |
| `--dhrystone-1-1` | Dhrystone 1.1 | DMIPS |
| `--dhrystone-2-1` | Dhrystone 2.1 | DMIPS |
| `--whetstone-sp` | Whetstone single precision | MWIPS |
| `--whetstone-dp` | Whetstone double precision | MWIPS |
| `--whetstone-native` | Whetstone source-native precision | MWIPS |
| `--linpack-100` | LINPACK n=100 | MFLOPS |

All supplied measurements should describe the same target machine/configuration
and frequency. Values must be finite and positive. Missing values are omitted,
not represented as zero. Native Whetstone remains distinct from SP.

For raw Dhrystones/second, pass `--dhrystone-unit dhrystones-per-second`; this
applies /1757 to either supplied Dhrystone version and records the original
inputs. No implicit KIPS/KWIPS conversion is performed for other options.

## Examples

One available measurement:

```sh
uv run --no-sync cpushowspeed classic predict-speed \
  --dhrystone-1-1 10 --format text
```

With the current default calibration (2026-10-03), this produces approximately
6.43727 speed-VAXen (SPECint92), CI95 5.99919–6.91744.

Multiple families:

```sh
uv run --no-sync cpushowspeed classic predict-speed \
  --dhrystone-1-1 10 --whetstone-dp 8 --linpack-100 2 --format text
```

This example produces approximately 6.90707 speed-VAXen, CI95 6.40953–7.45594.
It is a hypothetical input example, not an additional historical measurement.

Both Dhrystone versions, with scores supplied as iterations per second:

```sh
uv run --no-sync cpushowspeed classic predict-speed \
  --dhrystone-1-1 17570 --dhrystone-2-1 15813 \
  --dhrystone-unit dhrystones-per-second
```

Default output is machine-readable JSON. It includes the supplied/normalized
inputs, per-metric coefficients and estimates, effective weights, scenario,
cohort, `target_metric` (`SPECint92`), `unit` (`speed-VAXen`), `vaxen`,
`vaxen_ci95` and artifact hashes.
`--format text` provides a compact display.

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

Defaults: `--scenario linear_clock --cohort with_spec89`.
Alternatives are `reported_clock` and `spec92_only`, respectively. Scenario selects
the training/calibration experiment; **supplied scores are not frequency-scaled
again**. The original linear-clock fit applied its qualified CPU-identity rule.

Default bundle directory: `data/derived/classic/network-fit/`.
Use `--calibration-dir PATH` for another bundle. The three required files are:

- `coefficients.csv` — exponents, speed-VAXen at unit score and score units.
- `coefficient-log-draws.npz` — correlated intercept and exponent draws.
- `prediction-calibration.json` — schema (version 3), form, target metric, normalization, ordered
  metric columns for each scenario/cohort, and SHA-256 hashes of the two files.

These derived files can be copied together to use the predictor elsewhere.
The coefficient CSV alone is insufficient for an exact joint bootstrap CI95.
A missing or mismatched bundle fails with an actionable error rather than
silently dropping uncertainty or guessing column order. To generate it using
the locally prepared experiment inputs:

```sh
uv run --no-sync cpushowspeed classic network-fit
```

All 63 nonempty subsets are exercised by tests. Additional tests check family
weights, cancellation of perfectly anticorrelated calibration errors, the
speed-VAXen output contract, raw Dhrystone units, invalid values and stale calibration files.

## Batch historical plot

`cpushowspeed plot timeline` applies this prediction contract to every
one-processor classical result in the built database and adds the saved SPEC89
bridge speed-VAXen estimates; see the [timeline contract](timeline.md). The former
`classic historical-timeline` command was removed on 2026-10-02.
