import math
import unittest

from cpushowspeed.classic_89_rate import (
    bridge_log,
    coefficient,
    evaluate,
    joint_bootstrap,
)


class ChainedRateTests(unittest.TestCase):
    def edges(self):
        return {"first": {k: math.log(2) for k in ("a", "b", "c")}, "second": {k: math.log(3) for k in ("a", "b", "c")}}

    def rows(self):
        return [
            dict(
                model_key=k,
                generation=g,
                raw_target=1 if g == "89" else 6,
                x=1,
                z=0 if g == "89" else math.log(6),
                spec_id=k + g,
                member_ids="[]",
            )
            for k in ("a", "b", "c")
            for g in ("89", "92")
        ]

    def test_two_edge_product_and_joint_known_solution(self):
        edges = self.edges()
        rows = self.rows()
        self.assertAlmostEqual(math.exp(bridge_log(edges)), 6)
        result, predictions = evaluate(rows, edges, 100, 3)
        for name in ("factor", "factor_ci95_low", "factor_ci95_high"):
            self.assertAlmostEqual(result[name], 6)
        self.assertLess(result["observed_rate_target_p95_percent"], 1e-10)
        self.assertLess(result["estimated_89_target_p95_percent"], 1e-10)
        self.assertEqual({r["target_kind"] for r in predictions}, {"observed_rate_target", "estimated_89_target"})

    def test_holdout_removed_from_both_edges_and_composite_training(self):
        edges = self.edges()
        rows = self.rows()
        baseline = coefficient(rows, edges, exclude="a")
        for edge in edges.values():
            edge["a"] = 100
        for r in rows:
            if r["model_key"] == "a":
                r["z"] = 100
        self.assertEqual(coefficient(rows, edges, exclude="a"), baseline)

    def test_shared_bridge_model_resampling_preserves_edge_correlation(self):
        # The two edges cancel exactly for every shared-model resample.
        # Independent edge bootstraps would invent uncertainty here.
        edges = {"first": {"a": -1, "b": 1}, "second": {"a": 1, "b": -1}}
        _, draws = joint_bootstrap([], edges, 500, 1)
        self.assertTrue(all(abs(x - 1) < 1e-12 for x in draws))

    def test_estimated_target_repetition_does_not_shrink_common_bridge_uncertainty(self):
        rows = [r for r in self.rows() if r["generation"] == "89"]
        edges = {"one": {"p": -0.2, "q": 0.2}, "two": {"r": 0, "s": 0}}
        a, _ = joint_bootstrap(rows, edges, 500, 1)
        b, _ = joint_bootstrap(rows * 10, edges, 500, 1)
        self.assertEqual(a, b)
        self.assertGreater(max(a), min(a))
