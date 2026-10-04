import math
import unittest

import numpy as np
from cpushowspeed.classical.power_law import deming_slope, fit, pooled_within


class PowerLawTests(unittest.TestCase):
    def setUp(self):
        self.x = np.log(np.array([1.0, 2.0, 4.0, 8.0, 16.0]))
        self.y = 0.7 + 0.9 * self.x
        self.w = np.ones(5)
        self.t = np.zeros(5)

    def test_exact_power_law_is_recovered_by_every_free_slope(self):
        for method in ("free_ols", "free_deming", "free_ols_year"):
            a, b, _ = fit(method, self.x, self.y, self.w, self.t, None, 1.0)
            self.assertAlmostEqual(b, 0.9, places=10, msg=method)
            self.assertAlmostEqual(a, 0.7, places=10, msg=method)

    def test_anchored_fit_passes_through_the_anchor(self):
        a, b, _ = fit("anchored_ols", self.x, self.y, self.w, self.t, -1.0, 1.0)
        self.assertAlmostEqual(a + b * -1.0, 0.0)

    def test_proportional_fit_keeps_unit_exponent(self):
        a, b, _ = fit("proportional", self.x, self.y, self.w, self.t, None, 1.0)
        self.assertEqual(b, 1.0)
        self.assertAlmostEqual(a, np.mean(self.y - self.x))

    def test_deming_limits(self):
        sxx, syy, sxy = 4.0, 3.0, 2.0
        # Error only in y gives OLS of y on x; error only in x gives inverse regression.
        self.assertAlmostEqual(deming_slope(sxx, syy, sxy, 1e9), sxy / sxx, places=6)
        self.assertAlmostEqual(deming_slope(sxx, syy, sxy, 1e-9), syy / sxy, places=6)

    def test_year_term_absorbs_a_drift(self):
        t = np.array([-5.0, -2.0, 0.0, 3.0, 6.0])
        y = 0.2 + self.x + 0.03 * t
        a, b, c = fit("proportional_year", self.x, y, self.w, t, None, 1.0)
        self.assertAlmostEqual(c, 0.03)
        self.assertAlmostEqual(a, 0.2)

    def test_pooled_within_variance(self):
        variance, df = pooled_within({"a": [1.0, 3.0], "b": [5.0], "c": [2.0, 2.0, 5.0]})
        self.assertEqual(df, 3)
        self.assertTrue(math.isclose(variance, (2 + 6) / 3))


if __name__ == "__main__":
    unittest.main()
