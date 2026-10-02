import math
import tempfile
import unittest
from pathlib import Path

from cpushowspeed.calibration import absolute_error_percent, error_summary, fit
from cpushowspeed.research_io import read_csv, write_csv


class CalibrationPolicyTests(unittest.TestCase):
    def test_relative_error_is_not_symmetric_factor_error(self):
        self.assertAlmostEqual(absolute_error_percent(math.log(0.5)), 50)
        self.assertAlmostEqual(absolute_error_percent(math.log(2)), 100)

    def test_model_center_and_observation_summaries_share_equal_model_weight(self):
        rows = [dict(model_key="a", log_error=math.log(0.5))] * 20 + [dict(model_key="b", log_error=math.log(2))]
        result = error_summary(rows)
        self.assertAlmostEqual(result["model_center_p95_percent"], 97.5)
        self.assertEqual(result["model_balanced_observation_p95_percent"], 100)
        self.assertEqual(result, error_summary(rows[:20] * 3 + rows[20:]))

    def test_csv_policies_keep_bom_and_newlines_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.csv"
            write_csv(path, [dict(a=1), dict(a=2, b=3)])
            self.assertEqual(path.read_bytes(), b"a,b\r\n1,\r\n2,3\r\n")
            path.write_bytes(b"\xef\xbb\xbfa\n1\n")
            self.assertEqual(read_csv(path, encoding="utf-8-sig"), [{"a": "1"}])
            write_csv(path, [], empty_text="")
            self.assertEqual(path.read_bytes(), b"")
