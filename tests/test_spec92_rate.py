"""Netlib CINT92 speed and rate disclosures share one page parser; both layouts validate."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cpushowspeed.spec.cpu92_disclosure import FIELDS, parse
from cpushowspeed.spec.cpu92_rate import BENCHMARKS, _detail
from cpushowspeed.spec.source_fields import parse_speed92

VALUES = {
    "CPU": "50 MHz Example RISC",
    "Number of CPUs": "2 (out of 4)",
    "Memory": "64MB",
    "O/S & Version": "OS 1",
    "Compilers & Version": "C 1.0",
    "Hardware Availability": "Jul-93",
    "Software Availability": "######",
    "Tested": "Aug-93",
}


def page(metric, means, rows, *, old=False, compiler_continuation=""):
    """A page in the fixed Netlib PDS layout; old pages state the mean in the STRONG heading."""
    lines = [
        "<H1>SPEC Benchmark CINT92 Summary</H1>",
        f"<H2>{metric} (Volume 5, Issue 3, September 1993)</H2>",
        "<DT><H3>Vendor</H3><P>",
        "<DT><H3>System 50</H3><P>",
        "<DT><STRONG>Results:</STRONG>",
        "<PRE>",
        "   Benchmark name ...",
        *rows,
        "</PRE>",
    ]
    if old:
        name, value = next(iter(means.items()))
        lines.append(f"<DT><STRONG>Geometric Mean ({name}):  {value}</STRONG><P>")
    else:
        lines += ["<DT><STRONG>Geometric Mean:</STRONG>", *(f"<DD>{k}:  {v}" for k, v in means.items())]
    for field in FIELDS:
        tag = "<DT>" if field in ("Hardware Availability", "Software Availability", "License #", "Tested", "By", "Of") else "<DD>"
        lines.append(f"{tag}{field}:   {VALUES.get(field, 'None')}")
        if field == "Compilers & Version":
            lines.append(f"<DD>                {compiler_continuation}")
    lines += [f"<DT><STRONG>{metric} Tuning Parameters/Notes/Summary Of Changes:</STRONG>", "<DD>All: -O", "<DD>"]
    return "\n".join(lines)


class Spec92DisclosureTests(unittest.TestCase):
    def test_every_field_and_date_is_kept(self):
        rows = [f"   {name}   10.0   100.0" for name in BENCHMARKS]
        record = parse(page("SPECint92", {"SPECint92": "100.0"}, rows, compiler_continuation="Fortran 2.0"))
        self.assertEqual(record["publication_month"], "1993-09")
        self.assertEqual(record["hardware_availability_month"], "1993-07")
        self.assertEqual(record["test_month"], "1993-08")
        self.assertIsNone(record["software_availability_month"])
        self.assertEqual(record["fields"]["Software Availability"], "######")
        self.assertEqual(record["fields"]["Compilers & Version"], "C 1.0; Fortran 2.0")
        self.assertEqual((record["company"], record["system"]), ("Vendor", "System 50"))
        self.assertEqual(record["notes"], [dict(heading="SPECint92 Tuning Parameters/Notes/Summary Of Changes", lines=["All: -O"])])
        self.assertEqual(len(record["table"]), 6)

    def test_missing_field_is_structural_error(self):
        text = page("SPECint92", {"SPECint92": "1"}, []).replace("<DD>FPU:", "<DD>Floating:")
        with self.assertRaisesRegex(ValueError, "missing fields: FPU"):
            parse(text)


class Spec92SpeedTests(unittest.TestCase):
    def test_speed_result_keeps_dates_and_fields(self):
        rows = [f"   {name}   10.0   12.0   100.0   80.0" for name in BENCHMARKS]
        result = parse_speed92(page("SPECint92", {"SPECint92": "100.0", "SPECbase_int92": "80.0"}, rows), "u/x.html", "d")
        self.assertEqual((result.peak, result.base, result.chips, result.clock_mhz), (100.0, 80.0, 2, 50.0))
        self.assertEqual(result.raw_fields["hardware_availability_month"], "1993-07")
        self.assertEqual(result.raw_fields["publication_month"], "1993-09")
        self.assertEqual(result.raw_fields["company"], "Vendor")
        self.assertEqual(result.raw_fields["Number of CPUs"], "2 (out of 4)")

    def test_old_layout_and_mean_check(self):
        rows = [f"   {name}   1000   10.0   100.0" for name in BENCHMARKS]
        result = parse_speed92(page("SPECint92", {"SPECint92": "100.0"}, rows, old=True), "u/x.html", "d")
        self.assertEqual((result.peak, result.base), (100.0, None))
        with self.assertRaisesRegex(ValueError, "disagrees"):
            parse_speed92(page("SPECint92", {"SPECint92": "90.0"}, rows, old=True), "u/x.html", "d")
        with self.assertRaisesRegex(ValueError, "not an integer speed"):
            parse_speed92(page("SPECrate_int92", {"SPECrate_int92": "100"}, rows), "u/x.html", "d")


class Spec92RateTests(unittest.TestCase):
    def test_old_and_new_detail_layouts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary_url = "https://www.netlib.org/performance/html/spec.crint92.9_93.col0.html"
            summary = root / "summary.html"

            def publish(detail_name):
                summary.write_text(f'<A HREF="{detail_name}">Example</A> 100\n')
                (root / "summary.html.meta.json").write_text(
                    json.dumps({"source_url": summary_url, "sha256": hashlib.sha256(summary.read_bytes()).hexdigest()})
                )
                return "https://www.netlib.org/performance/html/" + detail_name

            url = publish("spec.example.crint.9_93.notes.html")
            rows = [f" {name} 2 10 100" for name in BENCHMARKS]
            record, subtests = _detail(
                page("SPECrate_int92", {"SPECrate_int92": "100"}, rows, old=True),
                url,
                "source-digest",
                {"SPECrate_int92": (summary_url, summary)},
            )
            self.assertEqual(record["peak_score"], 100)
            self.assertEqual(record["peak_copies_min"], 2)
            self.assertEqual(record["cpu_count"], 2)
            self.assertEqual(len(subtests), 6)
            self.assertEqual(record["hardware_availability_month"], "1993-07")
            self.assertEqual(record["software_availability_month"], "")
            new_url = publish("spec.example.crint92.9_93.notes.html")
            new_rows = [f" {name} 3 10 2 10 100 100" for name in BENCHMARKS]
            means = {"SPECrate_int92": "100", "SPECrate_base_int92": "100"}
            record, subtests = _detail(
                page("SPECrate_int92", means, new_rows), new_url, "source-digest", {"SPECrate_int92": (summary_url, summary)}
            )
            self.assertEqual(record["base_score"], 100)
            self.assertEqual(record["peak_copies_min"], 3)
            self.assertEqual(record["base_copies_min"], 2)
            self.assertEqual(len(subtests), 6)
            with self.assertRaisesRegex(ValueError, "detail and issue summary disagree"):
                _detail(
                    page("SPECrate_int92", {"SPECrate_int92": "101"}, [f" {name} 2 10 101" for name in BENCHMARKS]),
                    new_url,
                    "source-digest",
                    {"SPECrate_int92": (summary_url, summary)},
                )


if __name__ == "__main__":
    unittest.main()
