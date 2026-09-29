"""Unit and interval boundaries for saved timeline estimates."""

import unittest

from cpushowspeed.timeline_estimates import value


class TimelineEstimateTests(unittest.TestCase):
    def test_whole_route_bounds_scale_with_input(self):
        f = dict(coefficient_vaxen="2", vaxen_ci95_low="1.5", vaxen_ci95_high="3")
        self.assertEqual(value(10, f), [20, 15, 30])
        self.assertEqual(value(10, dict(coefficient=5, ci95_low=4, ci95_high=6), True), [50, 40, 60])

    def test_invalid_interval_is_not_published(self):
        for low, high in [(0, 3), (4, 3), (1, float("inf"))]:
            with self.assertRaises(ValueError):
                value(10, dict(coefficient_vaxen=2, vaxen_ci95_low=low, vaxen_ci95_high=high))
