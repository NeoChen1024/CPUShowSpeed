# Power-law sensitivity of classical calibrations

Reviewed 2026-10-03. A sensitivity report, not a change to the main model: the
[network fit](classic-network-fitting.md) still uses proportional coefficients
(log target = log score + α, exponent 1).

## Question

Is speed-VAXen proportional to each classical score, or a power law
`speed = a × score^b` with `b ≠ 1`? A naive log–log slope can be biased toward
zero by errors in the score (attenuation), and the score–SPEC relation may drift
with era (compilers, caches). The VAX-11/780 is a natural check, since it is
1 speed-VAXen by definition but has no SPEC target to fit.

## Method

`cpushowspeed classic power-law-sensitivity` fits each classical metric alone on
the network's anchored nodes (`linear_clock`; observed SPECint92 and SPECint89
through the int89_to_int92 bridge). Each system weighs 1, split over its nodes.

| Method | Form |
| --- | --- |
| `proportional` | log y = α + log x (the network's form) |
| `free_ols` | log y = a + b log x |
| `free_deming` | the same, with errors in both variables |
| `anchored_ols`, `anchored_deming` | log y = b (log x − log x₇₈₀): through the 780 at 1 speed-VAXen |
| `proportional_year` | log y = α + log x + c (year − 1990) |
| `free_ols_year` | log y = a + b log x + c (year − 1990) |

- **x₇₈₀** is the median of the VAX-11/780's own measured classical nodes for
  that metric (Dhrystone 1.1: 0.88 DMIPS from 2 nodes; 2.1: 0.835 from 1;
  Whetstone DP 0.64 from 2, SP 0.74 from 1, native 1.02 from 1; LINPACK 0.13
  MFLOPS from 2). The 780 is measured below 1 DMIPS, like any other machine.
  The definitional 1 DMIPS is not used as an anchor.
- **Deming δ** is the ratio of error variances, y over x. Both are pooled within
  (system, target clock):
  - y: over distinct targets
  - x: over distinct classical runs
  - Results: δ = 0.28 (Dhrystone), 0.21 (LINPACK), 1.0–1.1 (Whetstone SP/DP)
  - These replicates mix compiler, OS and option differences. They are an
    upper bound on pure measurement error.
- **Year** is the target result's chronology year. Nodes without one are dropped
  from the year methods. The 780 is predicted at 1977.
- **Validation**:
  - leave-one-system-out relative error
  - the predicted VAX-11/780 speed for the free and year methods (the anchored
    methods equal 1 by construction)
  - system-cluster bootstrap CIs (2,000 draws)

## Results

`linear_clock`, 2026-10-03 data. Exponent CI95 from the bootstrap; 780 is the
predicted speed-VAXen of the VAX-11/780 at its measured score (true value 1);
LOSO is the median and the model-center P95 of leave-one-system-out errors.

| Metric | Method | Exponent b | 780 | LOSO median | LOSO P95 |
| --- | --- | --- | ---: | ---: | ---: |
| Dhrystone 1.1 (69 systems) | proportional | 1 | 0.55 | 16.9% | 38.7% |
| | free OLS | 0.935 (0.901–0.966) | 0.72 | 15.1% | 39.1% |
| | free Deming | 0.963 (0.931–0.993) | 0.64 | 15.0% | 38.6% |
| | anchored OLS | 0.863 (0.854–0.871) | 1 | 8.3% | 48.4% |
| | free + year | 0.973 (0.907–1.031) | 0.83 | 15.0% | 37.8% |
| Dhrystone 2.1 (66) | proportional | 1 | 0.56 | 19.3% | 39.5% |
| | free OLS | 0.894 (0.868–0.915) | 0.88 | 12.1% | 39.1% |
| | free Deming | 0.919 (0.893–0.941) | 0.79 | 13.1% | 38.8% |
| | anchored OLS | 0.865 (0.857–0.873) | 1 | 10.4% | 38.8% |
| | free + year | 0.868 (0.814–0.927) | 0.74 | 13.2% | 39.2% |
| Whetstone DP (57) | proportional | 1 | 0.59 | 27.3% | 50.5% |
| | free OLS | 0.840 (0.816–0.866) | 1.12 | 21.3% | 35.0% |
| | free Deming | 0.853 (0.828–0.881) | 1.06 | 21.0% | 35.1% |
| | anchored OLS | 0.865 (0.855–0.874) | 1 | 20.7% | 34.1% |
| | free + year | 0.937 (0.890–1.013) | 2.45 | 18.5% | 32.7% |
| Whetstone SP (50) | proportional | 1 | 0.51 | 20.0% | 45.4% |
| | free OLS | 0.875 (0.843–0.909) | 0.86 | 21.6% | 32.5% |
| | free Deming | 0.895 (0.868–0.930) | 0.79 | 20.0% | 34.5% |
| | anchored OLS | 0.842 (0.830–0.854) | 1 | 23.4% | 29.8% |
| | free + year | 0.982 (0.934–1.042) | 1.82 | 21.6% | 29.1% |
| LINPACK n=100 (83) | proportional | 1 | 0.45 | 45.9% | 152.9% |
| | free OLS | 0.722 (0.682–0.756) | 1.48 | 24.6% | 107.0% |
| | free Deming | 0.823 (0.781–0.877) | 0.96 | 29.1% | 114.7% |
| | anchored OLS | 0.807 (0.792–0.822) | 1 | 30.9% | 106.7% |
| | free + year | 0.554 (0.482–0.623) | 0.26 | 30.3% | 69.3% |

Whetstone native (16 systems), the anchored Deming rows, the proportional + year
rows and every CI are in the
[machine-readable table](data/classic/power-law-sensitivity.csv), with its
[audit](data/classic/power-law-sensitivity-audit.json).

## Findings

1. **Free exponents are below 1 for every metric**: 0.72–0.96. Every CI
   excludes 1 except with a year term.
   - Errors in x do not explain this. Deming moves b only 0.01–0.10 toward 1,
     because the score range is wide relative to replicate scatter.
2. **The proportional form underpredicts the VAX-11/780 by 41–55%** for every
   metric except Whetstone native (0.45–0.59 speed-VAXen against 1; native 0.89).
   The free power laws predict 0.64–1.56, so a power law largely reconciles the 780 with the
   1988–1995 calibration population:
   - Dhrystone 2.1: 0.88
   - Whetstone DP: 1.12
   - LINPACK, Deming: 0.96
3. **Anchoring through the 780 costs little in held-out error.** Against free
   OLS, anchored LOSO P95 is:
   - equal or lower for Dhrystone 2.1, Whetstone DP and SP, and LINPACK
   - higher for Dhrystone 1.1 (48.4% vs 39.1%)

   Against the proportional form, P95 falls 15–46 points for Whetstone SP/DP and
   LINPACK (7 for native), and Dhrystone stays within 1 point except Dhrystone 1.1. Median
   errors are similar or lower.
4. **Era is confounded with the slope.** At a fixed score, later systems earn less
   SPEC:
   - With the exponent fixed at 1, the year term is −30% to −69% per decade.
   - With a free exponent, b returns to near 1 for Dhrystone 1.1 (0.97) and
     Whetstone SP/DP (0.98/0.94), but not for Dhrystone 2.1 (0.87).
   - LINPACK's year model is unstable: the year coefficient +457% per decade
     with b 0.55.
   - Year models extrapolate badly to 1977: the 780 is predicted at 0.26–3.3.

   The data cannot separate "SPEC grows sub-linearly with the classical score"
   from "the classical score inflates relative to SPEC over time" (compilers
   tuned to Dhrystone, for example). Both predict b < 1 in a pooled fit.

## Limitations

- Single-metric fits ignore the network's latent coupling and family balancing.
  Coefficients are not directly comparable with the network's.
- The 780 is one system with one or two measured nodes per metric. Its
  agreement is a single validation point, not a test.
- Replicate variances mix compiler, OS and configuration differences, so δ is
  approximate. Deming and OLS slopes differ by at most 0.10, but other δ values
  were not run.
- No result here changes any published estimate or the timeline.

## Next steps

Extending a power-law form into the network (and the composite and SPEC89
stages) would need:
- a shared exponent or one per family
- a decision between the 780 anchor and a free intercept
- a decision on whether the year confounding is modeled or left as a caveat

These are decisions for review, not implemented.
