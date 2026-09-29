# SPEC95/CPU2000 relaxed fitting

> Historical CPU95/2000-only experiment. The current all-generation matching
> implementation and regenerated joint bundles are described in
> [joint tracks](spec-joint-tracks.md#all-generation-matching-update--2026-09-29).
> Standalone 95/2000 tables below retain their original scope.

Computed and reviewed: 2026-09-29.

## Implemented scope

The [overlap audit](spec95-spec2000-overlap-audit.md) identified RAM equality,
lexical/platform naming differences and limited complete-case coverage. The
user authorized broader matching. Three explicit policies now run side by side:

| Policy | Admission rule |
| --- | --- |
| strict | Original exact normalized names/CPU/chips, equal RAM, compatible clock and resources |
| ram-aliases | Candidate platform/CPU naming normalization plus unrestricted RAM; compatible clock and resources retained |
| cpu-clock | Also permit different platform names; same normalized CPU, chips, clock and compatible enabled resources |

The latter two retain clocks within 1%, reject known core/thread-per-core
contradictions, and require the same chip count. Unknown resources remain
unknown. They do not scale scores to new clock rates or CPU counts. NC/zero
aggregates stay excluded. These are deliberate model assumptions, not claims
that differing memory systems or platforms are equivalent.

The RAM/alias policy applies the audit's explicit Compaq/Model/clock-suffix,
XP1000 branding and MIPS R-series label rules. Full disclosure/source identity
and original configuration fields survive every match. The admitted alias
family names were examined in the preceding source audit; full software and
runtime equivalence remains unverified. `cpu-clock` is the broader sensitivity
case, not an automatic replacement for same-platform evidence.

## Joint fits: the previously unsupported edge now has coefficients

Both relaxed scenarios fit all five adjacent joint edges, base and peak, with
speed-only, rate-only and equal-geometric predictors: 30 supported method/mode
rows per scenario. The strict baseline retains its six insufficient-model rows.
Only the CPU95/2000 matching boundary changes; other edges retain their strict
cohorts. Processor aliases are propagated through fold identities throughout
the graph to prevent a held-out CPU reappearing under an alternate label.

For each base/peak mode, the expanded CPU95/2000 cohort is:

| Policy | Complete triples | Target system names | CPU models | CPU/chips/clock configurations |
| --- | ---: | ---: | ---: | ---: |
| strict | 2 | 1 | 1 | 1 |
| ram-aliases | 10 | 9 | 3 | 5 |
| cpu-clock | 72 | 14 | 3 | 5 |

Three CPU labels (21264, 21264A, UltraSPARC II) cover only two broad architecture
families. Increasing 10 to 72 tuples does not increase independent CPU coverage.
All repeat observations remain, with configuration grouping controlling weight.

Held-out errors below remove the whole CPU model, including evidence on every
upstream rate edge. Methods within each scenario use identical complete cases.

| Policy | Mode | Speed-only P95 | Rate-only P95 | Equal-geometric P95 |
| --- | --- | ---: | ---: | ---: |
| ram-aliases | base | 18.18% | 18.05% | 18.12% |
| ram-aliases | peak | 9.84% | 10.15% | 9.99% |
| cpu-clock | base | 24.74% | 24.96% | 25.46% |
| cpu-clock | peak | 13.53% | 13.59% | 13.89% |

Both scenarios can now estimate this local bridge. The three predictors perform
similarly on this small cohort; this is not evidence of a universal speed/rate
identity or a statistically significant preferred weight. Greater dispersion
under the broader platform scenario is retained as useful sensitivity evidence.
No observation is selected or removed by its residual.

## VAXen coefficients and uncertainty

The target is an observed SPEC95 rate score. The local fitted prediction then
uses the CPU95→CPU92 rate prefix and the defined rate-VAXen unit. Thus these
are conditional VAXen estimates, not direct SPEC92 measurements of the added
machines. The relaxed rate95/2000 pairs also recalibrate the upstream prefix
used by later-generation VAXen predictions in the same experimental scenario.
Local errors on those later edges need not change when the shared prefix changes.

The coefficients, local CI95 and full-route CI95 are in the scenario summary
CSVs. Each run requests 10,000 jointly clustered bootstrap draws; empty relevant
resamples are discarded with valid counts recorded. Coefficient CI95 is not a
prediction interval. Whole-model folds and availability masks use the same
rules as the [joint experiment](spec-joint-tracks.md).

## Independent speed and rate fits also rerun

The separate speed→speed and rate→rate fits use the same three matching
policies and the established grouped log-ratio estimator. Their P95 removes one
processor configuration at a time, unlike the whole-CPU-model joint table above.
Their populations also differ; compare scenarios within a track and mode.

| Track | Mode | Policy | Paired submissions | Configurations | P95 |
| --- | --- | --- | ---: | ---: | ---: |
| speed | base | strict | 16 | 11 | 19.55% |
| speed | peak | strict | 13 | 9 | 12.46% |
| speed | base | ram-aliases | 33 | 21 | 19.99% |
| speed | peak | ram-aliases | 24 | 16 | 20.95% |
| speed | base | cpu-clock | 184 | 31 | 26.23% |
| speed | peak | cpu-clock | 142 | 26 | 31.57% |
| rate | base | strict | 16 | 13 | 20.27% |
| rate | peak | strict | 16 | 13 | 16.27% |
| rate | base | ram-aliases | 36 | 26 | 20.12% |
| rate | peak | ram-aliases | 36 | 26 | 26.80% |
| rate | base | cpu-clock | 98 | 28 | 21.83% |
| rate | peak | cpu-clock | 98 | 28 | 25.09% |

This also increases the evidence for the ordinary rate bridge, without using
speed observations as synthetic rate labels. Factor changes and larger errors
are reported, not used to cherry-pick a preferred cohort.

## Reproduce and outputs

```sh
uv run --no-sync cpushowspeed bridge fit-joint-tracks
uv run --no-sync cpushowspeed bridge fit-joint-tracks --matching-policy ram-aliases
uv run --no-sync cpushowspeed bridge fit-joint-tracks --matching-policy cpu-clock
uv run --no-sync cpushowspeed bridge refit-95-2000
```

`fit-joint-tracks` defaults to the reproducible strict baseline. A non-strict
policy appends its name to the output and research directories, preventing
accidental overwrite. `--output-dir` and `--research-dir` are directory roots.

- [RAM/alias joint results](data/spec/joint-tracks/ram-aliases/summary.csv)
- [CPU-clock joint results](data/spec/joint-tracks/cpu-clock/summary.csv)
- [Independent-track factors](data/spec/95-2000-refit/single-track-factors.csv)

Full source-paired tuples, relaxed-field flags, rejections, holdout predictions,
bootstrap vectors and graphs remain under `data/derived/spec/joint-tracks/`
and `data/derived/spec/95-2000-refit/`. Relaxed matches have explicit
`platform_alias_ram_relaxed` or `cpu_clock_resources` tiers rather than being
labelled strict hardware-near matches. Source system names stay intact even
when a normalized grouping key is used.

The prediction CLI retains its prior default calibration. The timeline now exposes
these scenarios as selectable alternatives, while its default retains the prior
rate baseline. The scenario results remain conditional research alternatives;
no conflicting CPU count/clock or NC result was silently admitted to them.
