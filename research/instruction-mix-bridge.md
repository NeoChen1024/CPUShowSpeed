# Gibson / ADP bridge preparation

Reviewed: 2026-09-28; pairing recomputed on resolved systems 2026-10-02 (schema
step 5c). Status: implemented source inventory, resolved-system pairing and
SPEC89/SPEC92 feasibility audits. The joint network fit that calibrates mix
values to VAXen is the [mix network](instruction-mix-network.md), refitted on
resolved systems on 2026-10-02.

## Reproduce and inspect

```sh
uv run cpushowspeed classic mix-inventory
```

The command reads the cached Longbottom CCTA/TSU mix source. It validates the original blob's BLAKE3, independently reparses its
190 table rows, and checks both sets of extracted raw rows against that original
HTML. It validates both operation-weight tables and exports all 380 mix listings,
including missing scores. Numerical source cells are calculated ratings, not
newly verified hardware executions.

Output: `data/derived/classic/mix-study/`, with `mix-records.csv`,
`mix-weights.csv` and `audit.json`; `data extract` loads the positive listings as
`mix:longbottom-cpumix` results. Pairing with classical results happens in
`classic mix-bridge` over resolved systems. The small
[review artifacts](data/classic/mix-study/) are versioned. The former
[candidate alias list](data/classic/mix-candidate-aliases.csv) was converted in
step 4 into open `system_link` reviews; it is **not** approval of configuration
equivalence and is read only by that review import.

## Source and definition findings

Primary compilation: Roy Longbottom's
[Computer Speeds From Instruction Mixes](http://www.roylongbottom.org.uk/cpumix.htm),
already cached by the project. The live page timed out during this pass. The
[author's ResearchGate copy](https://www.researchgate.net/publication/318793156_Computer_Speeds_From_Instruction_Mixes_pre-1960_to_1971)
corroborates the compilation's scope and operation definitions; it is the same
work, not independent measurements.

| Inventory | Gibson | ADP |
| --- | ---: | ---: |
| Source machine/configuration listings | 190 | 190 |
| Positive KIPS cells | 177 | 183 |
| Missing score listings retained | 13 | 7 |
| Operation categories | 12 | 7 |
| Sum of weights | 1.000 | 1.000 |

174 of the 190 source rows have both scores (173 distinct source machine labels). The Gibson variation includes
12.9% floating-point operations; ADP has no explicit floating-point category.
Store the version as **CCTA/TSU variation reproduced by Longbottom**, rather than
assuming every historical "Gibson Mix" uses these weights.

The source defines:

\[
T_{\mu s}=\sum_i w_i t_{i,\mu s},\qquad
KIPS=\frac{1000}{T_{\mu s}}a.
\]

Here `a` is an architecture adjustment reported as ranging from 1 to 2, often
1 for accumulator/single-address designs and 1.25 for a single address plus
multiple registers. Individual table rows do not supply their exact factors.
Thus the stored scores already include an adjustment: do not apply it twice,
and do not silently remove it by assuming a per-machine value. Eight-character
transfer and arithmetic categories describe work that may require multiple
native instructions, software routines or different precisions. KIPS/1000 is
not Dhrystone DMIPS or measured SPEC throughput.

The earliest explicit source-table years with positive values are 1954 (IBM 650
and ICL 1202). They are chronology leads, not yet approved timeline dates. The
PDP 8E row's 1968 date and option naming remain unresolved and must not overwrite
existing PDP-8/E chronology. Honeywell 300's separately verified vendor Gibson
ratings remain a distinct, unestablished mix variant.

## Actual bridge candidates

Mix results pair with classical results of the **current classical inventory**
(not only SPEC-era machines) in two scenarios:

- `resolved_system`: both resolve to the same `system_id`.
- `plus_pending_links`: additionally, the system links a review leaves open
  (`needs_review`, from the former alias list); rejected links never pair.

Target values are original interpreted classical scores; predicted VAXen values
were not used to manufacture bridge observations. No pairing is approved.

| Mix | Classical metric | `resolved_system` pairs / systems | `plus_pending_links` pairs / systems |
| --- | --- | ---: | ---: |
| Gibson | Whetstone native MWIPS | 19 / 9 | 40 / 15 |
| Gibson | Whetstone DP MWIPS | 8 / 6 | 25 / 12 |
| Gibson | LINPACK n=100 MFLOPS | 5 / 2 | 5 / 2 |
| ADP | Whetstone native MWIPS | 14 / 8 | 35 / 14 |
| ADP | Whetstone DP MWIPS | 5 / 5 | 22 / 11 |

Total: **127 metric pairs**, 76 of them only through pending links. Counts
overlap across metrics and variants. There are **no Dhrystone pairs**. The
former name-based run (2026-09-28) found 131 pairs on 37 configurations; its
tables are archived in [`data/archive/name-pairing/`](data/archive/name-pairing/README.md).

The five LINPACK pairs come from CDC 6600/7600, with no ADP score for those mix
rows. They are useful diagnostics, but two related machines cannot establish
broad architecture coverage. The main prospective bridges are therefore
**Gibson/ADP → Whetstone native/DP → existing classical calibration → VAXen**.

### Review priorities

1. **IBM 360/30, 360/50; 370/145, 370/155, 370/165; ICL 1906A/1906S:** start with
   names that match without family substitution. Confirm arithmetic facilities,
   memory-cycle assumptions and the source program/precision description.
2. **CDC 6600/7600:** check the Whetstone/LINPACK paths separately; the
   "6600 (Cyber74)" alias remains a candidate, not confirmed identity.
3. **ICL KDF9 and 1904 variants:** preserve language/optimization and plus-marker
   distinctions. KDF9 native Whetstone configurations in the present inventory
   range from 0.002 to 0.08 MWIPS; that is a reason to examine environment and
   workload semantics, not to discard inconvenient scores.
4. **PDP-8/E, PDP-11, HP 2100:** resolve EAE/EAU/FPU/software-floating-point options
   and base-model names before considering any pair approved. The existing name
   normalizer drops some option flags, so normalized matching is not sufficient.
5. **IBM 360/65 G versus H/I/J:** inspect memory-size/interleaving distinctions.
   Different memory capacity alone is not a rejection criterion; timing and
   architecture differences must remain explicit.

## Planned numerical experiments

The 2026-09-28 experiment below implements provisional versions of steps 1-2
on unapproved candidate cohorts, including a literal-name sensitivity subset.
Configuration approval, independent-source validation and chain propagation
remain outstanding.

After evidence review, export approvals with model/configuration group IDs and
reasons, retaining every source observation. The next experiment should:

1. Fit four separate zero-intercept geometric-ratio edges: each mix against
   Whetstone native and DP. Do not merge native, SP and DP merely by label.
2. Use the project's model-centered weighting and primary P95 definition, plus
   leave-one-model-out and whole-source holdouts where coverage permits. All
   variants of a held-out physical model must leave together.
3. Compare Gibson-only, ADP-only and joint estimates on the same held-out machines.
   Their shared operation timings and source compilation create dependence;
   they are not two independent confirmations of capacity.
4. Propagate the new bridge uncertainty with the saved classical calibration,
   preserving shared machines and bootstrap dependence. Do not train against
   existing predicted VAXen and then count those predictions as new SPEC evidence.
5. Report interval growth and architecture/environment residuals as limitations;
   do not remove rows merely because the prediction error is large.
6. Publish a distinct `instruction_mix_estimate` route only after the audited
   bridge exists. Pending rows may be shown in an evidence table, but have no
   invented VAXen or CI95.

The separate reconstruction route remains available later: map each weighted
operation to instruction/routine timing, verify against published examples and
then extend to machines lacking a compiled benchmark. The current inventory
already supplies numerical historical ratings, so simulation is not required
before testing the archival bridge.

## Additional source leads

- Gibson's **IBM TR 00.2043** remains a bibliographic lead; a search located the
  citation in a Computer Architecture historical appendix, not the original
  report. Do not claim its weights have been independently recovered.
- **Guide to the Processing Speed of Computers**, associated with NPL/Clifford
  Nott: the expanded search below recovered Wichmann's account and two summary
  figures. The underlying report and individual benchmark tables remain missing.
- Wikipedia mirrors repeating Longbottom's table are source copies, not additional
  calibration samples. Seek CCTA/NPL records, vendor timing reports and original
  benchmark results for independent evidence.

## Expanded web search, 2026-09-27

The [source hunt](data/classic/mix-study/source-hunt.csv) records twelve source
dispositions, including unsuccessful retrievals and shared-source copies.
[Acquisition records](data/classic/mix-study/source-hunt-acquisition.csv) retain
URLs, local paths, sizes and SHA-256 hashes for five acquired PDFs (including
the subsequently user-supplied SC-3 paper). Large
source files remain outside Git. This is a bounded search, not a claim that all
online sources have been exhausted.

### Newly transcribed source values

[Additional observations](data/classic/mix-study/additional-observations.csv)
contains **six absolute ratings and four relative table cells**. All ten cells
were checked against rendered original pages. They are vendor claims, not
independently verified benchmark executions. They are a separate reviewed
evidence file; `classic mix-inventory` does not ingest them yet. Existing
candidate counts and fits are unchanged.

| Source configuration | Reported Gibson-Mix I MIPS | Converted KIPS |
| --- | ---: | ---: |
| TR 440/200, one processor | approximately 0.48 | 480 |
| TR 440/400, one processor | approximately 0.83 | 830 |
| TR 440/400, two processors | approximately 1.49 | 1490 |
| TR 440/500, one processor | approximately 1.2 | 1200 |
| TR 440/500, two processors | approximately 2.04 | 2040 |
| TR 440/500, three processors | approximately 2.76 | 2760 |

Source: Telefunken, [TR 440 overview](http://computermuseum.informatik.uni-stuttgart.de/ftp/telefunken/tr440/doku/TR440_Ueberblick.pdf),
physical pages 3-4, printed A0-3/A0-4. The archive HTTPS certificate failed
verification; the public HTTP URL supplied the saved PDF. Its document date
remains unknown. `Rechnerkern` counts are retained as processor counts, not
silently interpreted as a modern core count. The document specifies different
memory systems for the models. No division by processor count was applied.
Equivalence of **Gibson-Mix I** and the CCTA variation remains unestablished.

Xerox's [Sigma 6/9 Sales Guide](https://www.bitsavers.org/pdf/sds/sigma/Sigma_6_9_Sales_Guide_Feb72.pdf),
dated 1972-02-20, identifies its scientific mix as Gibson on physical page 18
and gives the following ratios on physical page 20 (printed 103/001-13):

| Mix | Sigma 6 reference | Sigma 9 |
| --- | ---: | ---: |
| Scientific/Gibson | 1.0 | 1.6 |
| Commercial, unspecified | 1.0 | 1.7 |

The two reference cells define normalization; they are not two independent
measurements. The commercial mix is **not explicitly identified as ADP**.
These ratios cannot supply absolute KIPS without another justified anchor.

### Highest-value remaining leads

1. **SC-3 spacecraft computer:** Stone and Kroesche's
   [1991 conference abstract](https://digitalcommons.usu.edu/smallsat/1991/all1991/36/)
   describes Gibson, Whetstone and Dhrystone on a 16 MHz 80386/80387 across
   memory/cache/wait-state modes. It is a particularly useful potential common
   configuration bridge. Automated PDF downloads returned HTTP 403; the user
   subsequently supplied the seven-page PDF from their download directory.
   Its title and authors match and its hash is recorded. The 2026-09-28 review
   below transcribes its numerical tables and identifies a memory-mode mismatch.
2. **NPL/CCA summary:** Wichmann's firsthand account in
   [Computer Resurrection 33](https://www.computerconservationsociety.org/resurrection/res33.htm)
   says the Nott guide was prepared but publication was stopped. Its figures 2
   and 3 survive in the issue PDF (physical pages 24-25, printed 22-23), including
   KI10, KL10 and several PDP-11 models. The rendered figures show composite
   performance ranges on an instructions/millisecond axis. They do not label
   individual Gibson/ADP observations or establish a CI95 interpretation.
   Recover the underlying analysis before digitizing them as benchmark scores;
   CCA provenance also means potential dependence on Longbottom's compilation.
3. **Wichmann CCU Report 11 (1970):** indexed author-uploaded text in
   [Some Statistics from ALGOL Programs](https://www.researchgate.net/publication/242495225_Some_Statistics_from_ALGOL_Programs)
   section 5.4.2 ranks fifteen machine/compiler combinations by a ratio involving
   Gibson and the Algol mix. This is direct historical cross-metric work, but the
   ranks must not become fifteen invented absolute Gibson values.
4. **CCTA originals:** Technical Note 3806 Issue 5 and Technical Memorandum 1163
   (1977) remain bibliographic targets. The secondary claim of 212 sets differs
   from the 190 rows recovered here; this does not yet establish 22 missing
   usable results. The author's GitHub mirror describes the same 190-result
   compilation and is not an independent sample source.
5. **Contemporary vendor claims:** indexed Electronics pages mention a 33 MHz
   NEC V80 Gibson rating of 13.1 MIPS (1989-03, printed page 19), and a Honeywell
   H632 modified-Gibson advertisement (1968-11-25, printed page 53). Both PDF
   downloads returned 403; their numbers remain leads rather than verified cells.

The recovered HP Journal 1971-10 issue discusses faster standard instruction
mixes and cites Gibson's report; the text search did not identify an absolute
Gibson rating. A 2021 Russian comparison adds BESM-1/STRELA estimates by assuming
a factor of 0.8, while repeating older Western rows. Those are explicitly
derived estimates, not independent observed Gibson/ADP results. A 1985 mbp COBOL
advertisement uses the Gibson name for a representative COBOL statement mix;
its semantic level requires separate review.

**Outcome:** additional Gibson evidence was recovered; no independently verified
new absolute ADP table was recovered in this pass. Keep every variant and source
identity available for review, and approve equivalence before adding these
records to bridge fitting or VAXen timeline estimates.

## OCR acquisition batch

Started on 2026-09-27. On 2026-09-28 the inventory showed that the first run had
stopped at AFIPS physical page 457 (repeated OCR output), with 1,417/1,418 pages
completed. The dependent external batch had consequently not started. It was
started explicitly and the AFIPS page retried. See the review below and use the
live inventory report for completion. Recovery outcome on 2026-09-28:
external OCR completed all 153 pages; AFIPS page 457 again failed repetition
validation. Seven documents / 920 pages are published, and another 650 AFIPS
pages are successful in staging (1,570/1,571 successful pages in total). The
AFIPS source's embedded text was screened separately and its relevant original
pages visually checked; its unpublished DocIR is not counted as complete.
The selection covers 8 documents / 1,571 pages:

| Collection | Documents | Pages | Processing |
| --- | ---: | ---: | --- |
| Local bitsavers mirror | 4 | 1418 | 3 published; AFIPS has one failed page |
| External PDFs, including SC-3 | 4 | 153 | All published on 2026-09-28 |

The bitsavers paths were verified under the root recorded in the existing
inventory, `/net/DF32_Pool/neo_chen/archive/bitsavers/pdf`. They are read directly
from that mirror. The external copy of Sigma is not selected a second time.
The long AFIPS and Interex volumes are processed in full to preserve context
around the mix references; their inclusion does not assert that every page
contains relevant numerical results.

Selections: [bitsavers](../inventories/instruction-mix-bitsavers-ocr.txt) and
[external](../inventories/instruction-mix-external-ocr.txt). The external source
root is `data/raw/classic/mix-hunt-2026-09-27/`. Its inventory database is
`data/derived/documents/mix-external-inventory.sqlite`; the existing bitsavers
database remains tied to its original root. Both batches use Chandra at
`http://localhost:30000/v1`, 8 rendering workers, 64 inflight pages and a
2048 MiB rendering buffer. During recovery, only three external pages remained
when the AFIPS single-page retry started with `--inflight-pages 1`; combined
inflight work stayed below 64. Raw OCR and DocIR outputs are unverified reading aids.

Resume the batches with these commands, in sequence:

```sh
uv run cpushowspeed documents ocr \
  --database data/derived/documents/inventory.sqlite \
  --output-root data/derived/documents/chandra-ocr \
  --file-list inventories/instruction-mix-bitsavers-ocr.txt \
  --api-base http://localhost:30000/v1 --model chandra \
  --jobs 8 --inflight-pages 64 --buffer-mib 2048
uv run cpushowspeed documents ocr \
  --database data/derived/documents/mix-external-inventory.sqlite \
  --output-root data/derived/documents/mix-external-ocr \
  --file-list inventories/instruction-mix-external-ocr.txt \
  --api-base http://localhost:30000/v1 --model chandra \
  --jobs 8 --inflight-pages 64 --buffer-mib 2048
```

Use `documents report` with the corresponding database, output root and file
list for current completion. Image captioning is a separate stage. The selected
numeric evidence review below does not certify every OCR page.

## First OCR evidence review, 2026-09-28

The [eight-document review ledger](data/classic/mix-study/ocr-review-ledger.csv)
distinguishes published OCR screening, embedded-text fallback and original-page
checks. The current search covers 920 published pages with 16 keyword-hit pages;
the 651-page AFIPS embedded text was searched separately while its one failed
OCR page prevents full-document publication.

`uv run cpushowspeed classic mix-evidence` reproducibly screens the eight selected
documents' **published** DocIR, including structured table cells. It writes
unverified keyword excerpts to `data/derived/documents/mix-evidence/hits.jsonl`
and source/DocIR hashes, scanned page counts and missing-document status to
`manifest.json`. Missing unpublished documents remain explicit. Keyword hits
are navigation aids; surrounding pages and figures may contain relevant values
without repeating a benchmark name. A negative search is not proof of absence.

### SC-3: twelve source-checked benchmark observations

The [curated SC-3 CSV](data/classic/mix-study/sc3-observations.csv) records all
12 primary score cells from Tables 3-5, checked against physical PDF pages 5-6.
Physical pages 2 and 7 were also inspected for clocks, hardware and references.
Reported units, cache state, memory bus width, wait states and original ratios
remain separate fields. No fitting or timeline inclusion has been performed.

| Benchmark/configuration | Original score |
| --- | ---: |
| Qualified Gibson, SC-2, 8 MHz, 16-bit memory | 539 thousand Gibson operations/s |
| Qualified Gibson, SC-3, 16 MHz, 16-bit memory | 713 thousand Gibson operations/s |
| Dhrystone 2.1, SC-3, 32-bit, 2 waits, cache off/on | 3902 / 6620 Dhrystones/s |
| Dhrystone 2.1, SC-3, 32-bit, 5 waits, cache off/on | 2533 / 6564 Dhrystones/s |
| Dhrystone 2.1, 25/33 MHz 386 PC clones | 10638 / 13514 Dhrystones/s |
| Whetstone, SC-3, 32-bit, 2/5 waits, cache off | 1.244 / 0.966 million Whetstones/s |
| Whetstone, 25/33 MHz 386 PC clones | 2.500 / 3.302 million Whetstones/s |

**Bridge interpretation:** the two Gibson runs use the same binary in 16-bit
memory; the classical runs use 32-bit memory. Matching only `SC-3` would conceal
a material configuration change. There is no directly interchangeable
Gibson/classical configuration pair established by these tables. Two SC-3
Dhrystone/Whetstone pairs do share stated 32-bit, cache-off, wait-state settings,
but Whetstone precision remains unspecified. Do not label it SP, DP or an
existing Native variant by assumption. PC FPU details and the Whetstone PC cache
state are not fully specified either.

The paper names Metaware High-C for the classical benchmarks, with no version
or flags. It says Dhrystone's allocation and console calls were removed while
the measured loop was unchanged. These are author-reported executions, not new
reproductions of the experiment. Its **qualified Gibson** references Carney,
"Selecting On-Board Satellite Computer Systems", Computer 16(4), 1983-04,
pp. 38-40. The operation weights and relationship to CCTA remain unverified.

[Arithmetic checks](data/classic/mix-study/ocr-review-checks.json) reproduce the
reported approximate improvements: Gibson 32.28%, Dhrystone caching 69.66%
(2 waits) and 159.14% (5 waits). Cached Dhrystone has similar per-MHz rates across
these systems, consistent with the authors' explanation that it fits in cache.
That supports a configuration-conditioned clock-scaling hypothesis, not a
universal multiplier for all memory modes or architectures.

### DINKIAC I: a source-backed reconstruction example

Richard W. Conn's "The DINKIAC I—A pseudo-virtual-memoried mini—For stand-alone
interactive use", AFIPS SJCC 1971, starts at physical page 9 (printed page 1)
of the [local-mirror proceedings](https://www.bitsavers.org/pdf/afips/1971-05_%2338.pdf).
Physical pages 13-15 (printed 5-7) were visually reviewed. Figure 2 supplies
seven operation groups, their Gibson percentages and delay-line revolution
times; Figure 4 supplies 31 simulation durations and two explicit missing cells.

- [Operation weights and timings](data/classic/mix-study/dinkiac-mix-weights.csv):
  percentages sum to 100; the weighted time is 8.6245 revolutions, matching the
  author's rounded 8.6.
- [Simulation results](data/classic/mix-study/dinkiac-simulation-results.csv):
  all 33 table positions retained, including two source dashes. The 31 durations
  range from 120391 to 707961 ms across memory/page/predictability cases.

The article models software subroutines for missing arithmetic hardware and
explicitly states that one Gibson operation can correspond to multiple native
instructions. The simulation further simplifies this mapping. Work per run is
only approximately 12,300 instructions and varies by run, so the durations are
not silently converted into exact KIPS. These are **simulation-model results**,
not measured performance of a historical production computer. They provide a
useful reconstruction precedent without supplying a new measured VAXen anchor.

### Other batch documents

The Sigma, TR 440 and NPL figures retain the source interpretations recorded
above. NBS Volume 2 locates a methodological Gibson quotation at physical page
63 and a related bibliography lead at page 90; the HP Interex volume locates
HP 1000 design history and references at pages 19 and 31. Neither search located
a new absolute mix table. HP Journal 1971-10 discusses standard instruction-mix
speed improvement on page 5 and cites Gibson on page 9; it does not establish
an absolute Gibson rating in those passages. Other AFIPS Gibson-name hits in
the embedded text concern authors of unrelated papers; only the DINKIAC passage
has yielded new mix reconstruction data in this review.

All new numerical records retain original-page locators and SHA-256 hashes.
Their `fit_eligible=false` flags preserve unresolved variant/configuration
questions. None has been rejected because of a fitted residual; no residuals
have yet been calculated for this material.

## Direct SPEC89 feasibility and classical trial fits, 2026-09-28

Reproduce after `classic mix-inventory` with:

```sh
uv run cpushowspeed classic mix-bridge --bootstrap 2000 --seed 20260928
```

The command reads the built database and records its input digest and code
hashes. Results and PNG/SVG scatterplots live under
`data/derived/classic/mix-bridge/`; compact `bridge-*` snapshots are versioned in
[data/classic/mix-study/](data/classic/mix-study/). Every pairing remains in the
full exported pair tables. No production coefficients changed.

Since step 5c (2026-10-02) the command reads only the database. The 360 positive
CCTA/TSU listings enter; the curated TR 440, Sigma and SC-3 cells below are not
yet database observations and no longer enter its audit. The counts in the
following two SPEC subsections were recomputed on that basis.

### Direct mix → SPEC89: no current model intersection

The audit compared 390 mix listings: 380 CCTA/TSU rows (including missing
values), six TR 440 ratings, two Sigma scientific relative cells and two SC-3
qualified-Gibson results. The unspecified Sigma commercial cells and DINKIAC
simulation durations are different quantities and are not absolute ADP/Gibson
score inputs. Of the 390 listings, 370 have positive values, including the two
Sigma relative cells; these units are not pooled.

No mix result shares a resolved system with a SPEC89 result: **zero pairs**
for all three target metrics. This is an input-coverage result, not a claim that
no overlap can exist in undiscovered archives.

| SPEC89 target | Positive values | Resolved systems | Mix pairs |
| --- | ---: | ---: | ---: |
| SPECint89 | 182 | 91 | 0 |
| SPECmark89 | 264 | 132 | 0 |
| SPECfp89 | 207 | 106 | 0 |

Counts overlap across metrics. Reference-definition records are counted and
identified separately in the coverage CSV, not treated as new executions.
VAX-11/780 being the SPEC reference cannot create a missing Gibson/ADP score.

The retained CPU-family lead is SC-3 versus `spec89:A0094`, a generic 33 MHz
`i386/387` with **SPECmark89 4.3**, no SPECint89 and cache label `64+0`.
SC-3's Gibson result is at 16 MHz on a 16-bit memory path. Shared CPU family
alone does not justify equating machines or scaling this Gibson result by
33/16. The selected linear-clock presumption for Dhrystone/Whetstone does not
establish one for Gibson, whose memory operations and mix definitions differ.
SPECmark89 must also remain separate from SPECint89; substituting 4.3 as an
integer score would create a false bridge. Consequently no direct coefficient,
CI95 or empty scatterplot is manufactured for SPEC89.

To make a direct edge identifiable, prioritize genuine mix results for machines
already represented in SPEC89 (e.g. VAX variants or sufficiently specified
386/486 configurations), or original SPEC89 results for machines in the mix
inventory. The source unit, mix version and memory/arithmetic configuration
must accompany the scores. Multiple independent model groups are needed to
assess transfer error; more submissions of one machine do not supply that
architecture diversity.

### Classical bridges: conditional fits on all existing candidates

Five edges were fitted using the established zero-intercept model `y = kx`.
Here `x` is mix KIPS and `y` is the **original classical score**, not VAXen.
Each resolved classical system contributes its median log score ratio, and
`k` is the geometric mean across those system centers. Repeated observations
remain represented in their existing configuration aggregates and pair rows;
there is no error-based deletion. Systems are held out together. The primary error statistic is model-center P95; the table below explicitly
reports the secondary model-balanced observation P95 to retain within-model
spread. Coefficient CI95 uses model bootstrap resampling.

`plus_pending_links` scenario:

| Mix → classical score | Pairs | Systems | k (classical unit / mix KIPS) | Held-out observation P95 |
| --- | ---: | ---: | ---: | ---: |
| Gibson → Whetstone native MWIPS | 40 | 15 | 0.000816159 | 146.4% |
| Gibson → Whetstone DP MWIPS | 25 | 12 | 0.000265175 | 307.8% |
| Gibson → LINPACK n=100 MFLOPS | 5 | 2 | 0.000232879 | 73.8% |
| ADP → Whetstone native MWIPS | 35 | 14 | 0.000408053 | 677.0% |
| ADP → Whetstone DP MWIPS | 22 | 11 | 0.000135528 | 982.8% |

`resolved_system` scenario (no pending link):

| Mix → classical score | Pairs | Systems | k | Held-out observation P95 |
| --- | ---: | ---: | ---: | ---: |
| Gibson → Whetstone native MWIPS | 19 | 9 | 0.000800293 | 144.8% |
| Gibson → Whetstone DP MWIPS | 8 | 6 | 0.000402074 | 394.7% |
| Gibson → LINPACK n=100 MFLOPS | 5 | 2 | 0.000232879 | 73.8% |
| ADP → Whetstone native MWIPS | 14 | 8 | 0.000436453 | 835.0% |
| ADP → Whetstone DP MWIPS | 5 | 5 | 0.000247937 | 181.1% |

The earlier name-matched run (2026-09-28) gave, for example, Gibson → Whetstone
native 0.000759617 on 16 model groups and ADP → Whetstone DP 0.000121170 on 12.

The large tail errors describe variation under these assumed matches; they are
not a declaration of failure or grounds for removing points. Language/compiler,
software floating point, model options and unreviewed aliases remain possible
contributors. The `resolved_system` scenario is a matching sensitivity check,
not chosen as a replacement cohort because its errors differ. A shared resolved
system does not itself validate configurations.

[Scatterplots](../data/derived/classic/mix-bridge/classical-mix-scatter.png) show
all candidate points plus both fitted lines and conditional coefficient CI95.
Those bands are **not** observation prediction intervals. LINPACK's relatively
smaller P95 rests on just CDC 6600/7600 and should not be interpreted as stronger
coverage than the Whetstone edges. All candidates remain unapproved. Further
VAXen propagation requires configuration review and a coherent uncertainty chain;
these exploratory factors do not authorize treating predicted VAXen as observed
SPEC training data.

### SPEC92 fallback audit: also no current direct intersection

The same command also audits SPEC92, preserving speed/rate and integer/FP
identities. The cached speed summaries are useful archaeological input here;
this does not change the project's production integer-rate target.

| Metric (all database scopes) | Positive values | Resolved systems | Mix pairs |
| --- | ---: | ---: | ---: |
| SPECint92 | 363 | 229 | 0 |
| SPECbase_int92 | 230 | 144 | 0 |
| SPECfp92 | 78 | 54 | 0 |
| SPECrate_int92 | 331 | 151 | 0 |
| SPECrate_base_int92 | 199 | 104 | 0 |

These **1,201 values** are not 1,201 independent submissions: metrics and
source compilations can describe the same system or result repeatedly.  The
counts span every database scope reporting the metric (the CPU92 results,
including the Netlib speed summaries, the DEC report columns and the DEC OpenVMS
table), so they differ from the former per-source-cohort table. SPECbase_fp92 is
no longer audited. No coefficient is computed from zero pairs. The
compact `bridge-spec92-target-coverage.csv` and audit snapshot retain counts and
the database input digest.

A targeted review of apparent old-model substrings found modern names such as
AlphaServer 2100 and RS/6000 360/370, not HP 2100 or IBM System/360 and /370.
No generic 386 result was found in these SPEC92 score rows. Loosening matches
by bare model number or manufacturer would manufacture spurious overlap.
Thus both SPEC89 and SPEC92 direct edges remain **unidentified from the current
inventory**, while the classical route has data for conditional exploration.

The joint mix → classical → SPEC92 rate network (`classic mix-network-fit`) was
removed on 2026-10-02 and rebuilt the same day on resolved systems; see the
[mix network](instruction-mix-network.md).
