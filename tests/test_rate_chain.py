"""Whole-chain propagation must preserve shared prefixes and reject shared edge clusters."""

import unittest

import numpy as np
from cpushowspeed.spec.cpu92_rate_fit import VAX_RATE92_REFERENCE
from cpushowspeed.spec.rate_chain import audit_overlap, bootstrap_log_means, configuration_logs, propagate


class RateChainTests(unittest.TestCase):
    def test_prefix_uncertainty_is_shared_and_reference_is_fixed(self):
        factors = np.asarray([[2, 3, 4, 5, 6], [4, 3, 4, 5, 6]], dtype=float)
        result = propagate(np.log(factors))
        np.testing.assert_allclose(result[0], np.asarray([1, 2, 6, 24, 120, 720]) / VAX_RATE92_REFERENCE)
        np.testing.assert_allclose(result[1, 1:] / result[0, 1:], 2)
        self.assertEqual(result[0, 0], result[1, 0])

    def test_independent_streams_and_repeatable_input_order(self):
        logs = {("a", 1, 100): 0.0, ("b", 1, 100): 1.0, ("c", 1, 100): 2.0}
        a = bootstrap_log_means(logs, "edge-a", 200)
        np.testing.assert_array_equal(a, bootstrap_log_means(dict(reversed(list(logs.items()))), "edge-a", 200))
        self.assertFalse(np.array_equal(a, bootstrap_log_means(logs, "edge-b", 200)))

    def test_duplicate_submissions_and_shared_sources(self):
        first = {
            "system_key": "s",
            "processor_key": "a",
            "chips": 1,
            "old_clock_mhz": 100,
            "base_ratio": 2,
            "old_source_url": "A",
            "new_source_url": "B",
        }
        second = {**first, "processor_key": "b", "old_source_url": "B", "new_source_url": "C"}
        self.assertEqual(configuration_logs([first], "base"), configuration_logs([first, first], "base"))
        audit = audit_overlap([[first], [second]])
        self.assertEqual(audit[0]["shared_submission_urls"], ["B"])
        self.assertEqual(audit[0]["shared_configurations"], [])


if __name__ == "__main__":
    unittest.main()
