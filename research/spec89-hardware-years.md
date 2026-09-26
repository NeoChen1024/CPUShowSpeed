# SPEC89 hardware introduction-year audit

Reviewed on 2026-09-26. The immutable [curated SPEC89 aggregate](data/spec89/v2.0.0/csv/aggregate89.csv)
contains 381 source observations. The [combined aggregate](data/spec89/aggregate89-plus-helman.csv)
adds 40 Helman worksheet observations for 421 total and still has 160 distinct
`system_normalized` labels.
The [hardware introduction catalog](data/spec89/hardware-introductions.csv)
has exactly one row for every label. It currently provides a source-checked
year for 26 labels, covering 99 combined observations; the other 134 labels
and 322 observations remain undated. Blank years mean unresolved evidence, not zero or
an assumed 1989 benchmark year. Some normalized labels are combined machine
families or beta configurations and need splitting or stronger source matching.

The catalog records the source's date at its actual precision, the event it
dates, the original URL and locator, and the review date. An **introduction**,
**announcement**, **general availability**, or manufacturer's historical
**model year** is kept distinct. These are dates of named hardware, not dates
of SPEC89 tests. The original `aggregate89.csv` and its checksum manifest are
unchanged. The catalog is preserved as source-checked historical date evidence. The
former SPEC89 annual-speed join command was retired when the project adopted
a rate-only analysis; the archived scores do not enter the current fit.

## Checked source groups

- DIGITAL's [historical timeline](https://archive.computerhistory.org/resources/text/DEC/dec.digital_%28DEC%29_timeline_1957-1997.102630354/timelinetext.htm)
  dates the VAX-11/780 introduction to 1977-10, DECstation 3100 announcement to
  1989-01, and original DEC 3000 Model 400/500 Alpha systems to 1992-11.
  DIGITAL's [VAX family timeline](https://archive.computerhistory.org/resources/text/DEC/dec.digital_at_work.1992.102630350.pdf)
  supplies year-level evidence for several other VAX variants. The 1977
  VAX-11/780 introduction should not be read as the first customer delivery.
- IBM's [POWER1 history](https://www.redbooks.ibm.com/redbooks/pdfs/sg247071.pdf)
  explicitly dates the Model 220 announcement to 1992-01 and Model 580 to
  1993-09. IBM's product lifecycle pages give general availability for
  [Model 340](https://www.ibm.com/support/pages/node/7093897) and
  [Model 560](https://www.ibm.com/support/pages/node/7094379) as 1992-01-21.
  The Model 530 remains undated: the checked Redbook passage associates it
  with early POWER1 systems but does not explicitly date that model.
- Sun's [Numerical Computation Guide, Table B-1](https://docs.oracle.com/cd/E19957-01/802-5692/802-5692.pdf)
  associates specific SPARCstation models with years 1989–1991. These are
  recorded as manufacturer model years, not month-precision release dates.
- A [1990 contemporary NeXT advertisement](https://archive.computerhistory.org/resources/access/text/2024/05/102734476-05-0012-acc.pdf)
  presents the NeXTstation as already on sale. Intel's
  [processor release chronology](https://www.intel.com/pressroom/kits/quickrefyr.htm)
  supplies dates for the otherwise generic `i486` and `i486DX2` labels.
  These CPU dates do not establish the launch year of an unspecified complete
  benchmark system; the CSV marks them as processor dates.
- HP's [January/February 1989 *Measure* index](https://www.hp.com/hpinfo/abouthp/histnfacts/publications/measure/index.html)
  lists the HP 9000 Model 340 workstation among new products; the CSV keeps
  only year precision.

Before reusing a catalog date for a future machine-capacity study, resolve
exact model identity and distinguish model introduction from the availability
of a later benchmark configuration.
