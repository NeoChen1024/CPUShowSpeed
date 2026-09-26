# Annual VAXen view of dated SPEC integer-speed evidence
> Archived speed-era research, retained for its source-checked observations.
> Its fitting and plotting commands are retired; it is excluded from the active rate analysis.
> Present-tense descriptions below refer to the original 2026-09-26 research snapshot.

Originally calculated on 2026-09-26 with the retired `cpushowspeed plot annual-vaxen` from the
locally cached Netlib CPU92 reports, official CPU95–CPU2026 bulk exports, the
source-checked [SPEC89 hardware-year catalog](spec89-hardware-years.md), and
the RAM-relaxed factor chain (retired output). This is an
**exploratory research figure**, not a validated universal conversion or a
claim that every listed score was attainable with the software of its
hardware year.

The generated peak figure (retired output)
and base figure (retired output)
have SVG versions beside the PNGs. The ignored, machine-readable
plotted records (retired output),
annual statistics (retired output),
exclusions (retired output),
and input/output hash summary (retired output)
are the audit trail. Records retain source URLs and checksums, reported scores,
benchmark generation, metric/mode, original date precision, date event type,
central normalized VAXen estimate, and the scope of each low/high range.

## Population and chronology

The peak chart has 18,479 eligible dated CPU92–CPU2026 score submissions
plus 47 dated SPEC89 integer-score **source observations**; the base chart
has 21,566 eligible CPU92–CPU2026 score submissions. The source-record CSV
retains 21,856 distinct dated CPU92+ result URLs, including one with a
source-checked hardware-date contradiction that is excluded from annual
statistics. Thus 21,855 distinct CPU92+ result URLs remain eligible. Base includes only the 13
previously reviewed CPU92 base scores; peak includes all 302 eligible CPU92
scores. Later speed-suite scores enter their own mode when positive. Rate,
FP, CoreMark, manual KIPS reconstructions, and machines without a checked
integer-speed score are outside this figure. Forty-seven of the 421 combined
SPEC89 observations have both a source-checked model year and a `SPECint89`
score; 374 other SPEC89 rows and three CPU92 pages without an integer score
are listed in the exclusion audit. Another 291 official CPU2000–CPU2017
CINT rows report no positive peak or base score and are also excluded. One additional [prelaunch hardware-date contradiction](spec2017-8280-speed-rate.md#hardware-date-contradiction-found-during-the-leader-audit)
is retained as a flagged source result but excluded from annual statistics.
The exclusion CSV thus has 669 source-linked rows in total.

For CPU92 and later, the year is the **reported hardware availability of the
tested configuration**, preserved from a month-precision disclosure. One
box per year contains all eligible submitted-result scores, with repeated
submissions retained; the line joins the highest submission in each year.
The lower panel shows submission count, exposing uneven archive coverage.
The annual CSV also records medians, quartiles, extrema, distinct system
labels, top system, and its result URL for every year from 1977 through 2026.

SPEC89 disclosures lack the same configuration-availability field. Their
source-checked **model, announcement, or processor introduction dates** use
different event types and therefore appear as separate peak-chart points,
never inside the CPU92+ annual boxes or maximum line. The three recovered
VAX-11/780 `SPECint89 = 1` reference observations are retained in the record
CSV and shown as one `1977, 1 VAX` reference marker. Native SPEC89 results,
worksheet derivatives, and development results have different marker classes.
The 15 distinct directly paired integer-score vectors give a geometric mean
`SPECint92 / SPECint89` of **0.9603866300**, with observed ratios
**0.8926553672–1.0561403509**. Non-reference SPEC89 points use the center;
the endpoints are stored as an observed-ratio sensitivity range, not a
confidence interval. They are not pooled into the later workload's boxes.

## Interpretation of normalized scores

Peak and base are separate charts, each using only its mode's
`alias_core_thread_clues` factor chain, anchored at `SPECint92 = 1 VAXen per
reported CPU92 score point`. CPU92 itself is a direct VAX-relative score;
CPU95–CPU2026 VAXen values are **normalized estimates**. The current
CPU2026 scale and its usage limits are in the
provisional CPU2026 factor table (retired output).
For every later-generation record, the `vaxen_low` and `vaxen_high` fields
hold only the adjacent edge's 95% configuration-bootstrap endpoints while
keeping all earlier chain factors fixed. The light band around annual maxima
uses these conditional last-edge endpoints. It is **not** a full-chain 95%
interval: upstream factor variation, source matching, workload differences,
and cross-edge dependence remain unquantified. The SPEC89 endpoints have a
different, explicitly labeled observed-range meaning.

The highest peak estimate among this cached cohort is approximately
**136,328 VAXen** in hardware year 2025; the highest base estimate is
approximately **109,182 VAXen**, also in 2025. The 2026-year boxes have only
81 peak and 95 base submissions, versus 883 and 1,021 respectively for
2025; a lower 2026 maximum is a coverage effect to investigate, not evidence
of performance regression. A CPU2026 result on hardware whose configuration
was available in an earlier year appears in that earlier bin. Such a point
can reflect later compiler, OS, and benchmark work, so the curve describes
**submitted systems grouped by hardware date**, not performance historically
measurable in that year.

The earliest displayed point is the 1977 VAX reference. No 1950s–1960s
machine has yet entered this integer-speed dataset with both a source-checked
date and a comparable score. Historical manual timing/KIPS extraction remains
separate research work.

## Labeling the top machine in each year

A full system name beside each point of the 36-year boxplot would cover the
data. The command therefore also creates companion
peak (retired output)
and base (retired output)
leader figures, with SVG versions for zooming. Each row names the year, a shortened **system model**, and a separately
labeled **CPU name**, then marks its annual highest VAXen estimate and draws
its applicable conditional range. Six historical SPEC89 leader sources do not
state a separate CPU field; their chart labels say so rather than inferring
one from the system name. The leader CSV (retired output)
retains the complete original system and processor labels, source URL and
locator, reported metric/score, hardware date and event type, VAXen estimate,
and uncertainty scope. It has 36 configuration-availability leaders per mode; the
peak figure adds six separate SPEC89 model-year leaders. The VAX reference is
the 1977 historical row. A shortened display label is never used as the
record identity. The PNG preview cannot contain per-point links; the
peak SVG (retired output),
base SVG (retired output),
and standalone peak HTML (retired output)
/ base HTML (retired output)
link plotted labels and points to their source result. The HTML also lists
full names, CPU fields, source locators, and direct source links below the
figure.

The maximum line in the distribution figure and the corresponding row in
the leader figure resolve to the **same source result URL** for each mode and
year. When submissions tie numerically, the annual statistic records the tie
count and all tied processor names. One source URL is selected
deterministically for the plotted representative; the label marks how many
other submissions share its maximum. The CSV preserves the choice. Thus “the machine of a year” here means the highest included
submission for that year, not every machine in the yearly box or the first
machine launched that year.
