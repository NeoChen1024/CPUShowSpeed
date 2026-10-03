# Gibson and ADP instruction mixes

Reviewed: 2026-09-27 to 2026-10-03. This report owns the CCTA Gibson/ADP mix
inventory, its pairing with classical results, the mix sources found so far and
the joint network fit that calibrates mix ratings to speed-VAXen (method
`instruction-mix-joint-network-v6-two-stage-power-law`).

## Source and definitions

Primary compilation: Roy Longbottom's
[Computer Speeds From Instruction Mixes](http://www.roylongbottom.org.uk/cpumix.htm),
cached by the project; the [author's ResearchGate copy](https://www.researchgate.net/publication/318793156_Computer_Speeds_From_Instruction_Mixes_pre-1960_to_1971)
is the same work, not independent measurements.

```sh
uv run cpushowspeed classic mix-inventory
```

The command validates the cached blob's BLAKE3, independently reparses its 190
table rows, checks both weight tables and exports all 380 mix listings, including
missing scores, to `data/derived/classic/mix-study/`; `data extract` loads the
positive listings as `mix:longbottom-cpumix` results. Numerical cells are
calculated ratings, not verified hardware executions.

| Inventory | Gibson | ADP |
| --- | ---: | ---: |
| Source machine/configuration listings | 190 | 190 |
| Positive KIPS cells | 177 | 183 |
| Missing score listings retained | 13 | 7 |
| Operation categories | 12 | 7 |
| Sum of weights | 1.000 | 1.000 |

174 of the 190 rows have both scores. The Gibson variation includes 12.9%
floating-point operations; ADP has none. The version is recorded as **CCTA/TSU
variation reproduced by Longbottom**, not every historical "Gibson Mix". The
source defines

\[
T_{\mu s}=\sum_i w_i t_{i,\mu s},\qquad
KIPS=\frac{1000}{T_{\mu s}}a,
\]

where `a` is an architecture adjustment of 1 to 2 (often 1 for accumulator
designs, 1.25 for single address plus registers) that individual rows do not
state. Stored scores already include it: do not apply it twice or remove it by
assuming a value. Mix categories can need several native instructions, software
routines or different precisions; KIPS/1000 is not DMIPS or SPEC throughput.
The earliest positive table years are 1954 (IBM 650, ICL 1202), chronology leads
only. The PDP 8E row's 1968 date does not overwrite PDP-8/E chronology.

## Pairing with classical results

Mix results pair with classical results of the whole classical inventory in two
scenarios: `resolved_system` (same `system_id`) and `plus_pending_links`
(additionally the system links a review leaves `needs_review`, converted from
the former candidate alias list; rejected links never pair). No pairing is
approved.

| Mix | Classical metric | `resolved_system` pairs / systems | `plus_pending_links` pairs / systems |
| --- | --- | ---: | ---: |
| Gibson | Whetstone native MWIPS | 19 / 9 | 40 / 15 |
| Gibson | Whetstone DP MWIPS | 8 / 6 | 25 / 12 |
| Gibson | LINPACK n=100 MFLOPS | 5 / 2 | 5 / 2 |
| ADP | Whetstone native MWIPS | 14 / 8 | 35 / 14 |
| ADP | Whetstone DP MWIPS | 5 / 5 | 22 / 11 |

There are 127 metric pairs (76 only through pending links) and no Dhrystone
pairs. The LINPACK pairs come only from CDC 6600/7600. Review priorities:

1. IBM 360/30, 360/50; 370/145, 370/155, 370/165; ICL 1906A/1906S: confirm
   arithmetic facilities, memory-cycle assumptions and program precision.
2. CDC 6600/7600: the "6600 (Cyber74)" link is rejected (the Cyber 74 is a
   separate 1971 model; see [identity and dates](identity-and-dates.md#cdc-cyber-73-and-74)).
3. ICL KDF9 and 1904 variants: native Whetstone runs range 0.002–0.08 MWIPS, a
   reason to examine environment and workload semantics, not to discard scores.
4. PDP-8/E, PDP-11, HP 2100: resolve EAE/EAU/FPU/software floating point options.
5. IBM 360/65 G versus H/I/J: memory size and interleaving.

`classic mix-bridge` also audits direct edges to SPEC. No mix result shares a
resolved system with any SPEC89 result (SPECint89 182 values on 91 systems,
SPECmark89 264 on 132, SPECfp89 207 on 106: zero pairs) or SPEC92 result
(SPECint92, SPECbase_int92, SPECfp92, SPECrate_int92 and SPECrate_base_int92:
1,201 values, zero pairs). Old-model substrings in SPEC92 names are modern
products (AlphaServer 2100, RS/6000 360/370). The only CPU-family lead is SC-3
against `spec89:A0094`, a generic 33 MHz i386/387 with SPECmark89 4.3 and no
SPECint89; shared family, different clock and memory path and a different metric
do not make a bridge. Direct edges need genuine mix results for machines already
in SPEC89 (VAX variants, specified 386/486 configurations) or the reverse. The
same command fits conditional `classical score = k × KIPS` edges per mix and
metric, saved as [`bridge-*` snapshots](data/classic/mix-study/); their large
tail errors (held-out observation P95 74–983%) describe variation under the
unapproved matches.

## Mix network

`classic mix-network-fit` extends the [classical network](classical-fits.md#sparse-network)
with the Gibson and ADP ratings (KIPS), calibrated in speed-VAXen.

- **Attachment.** A rating attaches to every network node of its resolved system;
  in `plus_pending_links` also to systems with an open link. Repeated ratings on
  one node use their log median. Ratings are never clock-scaled.
- **Clusters.** Nodes sharing one attached rating form one cluster for bootstrap
  and holdouts; SPEC89 bridge evidence is merged into the same clusters.
- **Fit.** The network's balanced log least squares with power laws and the
  two-stage fit. Gibson and ADP share one family weight and one exponent, set
  from nodes where mixes are rated beside classical scores; mix-only nodes
  (Gibson beside ADP) inform only the intercepts. The VAX-11/780 has no mix
  rating, so each mix keeps a **free intercept**.
- **Estimates.** Each rating gives `exp(a_mix) * KIPS^beta`; each source row also
  gets a combined estimate (equal-log-weight mean of its ratings) whose CI95 uses
  the aligned intercept and exponent draws.

Without mixes, `resolved_system` reproduces the network coefficients exactly;
merging pending-linked clusters moves them by at most 0.27%.

Of 360 positive ratings on 184 resolved systems, 18 ratings on 10 systems attach
under `resolved_system` (CDC 6600/7600, IBM 360/30, 360/50, 370/145, 370/155,
370/165, ICL 1906A/1906S and PDP-8/E); under `plus_pending_links` 36 ratings
attach to 17 nodes in 15 clusters. No attached system has a SPEC target, so every
mix coefficient rests on classical scores alone and there is no observed-SPEC
holdout.

`linear_clock / with_spec89`, speed-VAXen at 1,000 KIPS (the intercept at 1 KIPS
lies far outside the data):

| Links | Shared exponent β (CI95) | Gibson at 1,000 KIPS | ADP at 1,000 KIPS |
| --- | --- | ---: | ---: |
| `resolved_system` | 0.984 (0.815–1.173) | 0.82 | 0.44 |
| `plus_pending_links` | 0.991 (0.832–1.143) | 0.72 | 0.37 |

The exponent interval is wide: ten to fifteen clusters span a narrow range of
ratings. The median rating CI95 spans a factor of 2.9 (Gibson) and 3.3 (ADP);
ratings far below the attached machines reach about 19–21, an extrapolation of
three to four orders of magnitude. The whole-cluster holdout compares a mix-only
prediction with the held-out node's classical prediction (a proxy, not SPEC): the
model-center P95 is 211.3% (`resolved_system`, 10 clusters) and 150.7%
(`plus_pending_links`, 15 clusters). Adding the mixes changes the network's
observed-SPECint92 held-out P95 from 67.9% to 67.7% / 67.5%.

The timeline uses `plus_pending_links / linear_clock / with_spec89`;
`resolved_system` is the sensitivity check. Saved:
[coefficients](data/classic/mix-network-coefficients.csv),
[holdout summary](data/classic/mix-network-holdout-summary.csv),
[anchor comparison](data/classic/mix-network-anchor-comparison.csv) and
[audit](data/classic/mix-network-audit.json).

Limitations: every system link is unapproved; the mix coefficients are
conditional on and correlated with the classical route, so agreement is not
independent validation; the proxy holdout's large tail is reported, not grounds
for removing ratings; CI95 covers coefficient sampling only; the mix exponent
rests on a few 1960s–1970s systems and era drift is not modeled.

History: a name-matched mix network (2026-09-28) was removed on 2026-10-02 and
rebuilt on resolved systems. On 2026-10-03 it followed the classical network to
speed-VAXen and power laws; the two-stage fit moved the mix exponent from 0.856
to 0.991, and every timeline mix estimate rose 79–103% against the proportional
version, following the classical estimates for slow machines.

## Further mix sources

A bounded web search (2026-09-27) recorded twelve source dispositions in the
[source hunt](data/classic/mix-study/source-hunt.csv), with
[acquisition records](data/classic/mix-study/source-hunt-acquisition.csv) for
five PDFs. Eight documents (1,571 pages, including the AFIPS SJCC 1971
proceedings) were OCRed and screened by `classic mix-evidence`; the
[review ledger](data/classic/mix-study/ocr-review-ledger.csv) separates OCR
screening from original-page checks. Keyword hits are navigation aids, not proof
of absence. None of the cells below is a database observation yet
(`fit_eligible=false`).

### Transcribed values

[Additional observations](data/classic/mix-study/additional-observations.csv)
holds six absolute ratings and four relative cells, all checked against rendered
pages. They are vendor claims, not verified executions.

| Source configuration | Reported Gibson-Mix I MIPS | Converted KIPS |
| --- | ---: | ---: |
| TR 440/200, one processor | approximately 0.48 | 480 |
| TR 440/400, one processor | approximately 0.83 | 830 |
| TR 440/400, two processors | approximately 1.49 | 1490 |
| TR 440/500, one processor | approximately 1.2 | 1200 |
| TR 440/500, two processors | approximately 2.04 | 2040 |
| TR 440/500, three processors | approximately 2.76 | 2760 |

Source: Telefunken, [TR 440 overview](http://computermuseum.informatik.uni-stuttgart.de/ftp/telefunken/tr440/doku/TR440_Ueberblick.pdf),
physical pages 3–4 (document date unknown). `Rechnerkern` counts are processor
counts; models have different memory systems; nothing is divided by processor
count. Equivalence of Gibson-Mix I and the CCTA variation is unestablished.
Xerox's [Sigma 6/9 Sales Guide](https://www.bitsavers.org/pdf/sds/sigma/Sigma_6_9_Sales_Guide_Feb72.pdf)
(1972-02-20, physical page 20) gives Sigma 9 / Sigma 6 ratios of 1.6 for its
scientific (Gibson) mix and 1.7 for an unspecified commercial mix, which is not
identified as ADP; ratios give no absolute KIPS.

### SC-3 spacecraft computer

Stone and Kroesche's [1991 paper](https://digitalcommons.usu.edu/smallsat/1991/all1991/36/)
(seven-page PDF supplied by the user) reports qualified Gibson, Dhrystone 2.1 and
Whetstone on a 16 MHz 80386/80387. The [curated CSV](data/classic/mix-study/sc3-observations.csv)
holds all 12 score cells of Tables 3–5 (physical pages 5–6):

| Benchmark/configuration | Original score |
| --- | ---: |
| Qualified Gibson, SC-2, 8 MHz, 16-bit memory | 539 thousand Gibson operations/s |
| Qualified Gibson, SC-3, 16 MHz, 16-bit memory | 713 thousand Gibson operations/s |
| Dhrystone 2.1, SC-3, 32-bit, 2 waits, cache off/on | 3902 / 6620 Dhrystones/s |
| Dhrystone 2.1, SC-3, 32-bit, 5 waits, cache off/on | 2533 / 6564 Dhrystones/s |
| Dhrystone 2.1, 25/33 MHz 386 PC clones | 10638 / 13514 Dhrystones/s |
| Whetstone, SC-3, 32-bit, 2/5 waits, cache off | 1.244 / 0.966 million Whetstones/s |
| Whetstone, 25/33 MHz 386 PC clones | 2.500 / 3.302 million Whetstones/s |

The Gibson runs use 16-bit memory and the classical runs 32-bit, so no
interchangeable Gibson/classical pair is established; Whetstone precision is
unspecified. The qualified Gibson cites Carney, *Computer* 16(4), 1983-04,
pp. 38–40; its weights are unverified. [Arithmetic checks](data/classic/mix-study/ocr-review-checks.json)
reproduce the reported improvements (Gibson 32.28%; Dhrystone caching 69.66% and
159.14%).

### DINKIAC I simulation

Richard W. Conn's DINKIAC I paper (AFIPS SJCC 1971, [proceedings](https://www.bitsavers.org/pdf/afips/1971-05_%2338.pdf)
physical pages 13–15) gives seven operation groups with Gibson percentages and
delay-line timings ([weights](data/classic/mix-study/dinkiac-mix-weights.csv):
weighted time 8.6245 revolutions, matching the author's 8.6) and 31 simulation
durations plus two source dashes ([results](data/classic/mix-study/dinkiac-simulation-results.csv)).
These are **simulation-model results**, a reconstruction precedent, not measured
performance; work per run varies, so durations are not converted to KIPS.

### Remaining leads

- Gibson's **IBM TR 00.2043** and the CCTA Technical Note 3806 / Technical
  Memorandum 1163 (1977) remain bibliographic targets; a secondary claim of 212
  result sets differs from the 190 rows recovered.
- The NPL **Guide to the Processing Speed of Computers** (Nott) was never
  published; Wichmann's account in [Computer Resurrection 33](https://www.computerconservationsociety.org/resurrection/res33.htm)
  preserves two summary figures (KI10, KL10, PDP-11) without individual ratings.
- Wichmann's CCU Report 11 (1970), [Some Statistics from ALGOL Programs](https://www.researchgate.net/publication/242495225_Some_Statistics_from_ALGOL_Programs)
  §5.4.2, ranks fifteen machine/compiler combinations by a Gibson-related ratio;
  ranks are not absolute ratings.
- Electronics pages cite a 33 MHz NEC V80 Gibson rating (13.1 MIPS, 1989-03) and
  a Honeywell H632 modified Gibson (1968-11-25); both PDFs returned 403.
- Honeywell 300's vendor Gibson ratings are in [historical sources](historical-sources.md#honeywell-300).
- Wikipedia tables and the author's GitHub mirror repeat Longbottom's compilation
  and are not additional samples.
