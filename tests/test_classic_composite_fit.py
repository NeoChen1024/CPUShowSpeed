import math
import unittest

from cpushowspeed.classic_composite_fit import compare, inputs


class CompositeFitTests(unittest.TestCase):
    def vectors(self):
        return [
            dict(
                target="SPECrate_int92",
                whetstone="MWIPS",
                model_key=k,
                spec_id=k,
                dhrystone_id=k + "d",
                whetstone_id=k + "w",
                linpack_id=k + "l",
                dhrystone=8,
                whetstone_score=27,
                linpack=1,
                spec_score=y,
                dhrystone_adjusted=16,
                whetstone_adjusted=54,
                candidate_known_clocks=True,
                candidate_unknown_clock_allowed=True,
                candidate_linear_clock_scaling=True,
            )
            for k, y in [("a", 100), ("b", 200), ("c", 400)]
        ]

    def test_geometric_mean_and_scaling(self):
        v = self.vectors()[0]
        self.assertAlmostEqual(inputs(v, "candidate_known_clocks")["equal_weight"], 6)
        self.assertAlmostEqual(inputs(v, "candidate_linear_clock_scaling")["equal_weight"], 6 * 4 ** (1 / 3))

    def test_identical_folds_and_no_heldout_leakage(self):
        vectors = self.vectors()
        _, folds, _ = compare(vectors, 100, 7)
        v2 = self.vectors()
        v2[0]["spec_score"] = 99999
        _, changed, _ = compare(v2, 100, 7)
        for old, new in zip(folds, changed):
            if old["heldout_model"] == "a":
                self.assertEqual(old["factor"], new["factor"])
        signatures = {}
        for f in folds:
            signatures.setdefault(f["predictor"], []).append(
                (f["scenario"], f["heldout_model"], f["training_models"], f["heldout_tuples"])
            )
        self.assertTrue(all(v == signatures["equal_weight"] for v in signatures.values()))
        f = next(f for f in folds if f["heldout_model"] == "a" and f["predictor"] == "equal_weight")
        self.assertAlmostEqual(f["absolute_center_error_percent"], 100 * (math.sqrt(200 * 400) / 100 - 1))
