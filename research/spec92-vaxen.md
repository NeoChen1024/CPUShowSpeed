# First SPEC92 VAXen figure

Recomputed on 2026-09-26 from the Netlib CPU92 files collected on 2026-09-25.
All 300 included detailed scores matched their independent issue summary
rows. The [collection and plot method](../docs/spec-collection.md)
reproduces these values. The score is SPECint92, a CINT92 speed metric relative
to the VAX-11/780 reference machine. These are published system scores, not
isolated CPU measurements or a bridge to another SPEC generation.

| Issue year | Eligible reports | Median VAXen | Maximum VAXen | System behind maximum | Summary source |
| --- | ---: | ---: | ---: | --- | --- |
| 1993 | 69 | 57.5 | 132.6 | DEC 7000 Model 610 | [1993-12 CINT92](https://www.netlib.org/performance/html/spec.cint92.12_93.col0.html) |
| 1994 | 111 | 84.3 | 200.6 | DEC 3000 Model 900 | [1994-12 CINT92](https://www.netlib.org/performance/html/spec.cint92.12_94.col0.html) |
| 1995 | 110 | 139.25 | 405.9 | AlphaServer 8000 5/350 | [1995-12 CINT92](https://www.netlib.org/performance/html/spec.cint92.12_95.col0.html) |
| 1996 | 10 | 258.4 | 432.8 | AlphaServer 8400 5/350 | [1996-04 CINT92](https://www.netlib.org/performance/html/spec.cint92.4_96.col0.html) |

Each maximum also appears in its [detailed disclosure](https://www.netlib.org/performance/html/spec.deoi761.cint92.12_93.notes.html),
[1994 disclosure](https://www.netlib.org/performance/html/spec.dec3900.cint92.12_94.notes.html),
[1995 disclosure](https://www.netlib.org/performance/html/spec.d8350i.cint92.12_95.notes.html),
and [1996 disclosure](https://www.netlib.org/performance/html/spec.I00295.cint92.4_96.notes.html).
The annual medians and report counts come from the 300 eligible source-linked
rows in the generated CSV; they are not values printed in a SPEC newsletter.

Five reports were excluded with per-source reasons in the generated audit CSV.
Two [1993-06 labeled](https://www.netlib.org/performance/html/spec.990b.cint92.6_93.notes.html)
[disclosures](https://www.netlib.org/performance/html/spec.ibmi990.cint92.6_93.notes.html)
claim testing in 1993-09, so their publication date is ambiguous. One of
these is the previously checked IBM POWERserver 970B `58.8` result; its score
transcription remains valid, but it is absent from the annual figure pending a
chronology check. The four two-CPU disclosures are now included as system-speed
results; this changed the annual submission distributions but not their maxima.
The 1996 box contains only ten qualifying reports and must not be read as a
complete market distribution.
