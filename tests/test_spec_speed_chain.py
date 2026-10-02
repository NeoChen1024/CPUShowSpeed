"""The speed chain is anchored at SPECint92 = 1 speed-VAXen and composes its saved edge factors."""

import csv
import math
import unittest

from cpushowspeed.spec_speed_chain import FACTORS, INTERVALS, convert_speed


class SpeedChainTests(unittest.TestCase):
    @unittest.skipUnless(INTERVALS.exists() and FACTORS.exists(), "saved speed chain required")
    def test_anchor_and_composition(self):
        self.assertEqual(convert_speed("cpu92", "peak", 7.0)["vaxen"], 7.0)
        factors = {(r["new_generation"], r["mode"]): float(r["factor_old_per_new"]) for r in csv.DictReader(FACTORS.open())}
        for mode in ("base", "peak"):
            scale = 1.0
            for generation in ("cpu95", "cpu2000", "cpu2006", "cpu2017", "cpu2026"):
                scale *= factors[generation, mode]
                converted = convert_speed(generation, mode, 2.0)
                self.assertTrue(math.isclose(converted["vaxen"], 2.0 * scale, rel_tol=1e-12))
                self.assertLessEqual(converted["ci95"]["low"], converted["vaxen"])
                self.assertLessEqual(converted["vaxen"], converted["ci95"]["high"])
        with self.assertRaises(ValueError):
            convert_speed("cpu89", "peak", 1.0)


if __name__ == "__main__":
    unittest.main()
