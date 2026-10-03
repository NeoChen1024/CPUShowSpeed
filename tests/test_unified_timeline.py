"""Timeline dates keep their source precision."""

import unittest

from cpushowspeed.unified_timeline import _month


class MonthTests(unittest.TestCase):
    def test_month_keeps_source_precision(self):
        self.assertEqual(_month("Aug-2019"), "2019-08")
        self.assertEqual(_month("2019-08"), "2019-08")
        self.assertEqual(_month(""), "")
        with self.assertRaises(ValueError):
            _month("2019")


if __name__ == "__main__":
    unittest.main()
