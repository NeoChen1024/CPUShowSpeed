# Early-benchmark closeout: environment model comparison

Review date: 2026-09-26. Compares a pooled multiplier, separate environment
multipliers, and partial pooling on the same observations. All environments
and repeats are retained. The equal-weight two-benchmark composite remains
fixed; no benchmark weights are optimized. This closes the current collected
classical-benchmark modeling experiment, not historical extrapolation validation.

## Data and identifiable effects

The primary cohort is DEC source-column observations. An extended sensitivity
cohort includes the existing legacy and DEC-to-archive candidates. Target is
SPEC92 integer-rate VAXen. Native/SP/DP and Dhrystone versions remain separate.

Environment is **construction cohort × SPEC target OS family**. It is a
proxy for a combination of conditions, not an isolated OS effect. Compiler
versions, classical-run OS, active CPU/copy counts and other settings are not
consistently available. Source and environment are confounded; no separate
compiler/source random effects are claimed. Unknown OS is retained explicitly.
`coverage.csv` enumerates the actual model/environment support and weights.

## Estimators and weighting

Let `z = log(y / sqrt(x1*x2))`, with the established input unit normalizers.
Within each machine-model/environment cell, take the median z. Each machine
has total training weight one, divided equally among its observed environments.
The pooled center alpha is the weighted mean of these cells.

- **Pooled:** predict `exp(alpha)` for all environments.
- **Grouped:** predict the weighted mean log ratio for the observed environment.
- **Shrinkage:** for environment e, predict
  `exp(alpha + n_e/(n_e+lambda) * (mean_e-alpha))`, where n_e is its total
  model/environment weight. This is partial pooling toward an empirical global
  center, not a fully estimated mixed-effects variance model.

Shrinkage strength is chosen from `{1,4,16}` using inner leave-one-machine-model
out log squared error on the outer training data only. With fewer than three
training models, use the predeclared fallback 4. Unknown test environments use
alpha for all three models. Full-data coefficients are descriptive outputs,
not validated factors for an unobserved historical environment.

Evaluation retains individual observations. Each machine receives equal weight,
each of its observed environments equal weight, and repeated observations share
that environment's weight. P95 uses the weighted empirical CDF (first value
whose cumulative weight reaches 95%). **This differs from the earlier interpolated
P95 of model centers**; 31.42% below is not a revision of the earlier 21.01%.
Training centers, weighting and evaluation units are identical across the three
models in this comparison. Log RMSE is the weighted root mean squared log error.

## Held-out results: Whetstone DP + LINPACK100

| Cohort / model | Models / observations | Observation P95 | Log RMSE |
| --- | ---: | ---: | ---: |
| DEC / pooled | 18 / 34 | 30.12% | 0.1566 |
| DEC / grouped | 18 / 34 | 22.69% | **0.0743** |
| DEC / shrinkage | 18 / 34 | **20.46%** | 0.0756 |
| Extended / pooled | 20 / 66 | 31.42% | 0.1581 |
| Extended / grouped | 20 / 66 | 22.81% | **0.0797** |
| Extended / shrinkage | 20 / 66 | **20.73%** | 0.0835 |

Every outer fold removes the whole machine model, across environments and
origins. Grouping improves typical log prediction error; shrinkage reduces this
pair's P95 slightly further, but does not beat grouping on log RMSE. Across the
8 DEC and 11 extended pair variants, grouping has the lowest observed held-out
log RMSE. These correlated comparisons are not independent significance tests.
No universal superiority of shrinkage is established.

## Unseen environment and source tests

For the DP/LINPACK extended cohort:

| Outer holdout | P95, all three methods |
| --- | ---: |
| Entire environment group | 43.83% |
| Entire construction origin, shared IDs purged | 44.02% |

When a group is entirely unseen, all methods fall back to the pooled center,
so equality is expected by construction. This exposes the limit of estimating
known group offsets; it does not empirically show that all possible hierarchical
models are equivalent. Leave-environment-out may retain the same machine in
other environments and is a domain-transfer test, not unseen-machine validation.

For origin holdout, training tuples sharing any SPEC/classical observation ID
with the test origin are purged. Indirect common upstream measurements can
remain. A DEC-only origin holdout has no training data and is explicitly reported
as unevaluable. `folds.csv` records all support counts, purges, selected strengths,
selection fallbacks and missing-fold statuses. No test labels tune the strength.

## Closeout decision

1. **Superseding user decision, 2026-09-26:** select pooled, equal-weight
   geometric composites and one fitted multiplier per combination/target as
   the primary research method. The numerical group/shrinkage comparisons remain
   valid diagnostics, but their environmental adjustments are not adopted for
   historical backcasting. See the [selected bridge method](../docs/methods.md#selected-classical-bridge-method).
2. Keep all raw observations and uncertain candidate matches. No score-based
   deletion, new unit change, or production VAXen conversion update is made.
3. Unknown historical environments remain an extrapolation problem. No interval
   coverage, architecture holdout, chronological backcast, or PDP-8/E validity is
   established here. The 20.73% figure must not be applied as a 95% error bound
   to early machines outside this dataset.
4. Source/software effects have not been uniquely decomposed. Future data should
   add crossed environments/configurations and older architectures, rather than
   treating missing environmental offsets as measured quantities.

## PDP-8/E follow-up boundary

Selected future route (not implemented in this experiment): use SIMH to execute
LLM-assisted assembly and check semantics; collect instruction traces and combine
them with documented instruction/memory timing and hardware-option assumptions.
Simulator wall-clock runtime is not hardware benchmark time. Trace completeness,
SIMH model configuration and timing reconstruction must be independently checked.
A reconstructed assembly workload remains a distinct implementation/evidence
class, with no presumed C-compiler environmental correction.

## Reproduction and artifacts

```sh
uv run cpushowspeed classic environment-fit
```

Inputs are the existing source-pair records, PDF table snapshot and archive SPEC
OS metadata. Outputs under `data/derived/classic/environment-fit/`:
`summary.csv`, `folds.csv`, `predictions.csv`, `parameters.csv`, `coverage.csv`,
`environment-comparison.png/.svg`, and `audit.json` with input/code/output hashes.
The summary includes 171 cohort/pair/holdout/model combinations, including
explicit unevaluable cases. All three methods share outer test observations.

Tracked [comparison summary](data/classic/environment-summary.csv),
[full-data parameters](data/classic/environment-parameters.csv),
[coverage](data/classic/environment-coverage.csv),
[fold settings](data/classic/environment-folds.csv), and
[audit](data/classic/environment-audit.json) preserve the closeout result.
Tests check model/environment weights, repeat invariance of training centers,
shrinkage direction, unknown-environment fallback, and isolation of held-out
outcomes from both coefficient fitting and inner strength selection. The plot
was visually inspected.
