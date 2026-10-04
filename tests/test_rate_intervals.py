"""Check percentile intervals against an exactly enumerable small bootstrap."""

import math
import unittest

from cpushowspeed.spec.result_pairing import ratio_statistics


class RateIntervalTests(unittest.TestCase):
    def test_three_configuration_exact_bootstrap_and_input_order(self):
        rows = [
            {
                "system_key": str(i),
                "processor_key": str(i),
                "chips": 1,
                "old_clock_mhz": 100,
                "match_tier": "hardware_near",
                "base_ratio": ratio,
                "old_base": ratio * 10,
                "new_base": 10,
            }
            for i, ratio in enumerate((1, 2, 4))
        ]
        result = ratio_statistics(rows, "base")
        self.assertAlmostEqual(result["factor_old_per_new"], 2)
        # In the exact 3^3 bootstrap, either extreme has mass 1/27 > 2.5%.
        self.assertAlmostEqual(result["cluster_bootstrap_95_low"], 1)
        self.assertAlmostEqual(result["cluster_bootstrap_95_high"], 4)
        self.assertAlmostEqual(result["heldout_p95_absolute_pct_error"], 0.1 * (1 - math.sqrt(2) / 4) + 0.9 * (math.sqrt(8) - 1))
        self.assertEqual(result["bootstrap_replicates"], 10000)
        repeated = ratio_statistics(list(reversed(rows)) + [rows[0]], "base")
        for field in ("factor_old_per_new", "cluster_bootstrap_95_low", "cluster_bootstrap_95_high"):
            self.assertEqual(result[field], repeated[field])


if __name__ == "__main__":
    unittest.main()
