"""Usenet shell archives, uuencoding, boxed reports and Dhrystone row rules."""

import binascii
import unittest

from cpushowspeed.classical.usenet_results import _dhrystone_record, _report_boxes, iso_date, shar_files, uudecode


class UsenetResultsTests(unittest.TestCase):
    def test_shar_members_strip_x_prefix_and_keep_cat_heredocs(self):
        text = "sed 's/^X//' << 'SHAR_EOF' > 'a.txt'\nXone\nXtwo\nSHAR_EOF\n" "cat << \\SHAR_EOF > 'b.db'\nMANUF\tREG\nSHAR_EOF\n"
        self.assertEqual(shar_files(text), {"a.txt": "one\ntwo", "b.db": "MANUF\tREG"})

    def test_uudecode_matches_binascii_including_short_last_line(self):
        data = b"Dhrystone 2.1 results, 1989" * 3
        lines = [binascii.b2a_uu(data[i : i + 45]).decode().rstrip("\n") for i in range(0, len(data), 45)]
        body = "begin 644 x\n" + "\n".join(lines) + "\n`\nend\n"
        self.assertEqual(uudecode(body), data.decode())

    def test_boxed_report_joins_wrapped_cells_and_skips_repeated_headers(self):
        header = "|manuf |reg |date    |"
        printed = "\n".join(
            [header, "|------|----|--------|", "|DEC   | 568|23-     |", "|      |    |March-  |", "|______|____|________|"]
            + [header, "|Sun   |7146|03/09/88|", "|______|____|________|"]
        )
        boxes = _report_boxes(printed)
        self.assertEqual([b["DATE"] for b in boxes], ["23-March-", "03/09/88"])
        self.assertEqual(boxes[1]["MANUF"], "Sun")

    def test_dates_are_us_month_first(self):
        self.assertEqual(iso_date("3/4/88"), "1988-03-04")
        self.assertEqual(iso_date("23-March-1989"), "1989-03-23")
        self.assertIsNone(iso_date(""))

    def test_register_value_preferred_and_pascal_excluded(self):
        row = dict(MANUF="Sun", MODEL="3/260", PROC="68020", CLOCK="0.00", NOREG="6000", REG="-1", COMPILER="cc")
        r = _dhrystone_record("src:x", "row1", "1.1", row, "row 1")
        self.assertEqual(
            (r["dhrystones_per_second"], r["variant"], r["clock_mhz"], r["excluded"]), (6000, "no register", None, None)
        )
        r = _dhrystone_record("src:x", "row2", "2", dict(row, REG="7000", COMPILER="Sun Pascal"), "row 2")
        self.assertEqual(r["dhrystones_per_second"], 7000)
        self.assertEqual(r["excluded"], "not the C program (Sun Pascal)")


if __name__ == "__main__":
    unittest.main()
