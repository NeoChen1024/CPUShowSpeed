"""Rate composites and the two-edge SPEC89 bridge on known solutions."""

import json
import math
import unittest

from classical_fixture import result
from cpushowspeed.calibration import ANCHOR
from cpushowspeed.calibration_edges import bridge_log, coefficient, joint_bootstrap
from cpushowspeed.classical_fit import RATE_TARGETS, composite_rows, evaluate, rate_calculate

D, W, L = "Dhrystone:v1.1_DMIPS", "Whetstone:MWIPS_DP", "LINPACK:n100_MFLOPS"


def systems():
    rows = []
    for key, scale in [("a", 1), ("b", 2), ("c", 4)]:
        values = {D: 4 * scale, W: 4 * scale, L: 4 * scale}
        rows.append(
            result(
                key,
                "sys:" + key,
                dict(values, SPECrate_int92=8 * scale / ANCHOR, SPECrate_base_int92=4 * scale / ANCHOR),
                clock=2,
                scope="reviewed-vector:dec",
            )
        )
        rows.append(result(key + "-conflict", "sys:" + key, {D: 1000}, clock=1))  # must not enter
    return rows


def rate_rows():
    rows = composite_rows(systems(), RATE_TARGETS)
    for r in rows:
        r["y_vaxen"] = r.pop("y")
    return rows


class RateCompositeTests(unittest.TestCase):
    def test_patterns_cohorts_and_excluded_clock_conflict(self):
        rows = rate_rows()
        # 3 systems x 2 targets x 2 cohorts x (3 pairs + 1 triple)
        self.assertEqual(len(rows), 48)
        self.assertEqual(sum(len(json.loads(r["member_ids"])) == 3 for r in rows), 12)
        self.assertTrue(all("conflict" not in json.dumps(r["member_ids"]) for r in rows))
        for r in rows:
            expected = 1 if r["target"] == "SPECrate_base_int92" else 2
            self.assertAlmostEqual(r["y_vaxen"] / r["x"], expected)

    def test_known_rate_factor_and_shared_baselines(self):
        summaries, predictions = rate_calculate(rate_rows(), 100, 20260927)
        for r in summaries:
            expected = 1 if r["target"] == "SPECrate_base_int92" else 2
            self.assertAlmostEqual(r["factor"], expected)
            self.assertAlmostEqual(r["factor_ci95_low"], expected)
            self.assertLess(r["loo_model_p95_percent"], 1e-10)
        self.assertTrue(all(abs(r["signed_error_percent"]) < 1e-10 for r in predictions))
        groups = {}
        for r in predictions:
            groups.setdefault((r["cohort"], r["target"], r["pattern"], r["predictor"]), []).append(r["spec_id"])
        for (cohort, target, pattern, _), ids in groups.items():
            self.assertEqual(sorted(ids), sorted(groups[cohort, target, pattern, "equal_weight"]))


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
        self.assertAlmostEqual(math.exp(bridge_log(edges)), 6)
        result_, predictions = evaluate(self.rows(), edges, 100, 3)
        for name in ("factor", "factor_ci95_low", "factor_ci95_high"):
            self.assertAlmostEqual(result_[name], 6)
        self.assertLess(result_["observed_rate_target_p95_percent"], 1e-10)
        self.assertLess(result_["estimated_89_target_p95_percent"], 1e-10)
        self.assertEqual({r["target_kind"] for r in predictions}, {"observed_rate_target", "estimated_89_target"})

    def test_holdout_removed_from_both_edges_and_composite_training(self):
        edges, rows = self.edges(), self.rows()
        baseline = coefficient(rows, edges, exclude="a")
        for edge in edges.values():
            edge["a"] = 100
        for r in rows:
            if r["model_key"] == "a":
                r["z"] = 100
        self.assertEqual(coefficient(rows, edges, exclude="a"), baseline)

    def test_shared_bridge_model_resampling_preserves_edge_correlation(self):
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


if __name__ == "__main__":
    unittest.main()
