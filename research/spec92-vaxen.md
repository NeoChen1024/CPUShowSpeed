# First SPEC92 VAXen figure
> Archived speed-era research, retained for its source-checked observations.
> Its fitting and plotting commands are retired; it is excluded from the active rate analysis.
> Present-tense descriptions below refer to the original 2026-09-26 research snapshot.

Recomputed on 2026-09-26 from Netlib CPU92 files collected on 2026-09-25.
All 302 included detailed scores matched their independent issue summary rows.
The former speed plot command produced these values; that command is now retired. The score is SPECint92, a CINT92 speed metric relative to the
VAX-11/780 reference machine. Each result is assigned to the
**disclosure-reported hardware-configuration availability year**; the test and
SPEC Newsletter issue months remain separate fields in the generated CSV.

| Reported hardware availability year | Included reports | Median VAXen | Maximum VAXen | System behind maximum | Detailed source |
| --- | ---: | ---: | ---: | --- | --- |
| 1991 | 3 | 21.2 | 64.0 | HP 9000 Series 700 Model 720 | [disclosure](https://www.netlib.org/performance/html/spec.I00121.cint92.4_96.notes.html) |
| 1992 | 15 | 30.0 | 157.7 | HP 9000 Series 700 Model 735/125 | [disclosure](https://www.netlib.org/performance/html/spec.7351i.cint92.12_95.notes.html) |
| 1993 | 91 | 64.8 | 138.4 | DEC 3000 Model 800 | [disclosure](https://www.netlib.org/performance/html/spec.dec3-800.cint92.6_94.notes.html) |
| 1994 | 92 | 90.7 | 202.9 | AlphaServer 2100 4/275 | [disclosure](https://www.netlib.org/performance/html/spec.dec21475.cint92.6_95.notes.html) |
| 1995 | 81 | 140.7 | 365.2 | Digital EB164 | [disclosure](https://www.netlib.org/performance/html/spec.deb164i.cint92.12_95.notes.html) |
| 1996 | 20 | 297.8 | 432.8 | AlphaServer 8400 5/350 | [disclosure](https://www.netlib.org/performance/html/spec.I00295.cint92.4_96.notes.html) |

The annual statistics come from the 302 generated source-linked CSV rows, not
from a printed annual summary. Three detailed pages lack a SPECint92 score and
are listed in the exclusion CSV. Two [1993-06 labeled](https://www.netlib.org/performance/html/spec.990b.cint92.6_93.notes.html)
[disclosures](https://www.netlib.org/performance/html/spec.ibmi990.cint92.6_93.notes.html)
claim testing in 1993-09; both remain score observations and carry a
`test_after_issue_month` flag. Several later publications describe hardware
available much earlier; for example the 1991-year maximum was published in a
1996 issue. Its plotted value therefore reflects later software and tuning,
not necessarily performance achievable with 1991 software. The original 1992
issues are absent from this Netlib archive. These boxes describe the cached
submissions, not all machines available in those years.
