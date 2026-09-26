"""Yearly quantiles must share calibration draws, including winner changes."""

import unittest

import numpy as np
from cpushowspeed.annual_rate_ci import year_draws


class AnnualRateCITests(unittest.TestCase):
    def test_one_generation_moves_together_and_duplicates_remain(self):
        rows = [{"generation": "a", "reported_score": score} for score in (1, 1, 5)]
        leader = {"generation": "a", "reported_score": 5}
        result = year_draws(rows, leader, np.asarray([[2.0], [3.0]]), ["a"])
        np.testing.assert_allclose(result["median"], [2, 3])
        np.testing.assert_allclose(result["q3"], [6, 9])
        np.testing.assert_allclose(result["fixed_leader"], [10, 15])
        np.testing.assert_array_equal(result["frontier"], result["fixed_leader"])

    def test_cross_generation_winner_can_change(self):
        rows = [{"generation": "a", "reported_score": 1}, {"generation": "b", "reported_score": 2}]
        result = year_draws(rows, rows[1], np.asarray([[1.0, 1.0], [3.0, 1.0]]), ["a", "b"])
        np.testing.assert_allclose(result["frontier"], [2, 3])
        np.testing.assert_allclose(result["fixed_leader"], [2, 2])
        np.testing.assert_allclose(result["median"], [1.5, 2.5])
        np.testing.assert_allclose(result["q1"], [1.25, 2.25])


if __name__ == "__main__":
    unittest.main()
