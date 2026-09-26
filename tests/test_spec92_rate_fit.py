"""Checks for the direct CPU92/CPU95 integer-rate bridge."""

import math
import unittest

from cpushowspeed.spec92_rate_fit import (
    VAX_RATE92_REFERENCE,
    _heldout_p95,
    _software_near,
)


class Cpu92RateFitTests(unittest.TestCase):
    def test_vax_throughput_reference(self):
        self.assertAlmostEqual(VAX_RATE92_REFERENCE, 23.71764705882353)
        self.assertAlmostEqual(1 / VAX_RATE92_REFERENCE, 25500 / 604800)

    def test_os_tier_is_not_hardware_tier(self):
        self.assertTrue(_software_near({"old_os": "UnixWare 2.0", "new_os": "UnixWare 2.0, SDK"}))
        self.assertTrue(_software_near({"old_os": "HP-UX B.10.01", "new_os": "HP-UX B.10.01"}))
        self.assertFalse(_software_near({"old_os": "HP-UX B.10.01", "new_os": "HP-UX B.10.20"}))

    def test_repeated_submission_does_not_add_independent_config(self):
        def pair(system, cpu, ratio):
            return {"system_key": system, "processor_key": cpu, "chips": 1, "old_clock_mhz": 100, "peak_ratio": ratio}

        pairs = [pair("a", "cpu-a", 100), pair("a", "cpu-a", 100), pair("b", "cpu-b", 110), pair("c", "cpu-c", 120)]
        expected = sorted(
            [math.expm1(abs(math.log(v) - (sum(map(math.log, (100, 110, 120))) - math.log(v)) / 2)) for v in (100, 110, 120)]
        )
        percentile = expected[1] + 0.9 * (expected[2] - expected[1])
        self.assertAlmostEqual(_heldout_p95(pairs, "peak"), percentile)


if __name__ == "__main__":
    unittest.main()
