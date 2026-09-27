# Hardware-year evidence: archive and web research

Reviewed: 2026-09-27. Current date catalog: **593 events**.

## Completed first batch

Status: **80/80 PDFs and 947/947 OCR pages complete**.
The hardware-year review is complete for all 80 documents: all 947 pages were
text-screened, with 145 relevant original pages visually checked (including
previous checks). This is a date-scope review, not verification of every claim
or benchmark value in every PDF. Remaining configuration dating continues
beyond this batch.

## Candidate inventory

The first pass lists **625 candidate files**, with family scope, target system
names, source-relative path, page count, BLAKE3, selection reason and OCR selection:

- [Candidate CSV](../inventories/hardware-year-candidates.csv).
- [Search rules and selection metadata](../inventories/hardware-year-search.json).
- [First OCR batch](../inventories/hardware-year-ocr.txt): **80 PDFs / 947 pages**.

These are discovery leads, not assertions that every candidate mentions every
listed target. The search covers DEC VAX/Alpha/PDP, IBM, HP, Apollo, Sun, Amdahl,
CDC, Unisys predecessors, Prime, Cray, SGI, Pyramid and ICL. Short Datapro reports
and product brochures are prioritized, with round-robin vendor/family coverage,
model-number hits, 4–30 pages and BLAKE3 deduplication within the OCR batch.
Duplicate mirrors and longer documents remain visible in the candidate CSV.
This is not an exhaustive full-text search of the entire mirror.

```sh
uv run cpushowspeed documents year-candidates
```

The default uses the current undated queue. To reproduce the initial selection,
use `--targets data/derived/documents/year-evidence/targets-at-selection.csv`.
That snapshot's SHA-256 matches the original target hash in the search metadata.
The command rewrites candidate and batch inventories, so preserve an active batch
before intentionally generating a new selection.

## OCR and discovery

The completed batch used the existing Chandra output root and resume state:

```sh
uv run cpushowspeed documents ocr \
  --output-root data/derived/documents/chandra-ocr \
  --api-base http://localhost:30000/v1 --model chandra \
  --jobs 8 --inflight-pages 64 --buffer-mib 2048 \
  --file-list inventories/hardware-year-ocr.txt
```

The live endpoint identified its model as `chandra` before dispatch. The source
root is the existing inventory root; PDFs remain immutable. Output is raw JSONL,
DocIR and image crops. This task does not require image-caption backfill to read
ordinary date tables. No document is considered processed merely because its
first pages have completed. Check actual completion with:

```sh
uv run cpushowspeed documents report \
  --output-root data/derived/documents/chandra-ocr \
  --file-list inventories/hardware-year-ocr.txt
uv run cpushowspeed documents year-evidence
```

The second command searches PDF text layers and whatever DocIR documents are
already published. It saves unreviewed passages to
`data/derived/documents/year-evidence/date-hits.jsonl`, with PDF page numbers and
source hashes, plus `search-audit.json`. It can be rerun after more OCR completes.
Text-layer extraction remains useful while OCR runs, but neither is verified
historical evidence until checked against original pages.

## Completed date-scope review

[Document review ledger](data/historical/year-document-reviews.csv) has one entry
for every batch PDF, including source BLAKE3, total/text-screened pages, original
pages visually checked, reused prior checks, disposition, event IDs and notes.
All 80 original PDF hashes were rechecked against the mirror on 2026-09-27.

| Disposition | Documents |
|---|---:|
| Date events recorded | 41 |
| Date events or source-label conflicts recorded | 13 |
| No explicit hardware launch date found | 17 |
| Software, pricing or event information only | 6 |
| Customer orders/installations only | 3 |
| **Total** | **80** |

The review screened all published text, then inspected date tables, chronological
passages, surrounding wording and page-local publication information against
original PDF images. Documents without keyword hits were also included. A
negative disposition means no usable explicit date was found in this review;
it is not proof that no date could ever be recovered. OCR search still contains
641 candidate passages/blocks, including duplicates and unrelated dates.

[Batch review index](data/historical/year-review-batch1.csv) is the refreshed
snapshot of `documents year-evidence` output. That command preserves completed
manual dispositions only when source hash and page coverage match the ledger.
OCR completion or the presence of a curated event alone does not imply completed
source review.

## Curated events and interpretation

[hardware-date-evidence.csv](data/historical/hardware-date-evidence.csv) contains
**337 events at first-batch completion**: **332 original-PDF-checked entries** and **5 previously checked
web announcement dates**. This full-batch pass adds **265 events** to the previous
72. The entries cover 54 PDFs; the other 26 documents have explicit non-event
review dispositions rather than invented launch dates.

- Dates retain their precision: `YYYY`, `YYYY-MM` or `YYYY-MM-DD`; quarters use
  year plus a separate `quarter` column. `date_raw` retains qualifiers when needed.
- Announcement, introduction, first delivery, installation and option events
  remain distinct. `source_page_date` is the date on the reviewed page when known;
  it can differ from the PDF filename or another page in the same PDF.
- A prospective delivery, or a delivery internally inconsistent with its own
  announcement, is retained but not selected as confirmed availability.
- Selected entries are **model-era proxies**, not exact dates for every tested
  clock, CPU count, FPU, memory, compiler or OS configuration. Announcement dates
  are used where no confirmed delivery was established; they are not relabeled
  as delivery. Same-model confirmed delivery is preferred where available.
- Physical PDF pages are one-based. Blank printed-page labels mean the physical
  locator is canonical; no printed label was supplied in that transcription.
- Publication/copyright years and customer orders are not CPU introduction dates.
- Repeated reports remain separate evidence, not independent statistical samples.

### Conflicts and configuration boundaries

- **Amdahl 5860:** 1982 Q3/Q4 versus 1983 Q3 are printed in different passages.
  The 1982–1983 evidence span remains visible. **5867** delivery in 1982 precedes
  its own 1984 announcement; these rows remain unselected. Other prospective
  quarters remain forecasts, even under a table heading called first delivery.
- **Amdahl 1987 PDF:** appended pages 22–23 are dated 1988-07. They establish the
  5990 announcement on 1988-05-03, not a 1987 launch. Page 3 explicitly confirms
  5890-200E shipments in March, but still describes 190E/300E shipments as planned.
- **MicroPDP-11/53:** the 1991 table conflicts with the 1988 table. Both original
  claims are retained; dates were not silently repaired. Plus variants remain
  separately named.
- **VAX 6000/310 and /410:** tables report 1989-07 and 1990-10, potentially reflecting
  reconfiguration. The evidence span is retained; dates are not automatically
  transferred to differently named 6310/6410 models. The VAX 4000 table's erroneous
  SPARC/RISC descriptions are not adopted as processor identification.
- **HP 3000:** original announcement, suspended marketing, reannouncement, CX and
  Series I/II/III/33 events are distinct. A Series I delivery date preceding its
  announcement is preserved as inconsistent. Publication year is not substituted.
- **Sperry 1100/90:** 1982/1983 reports forecast June 1983 or April 1984; the 1984-11
  report explicitly records delivery in 1983-12 and subsequent installations.
- **Configuration scope:** Cyber 810A/830A is not unsuffixed 810/830; DECsystems is
  not DECstations; Datasystem packaged configurations are not underlying PDP CPU
  introductions; CRAY-2S is not original CRAY-2. UNIVAC multiprocessor/storage
  variants and CDC floating-point options retain separate events.

The five web entries retain their earlier source citations to the user-accepted
Computer History Wiki (gunkies). This pass used the local archive and did not
perform another web search or change those entries.

## Timeline integration and remaining work

The [historical timeline](historical-vaxen-timeline.md) reads selected reviewed
events before bulk model-year catalogs; explicit conflict overrides still win.
The first-batch result had **896 dated / 815 undated rows**, spanning **1963–2002**.
Compared with the immediately preceding 891/820 run, **5 rows gained dates** and
**37 rows changed a point year or evidence span** (including those five).
[Change CSV](data/historical/year-review-batch1-changes.csv) records each change.

All **1,711** score, input-score and calibration-CI records were checked unchanged.
No benchmark fitting was rerun. Older catalog years can move when an explicit
source introduction replaces an approximate delivery-year proxy; the event type
and source remain visible in the output rather than pretending these are the
same historical event.

## Unknown-year expansion — 2026-09-27

The next pass starts from 815 undated rows (754 distinct source system names).
It searches **all 545 remaining PDFs** in the existing candidate inventory.
This is text/DocIR discovery across the complete candidate list, **not** a claim
that every page received visual review. An initial text-layer scan found 1,523
context hits. The standard `documents year-evidence` search subsequently produced
3,110 discovery hits, which are not independently verified date events.

**32 PDFs / 310 pages** lacked usable text and were processed with 64 inflight
pages. All 310 DocIR pages published successfully. This pass checked **26 local
original pages** plus **three external Apple fact-sheet pages** visually. It
also reused the previously checked Sperry 1100/90 page. The first 80-document
review ledger remains separate from this broader, partially reviewed search.

### Adopted evidence

The catalog adds **178 events**, for **515 total**. Sources include:

- Contemporary Datapro tables: VAX, IBM 370/4300/9370, HP 1000, ICL, CDC and
  UNIVAC/Sperry. Original-page citations and source BLAKE3 identify the evidence.
- DIGITAL's vendor-authored history preserved by Computer History Museum,
  IPSJ's computer museum, and NEC's announcement index.
- The RS/6000 model catalog attributed to IBM's Sales Manual; OpenPA,
  apple-history and sgistuff model histories. These remain identified as
  secondary catalogs, not newly recovered vendor announcement letters.
- Three AppleSpec Database fact sheets, and Sun's Ultra 1 announcement as
  preserved in SunFlash/Usenet. The release dateline, rather than the date of
  the Usenet posting, supplies the announcement date.
- Existing SPEC CPU2000 hardware-availability disclosures for ProLiant,
  pSeries and AlphaServer configurations. Platform name and clock are matched;
  explicit Opteron model numbers must also match. All distinct availability
  months are retained, without selecting by performance. These dates describe
  configurations, not the first introduction of a whole product family.

Dates remain model-era proxies. A base-model date does not date a later FPU,
CPU upgrade or memory configuration. Apple 9500/233, generic Macintosh/PowerPC
names, MicroVAX versus VAXstation variants, and unconfirmed forecast shipments
are not filled merely from a nearby product name. Explicit curated regex rules
now remain authoritative even when normalized model keys collide; the Amdahl
470/V8 spelling is explicitly included in its existing 470V/8 alias rule.

### Conflicts retained

- The 1981 UNIVAC report records 1100/80 first delivery in **1977-03**, while a
  1984 Sperry table reports introduction in **1980-05** without explaining the
  configuration boundary. Both remain in the CSV; the timeline shows the
  **1977–1980** source span. Its point year is a display midpoint, not a newly
  established launch date. SAM option availability remains unknown.
- Apple 7500/8500 sources disagree on the month within **1995**. Only the common
  year is adopted. Later clock revisions use their own chronology where given.
- The Apple support page headed Quadra 700 describes a PowerPC-upgraded system;
  its 1994 date is not used for the original 68040 configuration.
- Sun FAQ rows with ambiguous inherited year columns, an incomplete SGI family
  tree, and customer-use reports that establish existence but not introduction
  remain leads rather than launch evidence.

### Results and audit artifacts

The rebuilt timeline contains **1,087 dated / 624 undated rows**: **191 additional
rows dated**, with point years spanning **1963–2005**. The earliest plotted year
has not moved. All **1,711** input-score, VAXen, CI95 and observation-count records
were compared with the baseline and are unchanged; no fitting was rerun.

- [Audit and input hashes](data/historical/year-expansion-audit.json).
- [545-document search/review ledger](data/historical/year-expansion-documents.csv).
- [Web source snapshots and acquisition failures](data/historical/year-expansion-web-sources.json).
- [Unresolved source leads](data/historical/year-expansion-open-leads.csv).
- [754-name target disposition](data/historical/year-expansion-targets.csv).
- [Per-configuration date changes](data/historical/year-expansion-changes.csv).
- [Updated timeline and interpretation](historical-vaxen-timeline.md).

The remaining 624 rows are retained in the plot's unresolved panel and exported
queue. Their unresolved status means no acceptable date was established in this
pass, not that no source exists. CPU-only names, upgrades, regional variants and
obscure systems still need targeted identity and chronology research. Candidate
text search and broad web searches are not exhaustive Internet archaeology.

### PDP-11/70 chronology cross-check — 2026-09-27

[Wikipedia's PDP-11 model list](https://en.wikipedia.org/wiki/PDP-11#Models)
gives 1975 for the PDP-11/70. This agrees with the existing vendor-history
event `hardware-date-0391`, which records introduction in **1975-02** from
[DIGITAL's timeline](https://archive.computerhistory.org/resources/text/DEC/dec.digital_%28DEC%29_timeline_1957-1997.102630354/timelinetext.htm).
Both current output rows, `PDP 11/70` and `DEC PDP 11/70 FP`, already have point
year and date span **1975**. No date or performance correction was required.
The FP row remains a model-era estimate, not evidence of the exact option's
availability. Wikipedia is accepted as a secondary chronology source under
the [source policy](../docs/sources.md#hardware-chronology-sources).

## Wikipedia and museum continuation — 2026-09-27

Using the accepted secondary-source policy, this pass starts with 624 undated
rows and attempts 92 source URLs. **54 sources supply adopted date evidence**;
the remainder include failed retrievals, irrelevant redirects, missing variant
dates and unresolved chronology. The source manifest separates these states.
Wikipedia article revisions and cached HTML hashes are retained; bulk article
text remains outside Git. HP Computer Museum pages were checked through the web
reader, with local HTTP 403 snapshot failures explicitly recorded.

The pass adds **78 events** covering **97 distinct previously unresolved source
system names**, dating **105 rows**. The timeline now contains **1,192 dated /
519 undated rows**; the point-year span remains **1963–2005**. The 515 earlier
events remain unchanged. None of the previously dated rows changes year, and
all **1,711 input-score, VAXen, CI95 and observation-count records** match the
baseline. This pass performs no OCR, benchmark extraction or refitting.

Coverage includes Sun SPARCstation/Ultra, DEC AlphaStation/AlphaServer, Cray,
SGI, IBM PC/4300, HP 9000/300, AT&T, Acorn, Commodore, Pyramid, Cromemco, Alliant,
Sequent, Meiko, Multiflow and several Japanese systems. Examples are Cromemco
Z2 (1977), Pyramid 90x (1983-08), HP 9000/320 (1985), NeXTstation Turbo (1992-04)
and SPARCstation Voyager (1994-03); each event's canonical CSV row carries its
source and locator. These remain model-era estimates for benchmark configurations.

Announcement, market release, first delivery and demonstration are explicitly
separated. Cray-3's 1993-05 NCAR loan is a demonstration installation; Multiflow
14/200's 1987-05 event is a public demonstration, not an inferred general-sale
date. Later CPU modules, FPU options and regional releases are not automatically
dated by the base-machine event. All repeat benchmark observations remain.

### Unresolved examples

- Power Macintosh 8100/100: Wikipedia and apple-history reverse the chronology
  of the 100/110 MHz revisions across 1994–1995. The original 80 MHz date is not
  transferred to this configuration.
- MicroVAX 3100/90: Wikipedia's list says 1993-10-12, while 1992 contemporary
  material already discusses the new model. This conflict is retained as a lead,
  rather than adopting the encyclopedia date without further review.
- AlphaStation 200 4/233 and 500/400: dates are absent in the respective model
  rows. Adjacent dated rows do not establish these variants' introduction.
- MIPS RC3230 and RS3230 are not silently equated. Generic CPU-only names,
  unnamed clones and truncated identities still need identification work.

### Artifacts

- [Audit and baseline hashes](data/historical/year-wikipedia-audit.json).
- [Source URLs, Wikipedia revisions and snapshot status](data/historical/year-wikipedia-sources.json).
- [Date changes](data/historical/year-wikipedia-changes.csv).
- [Initially undated target disposition](data/historical/year-wikipedia-targets.csv).
- [Unresolved chronology and identity leads](data/historical/year-wikipedia-open-leads.csv).

The earlier expansion tables remain snapshots of their own pass. The current
`undated.csv` generated by the timeline is the latest remaining queue; neither
its entries nor the unadopted source manifest claim an exhaustive negative search.

## x86 CPU-release fallback — 2026-09-27

User-selected rule: when a remaining x86 configuration has an identifiable CPU,
use the CPU's release year as a hardware-era estimate without requiring the
original PC model's launch documentation. This supplements the model chronology;
it does not relabel CPU introduction as system availability.

[CPU proxy mappings](data/historical/cpu-release-proxies.csv) add dates to **99
rows**, yielding **1,291 dated / 420 undated** configurations and a **1963–2006**
point-year range. The 593 model-date events remain unchanged. All earlier dated
rows keep their years; all 1,711 numeric results, input scores, observation counts
and calibration CI95 values match the baseline.

Sources include Intel's chronological processor reference and launch releases,
and Wikipedia's processor model tables. Pentium clock grades are dated separately:
60/66 MHz to 1993, 75/90/100 to 1994, 120/133 to 1995 and 166 to 1996. Likewise,
the 486DX 33/50 MHz dates differ from the 486 family's initial release. AMD
Am486, Am5x86, Athlon/Duron/Opteron and Cyrix 5x86 retain their own chronologies.
Each mapping contains its URL and locator, plus a cached revision/hash where
available. No original benchmark names or CPU strings are overwritten.

Mappings target exact configuration IDs and validate the source name, CPU and
clock before applying. The two Escom configurations therefore receive separate
486DX2 and Pentium dates. Known model dates and deliberately unresolved conflicts
are never replaced. The method `reviewed_cpu_release_year_proxy` is shown in the
export and HTML details; the static axis and caption now say model/CPU year.

Limitations remain explicit: generic Intel-compatible 486 naming does not prove
its manufacturer; 72 MHz DX2 is a family-era proxy, not proof of a released SKU;
unspecified Opteron and Athlon steppings use the earliest named model's release.
Source labels calling Nocona/Woodcrest "Pentium" are retained, with their Xeon
interpretation disclosed. Ambiguous 386/40, generic Xeon without a sufficient
variant and unclear CPU identities remain undated in this pass.

[Change CSV](data/historical/year-cpu-changes.csv) and
[audit](data/historical/year-cpu-audit.json) record the baseline comparison.
