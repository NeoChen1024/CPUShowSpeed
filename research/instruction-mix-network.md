# Gibson/ADP ratings in the classical network

Reviewed: 2026-10-02; re-anchored to speed-VAXen 2026-10-03. Status:
implemented conditional fit on the schema database
(`instruction-mix-joint-network-v3-speed-anchor`). It replaces the
name-matched mix network experiment removed on 2026-10-02, which remains in Git
history. Source definitions and the pairing review queue are in the
[instruction-mix bridge](instruction-mix-bridge.md).

## Method

`cpushowspeed classic mix-network-fit` extends the
[classical network](classic-network-fitting.md) with CCTA Gibson and ADP ratings
(KIPS). Like that network, it is calibrated in speed-VAXen (SPECint92 = 1).

- **Attachment.** A rating attaches to every network node of its resolved system
  (`resolved_system`). In the `plus_pending_links` scenario it also attaches to
  systems a review leaves linked as `needs_review`; rejected links never attach.
  Repeated ratings on one node use their log median. Ratings are never
  clock-scaled.
- **Clusters.** Nodes sharing one attached rating form one model cluster for
  bootstrap and holdouts, and SPEC89 bridge evidence is merged into the same
  clusters.
- **Fit.** The classical network's family-, variant-, node- and model-balanced log
  least squares. Gibson and ADP share one `InstructionMix` family weight. Every
  scenario is fitted for both clock policies and both cohorts (`spec92_only`,
  `with_spec89`).
- **Estimates.** Each rating is scaled by its coefficient. Each source table row
  also gets a combined estimate: the equal-log-weight mean of its available ratings.
  Its CI95 comes from the aligned coefficient draws, so the two coefficients'
  dependence is kept.

Without mixes, `resolved_system` reproduces the saved network coefficients
exactly. Merging pending-linked clusters moves them by at most 0.34%.

## Results

Of 360 positive ratings on 184 resolved systems, 18 ratings on 10 systems attach
under `resolved_system`. These are CDC 6600/7600, IBM 360/30, 360/50, 370/145,
370/155 and 370/165, ICL 1906A/1906S, and PDP-8/E. Under `plus_pending_links`,
36 ratings attach to 17 nodes in 15 clusters. No attached system has a SPEC
target. Every mix coefficient therefore rests on classical scores alone, and
there is no observed-SPEC holdout.

Speed-VAXen per KIPS, `linear_clock / with_spec89`:

| Links | Gibson | ADP |
| --- | --- | --- |
| `resolved_system` | 0.00046192 (0.00032202–0.00061512) | 0.00024136 (0.00012298–0.00037037) |
| `plus_pending_links` | 0.00039425 (0.00028095–0.00052303) | 0.00019421 (0.00011428–0.00030504) |

The whole-cluster holdout compares a mix-only prediction with the held-out
node's classical-network prediction (a proxy, not a SPEC measurement). The
model-center P95 is 194.9% for `resolved_system` (10 clusters) and 187.7% for
`plus_pending_links` (15 clusters). On the 59 observed-SPECint92 models, adding
the mixes changes the network's held-out P95 from 87.9% to 87.4% / 87.2%.

The timeline uses `plus_pending_links / linear_clock / with_spec89`, as the
former experiment used its unapproved name candidates. `resolved_system` is the
sensitivity check. The coefficients, holdout summary and anchor comparison of all
eight runs are saved in:

- [mix-network-coefficients.csv](data/classic/mix-network-coefficients.csv)
- [mix-network-holdout-summary.csv](data/classic/mix-network-holdout-summary.csv)
- [mix-network-anchor-comparison.csv](data/classic/mix-network-anchor-comparison.csv)
- [mix-network-audit.json](data/classic/mix-network-audit.json)

## Changes

The 2026-10-03 re-anchoring to speed-VAXen raised the timeline run's
coefficients by 1.9% (Gibson 0.00037246 → 0.00037966) and 2.0% (ADP
0.00018340 → 0.00018706), following the classical coefficients they are
calibrated through. Adding the [1990 DEC report rows](vendor-performance-reports.md)
and [MIPS Performance Brief 3.5](vendor-performance-reports.md) the same day
raised them a further 1.5% (Gibson 0.00037966 → 0.00038447 → 0.00038526, ADP
0.00018706 → 0.00018943 → 0.00018992). [Richardson's Dhrystone
lists](usenet-result-lists.md) then lowered them 0.7% and 0.9% (Gibson →
0.00038253, ADP → 0.00018819), following the lower Dhrystone coefficients.
The [smaller Usenet result posts](usenet-result-lists.md#smaller-result-posts-19901991)
raised them 0.15% and 0.13% (Gibson → 0.00038310, ADP → 0.00018844), and the
[printed SPEC89 means](usenet-result-lists.md#printed-spec89-means-19901991) a further
2.9% and 3.1% (Gibson → 0.00039425, ADP → 0.00019421), following the higher
Whetstone and LINPACK coefficients.

### Name-matched experiment

The former fit (2026-09-28) joined ratings through name-matched classical
candidate pairs. Its `linear_clock / with_spec89` coefficients were Gibson
0.00036847 and ADP 0.00018273 rate-VAXen/KIPS. The resolved-system,
rate-anchored run gave +1.1% and +0.4%. Before the 2026-10-02 catalogue spelling
merges it gave +9.5% and +7.1%; the merges lowered the classical coefficients the
mixes are calibrated through (see
[classical network](classic-network-fitting.md#pair-review-and-spelling-merges-2026-10-02)).

## Limitations

- Every system link is unapproved. A shared resolved system does not establish
  equal configuration, arithmetic options or memory timing.
- The mix coefficients are conditional on the classical calibration and
  correlated with the classical route. Agreement between the two is not
  independent validation.
- The proxy holdout measures consistency with the classical network, not SPEC
  error. Its large tail is reported, not grounds for removing ratings.
- CI95 covers coefficient sampling, not individual prediction error.
