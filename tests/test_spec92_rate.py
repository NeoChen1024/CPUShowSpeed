"""Both historical Netlib CINT92 rate layouts validate against issue summaries."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cpushowspeed.spec92_rate import BENCHMARKS, _detail


class Spec92RateTests(unittest.TestCase):
    def test_old_and_new_detail_layouts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            detail_name = "spec.example.crint.9_93.notes.html"
            url = "https://www.netlib.org/performance/html/" + detail_name
            summary_url = "https://www.netlib.org/performance/html/spec.crint92.9_93.col0.html"
            summary = root / "summary.html"
            summary.write_text(f'<A HREF="{detail_name}">Example</A> 100\n')
            (root / "summary.html.meta.json").write_text(
                json.dumps({"source_url": summary_url, "sha256": hashlib.sha256(summary.read_bytes()).hexdigest()})
            )
            common = (
                "<H2>SPECrate_int92 (Volume 5, Issue 3, September 1993)</H2>"
                "<H3>Vendor</H3><H3>System</H3><DD>CPU: 50 MHz Example\n"
                "Number of CPUs: 2<DD>O/S & Version: OS 1\n"
                "<DT>Tested : Aug-93<DT>Hardware Availability: Jul-93"
            )
            rows = "\n".join(f" {name} 2 10 100" for name in BENCHMARKS)
            record, subtests = _detail(
                common + "<DT><STRONG>Geometric Mean (SPECrate_int92): 100</STRONG>\n" + rows,
                url,
                "source-digest",
                {"SPECrate_int92": (summary_url, summary)},
            )
            self.assertEqual(record["peak_score"], 100)
            self.assertEqual(record["peak_copies_min"], 2)
            self.assertEqual(len(subtests), 6)
            self.assertEqual(record["hardware_availability_month"], "1993-07")
            new_name = "spec.example.crint92.9_93.notes.html"
            new_url = "https://www.netlib.org/performance/html/" + new_name
            summary.write_text(f'<A HREF="{new_name}">Example</A> 100\n')
            (root / "summary.html.meta.json").write_text(
                json.dumps({"source_url": summary_url, "sha256": hashlib.sha256(summary.read_bytes()).hexdigest()})
            )
            new_rows = "\n".join(f" {name} 3 10 2 10 100 100" for name in BENCHMARKS)
            record, subtests = _detail(
                common + "<DD>SPECrate_int92: 100<DD>SPECrate_base_int92: 100\n" + new_rows,
                new_url,
                "source-digest",
                {"SPECrate_int92": (summary_url, summary)},
            )
            self.assertEqual(record["base_score"], 100)
            self.assertEqual(record["peak_copies_min"], 3)
            self.assertEqual(record["base_copies_min"], 2)
            self.assertEqual(len(subtests), 6)
            with self.assertRaisesRegex(ValueError, "detail and issue summary disagree"):
                _detail(
                    common + "<DD>SPECrate_int92: 101\n" + rows,
                    new_url,
                    "source-digest",
                    {"SPECrate_int92": (summary_url, summary)},
                )


if __name__ == "__main__":
    unittest.main()
