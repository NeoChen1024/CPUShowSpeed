"""Independent source examples and conservative identity rules for discovery."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import blake3
from cpushowspeed.classic_overlap import (
    full_name,
    model_key,
    parse_dhrystone,
    parse_linpack_pdf,
    parse_whetstone,
    relaxed_key,
)


def source(text, index):
    return {
        "source": {"source_id": "fixture", "url": "https://example.org/", "blake3": "hash", "lineage": "fixture"},
        "blocks": [{"kind": "preformatted", "pre_index": index, "text": text}],
    }


class OverlapTests(unittest.TestCase):
    def test_dhrystone_decimal_clock_and_flagged_score(self):
        text = "306 Amiga 1000             AmigaDOS     68000         7.16   0.54 -----   1\n040 DEC 3000/500  AXP      OSF/1 T1.3-3 DEC 21064   150.0  211.0  137.1* 25"
        rows, rejected = parse_dhrystone(source(text, 0))
        self.assertFalse(rejected)
        self.assertEqual(rows[0]["clock_mhz"], 7.16)
        self.assertEqual(rows[0]["metrics_raw"]["v1.1_DMIPS"], "0.54")
        self.assertEqual(rows[1]["metrics_raw"]["v2.1_DMIPS"], "137.1*")
        self.assertEqual(rows[1]["os_raw"], "OSF/1 T1.3-3")

    def test_whetstone_supplier_and_pc_boundary(self):
        text = "Digital\nVAX 11/780 noF  P8             5     0.740                   0.253   For  Opt   145   1977 \nPCs (Precision P14) via the same optimised Watcom compiled C/C++ code\nPentium          100     66.2    16.8    97.8    66.2    1994 "
        rows, rejected = parse_whetstone(source(text, 2))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["system"], "DEC VAX 11/780 noF")
        self.assertEqual(rows[0]["metrics_raw"]["MWIPS"], "0.740")
        self.assertEqual(rows[0]["metrics_raw"]["MWIPS_DP"], "0.253")
        self.assertEqual(rows[0]["language_raw"], "For")
        self.assertEqual(rows[0]["introduction_year_raw"], "1977")

    def test_linpack_table_boundary_and_uninterpreted_scores(self):
        text = "Introduction mentions Table 1\fTable 1: Performance\nVAX 11/780 FPA  VMS v4.5  .14\nDEC 3000-500 Alpha AXP(150 MHz)  Fortran  30  107  150\fTable 2: Parallel\nDEC 3000-500  1  2  3"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "raw"
            p.write_bytes(b"%PDF-fixture")
            meta = {
                "source_id": "linpack",
                "url": "https://example.org",
                "lineage": "fixture",
                "blob_path": str(p),
                "blake3": blake3.blake3(p.read_bytes()).hexdigest(),
            }
            with patch("cpushowspeed.classic_overlap.subprocess.run", return_value=SimpleNamespace(stdout=text.encode())):
                rows, rejected = parse_linpack_pdf(meta)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["locator"], "pdf:page:2:line:2")
        self.assertEqual(rows[1]["system"], "DEC 3000-500 AXP")
        self.assertEqual(rows[1]["clock_mhz"], 150)
        self.assertEqual(rows[1]["metrics_raw"]["table1_uninterpreted_columns"], ["Fortran", "30", "107", "150"])

    def test_suffixes_are_not_merged(self):
        self.assertNotEqual(model_key("Sun SPARCstation 1"), model_key("Sun SPARCstation 1+"))
        self.assertNotEqual(model_key("DEC 3000/400"), model_key("DEC 3000/400S"))
        self.assertNotEqual(model_key("HP 9000/735/755"), model_key("HP 9000/735"))
        self.assertEqual(model_key(full_name("Digital Equipment Corporation", "DEC 3000 Model 900")), model_key("DEC 3000/900 AXP"))
        self.assertEqual(relaxed_key("SPARCstation 2 (40)", 40), model_key("Sun SPARCstation 2"))
        self.assertNotEqual(relaxed_key("SPARCstation 2 (40)", 80), model_key("Sun SPARCstation 2"))
        self.assertEqual(relaxed_key("HP 9000 Series 700 Model 735/99", 99), model_key("HP 9000/735"))


if __name__ == "__main__":
    unittest.main()
