# Predict SPEC92 integer rate from classical scores

`cpushowspeed classic predict-rate` accepts any nonempty subset of six metrics
and predicts **peak `SPECrate_int92`**, equivalent VAXen and conditional calibration
CI95. It reads an existing calibration bundle; prediction performs no fitting
or network access. The [network experiment](../research/classic-network-fitting.md)
owns coefficient estimation and empirical limitations.

## Common prediction entry point

`cpushowspeed predict classical` exposes the same classical prediction command.
`cpushowspeed predict spec-rate GENERATION MODE SCORE` exposes the existing SPEC
integer-rate converter, supporting 92, 95, 2000, 2006, 2017 and 2026, with
`base` or `peak` and `--format json|text`. Both paths read saved calibration and
return VAXen plus conditional CI95. For example:

```sh
uv run cpushowspeed predict spec-rate 2017 base 11800 --format text
uv run cpushowspeed predict classical --dhrystone-1-1 10 --format text
```

The original `convert-rate` and `classic predict-rate` commands remain aliases
of the same implementations. SPEC speed, FP and SPEC89 scores are not rate
inputs. SPEC2026 retains the sparse-calibration limitations described in the
rate-chain research. The classical path targets peak rate; the SPEC path retains
the supplied base/peak mode. Their JSON output schemas and calibration-scenario
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
uv run --no-sync cpushowspeed classic predict-rate \
  --dhrystone-1-1 10 --format text
```

With the current default calibration, this produces approximately
153.49934 SPECrate_int92, CI95 139.64299–169.15674; equivalently
6.47195 VAXen, CI95 5.88773–7.13210.

Multiple families:

```sh
uv run --no-sync cpushowspeed classic predict-rate \
  --dhrystone-1-1 10 --whetstone-dp 8 --linpack-100 2 --format text
```

This example produces approximately 175.56987 SPECrate_int92 and 7.40250 VAXen.
It is a hypothetical input example, not an additional historical measurement.

Both Dhrystone versions, with scores supplied as iterations per second:

```sh
uv run --no-sync cpushowspeed classic predict-rate \
  --dhrystone-1-1 17570 --dhrystone-2-1 15813 \
  --dhrystone-unit dhrystones-per-second
```

Default output is machine-readable JSON. It includes the supplied/normalized
inputs, per-metric coefficients and estimates, effective weights, scenario,
cohort, calibrated output units, conditional CI95 and artifact hashes.
`--format text` provides a compact display.

## Calculation and uncertainty

Each score gives `V_b = k_b * score_b`. Give available benchmark families equal
weight and split a family's weight equally across its supplied versions. The
combined VAXen estimate is the weighted geometric mean of `V_b`. For example,
Dhrystone 1.1 + Dhrystone 2.1 + LINPACK get weights 1/4, 1/4 and 1/2.

Raw predicted `SPECrate_int92 = VAXen * 604800 / 25500`.

For CI95, apply those same weights to each **joint** log-coefficient bootstrap
replicate and take the linear 2.5/97.5 percentiles of the final estimates. Do
not geometrically combine marginal interval endpoints or treat coefficients
as independent. The interval describes conditional calibration uncertainty,
not an individual-machine prediction interval, source-score error or unknown
architecture/compiler bias. Output is explicitly a model prediction, not a
reported SPEC result. Base-rate prediction is not supplied by this model.

## Calibration selection and portability

Defaults: `--scenario linear_clock --cohort with_spec89`.
Alternatives are `reported_clock` and `rate_only`, respectively. Scenario selects
the training/calibration experiment; **supplied scores are not frequency-scaled
again**. The original linear-clock fit applied its qualified CPU-identity rule.

Default bundle directory: `data/derived/classic/network-fit/`.
Use `--calibration-dir PATH` for another bundle. The three required files are:

- `coefficients.csv` — point factors and score units.
- `coefficient-log-draws.npz` — correlated coefficient draws.
- `prediction-calibration.json` — schema, target metric, normalization, ordered
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
weights, cancellation of perfectly anticorrelated calibration errors, rate/VAXen
normalization, raw Dhrystone units, invalid values and stale calibration files.

## Batch historical plot

`cpushowspeed classic historical-timeline` applies this prediction contract to
existing source configurations and combines them with SPEC89 bridge estimates.
See the [timeline method and outputs](../research/historical-vaxen-timeline.md).
