"""Speed composites and the SPEC89 bridge on known solutions."""

import json
import math
import unittest

import numpy as np
from classical_fixture import result
from cpushowspeed.classical.calibration_edges import bridge_log, coefficient, joint_bootstrap
from cpushowspeed.classical.composite_fit import SPEED_TARGETS, composite_calculate, composite_rows, evaluate, speed_edges

D, W, L = "Dhrystone:v1.1_DMIPS", "Whetstone:MWIPS_DP", "LINPACK:n100_MFLOPS"
# The 780 scores 1 in each metric, so speed-VAXen = composite ** exponent.
ANCHOR, ANCHOR_SD = {D: 0.0, W: 0.0, L: 0.0}, {D: 0.0, W: 0.0, L: 0.0}
EXPONENT = {"SPECbase_int92": 0.9, "SPECint92": 0.8}


def systems():
    rows = []
    for key, scale in [("a", 1), ("b", 2), ("c", 4)]:
        values = {D: 4 * scale, W: 4 * scale, L: 4 * scale}
        rows.append(
            result(
                key,
                "sys:" + key,
                dict(values, SPECint92=(4 * scale) ** 0.8, SPECbase_int92=(4 * scale) ** 0.9, SPECrate_int92=1000),
                clock=2,
                scope="reviewed-vector:dec",
            )
        )
        rows.append(result(key + "-conflict", "sys:" + key, {D: 1000}, clock=1))  # must not enter
    return rows


def speed_rows():
    rows = composite_rows(systems(), SPEED_TARGETS)
    for r in rows:
        r["y_vaxen"] = r.pop("y")
    return rows


class SpeedCompositeTests(unittest.TestCase):
    def test_patterns_cohorts_and_excluded_clock_conflict(self):
        rows = speed_rows()
        # 3 systems x 2 targets x 2 cohorts x (3 pairs + 1 triple)
        self.assertEqual(len(rows), 48)
        self.assertEqual(sum(len(json.loads(r["member_ids"])) == 3 for r in rows), 12)
        self.assertTrue(all("conflict" not in json.dumps(r["member_ids"]) for r in rows))
        for r in rows:
            self.assertAlmostEqual(r["y_vaxen"], r["x"] ** EXPONENT[r["target"]])

    def test_known_exponent_through_the_vax780_and_shared_baselines(self):
        summaries, predictions = composite_calculate(speed_rows(), ANCHOR, ANCHOR_SD, 100, 20260927)
        for r in summaries:
            expected = EXPONENT[r["target"]]
            self.assertAlmostEqual(r["exponent"], expected)
            self.assertAlmostEqual(r["exponent_ci95_low"], expected)
            self.assertAlmostEqual(r["exponent_ci95_high"], expected)
            self.assertAlmostEqual(r["vaxen_at_unit_score"], 1)
            self.assertLess(r["loo_model_p95_percent"], 1e-10)
        self.assertTrue(all(abs(r["signed_error_percent"]) < 1e-10 for r in predictions))
        groups = {}
        for r in predictions:
            groups.setdefault((r["cohort"], r["target"], r["pattern"], r["predictor"]), []).append(r["spec_id"])
        for (cohort, target, pattern, _), ids in groups.items():
            self.assertEqual(sorted(ids), sorted(groups[cohort, target, pattern, "equal_weight"]))


class BridgeTests(unittest.TestCase):
    def edges(self):
        return {"first": {k: math.log(2) for k in ("a", "b", "c")}, "second": {k: math.log(3) for k in ("a", "b", "c")}}

    def rows(self):
        # speed-VAXen = x ** 0.8 through the 780 (x = 1); SPECint89 targets are a sixth of it.
        return [
            dict(
                model_key=k,
                generation=g,
                lx=math.log(x),
                ly=0.8 * math.log(x) - (math.log(6) if g == "89" else 0),
                spec_id=k + g,
                member_ids="[]",
            )
            for k, x in (("a", 2), ("b", 5), ("c", 11))
            for g in ("89", "92")
        ]

    def test_two_edge_product_and_joint_known_solution(self):
        edges = self.edges()
        self.assertAlmostEqual(math.exp(bridge_log(edges)), 6)
        result_, predictions = evaluate(self.rows(), edges, 0.0, np.zeros(100), 100, 3)
        for name in ("exponent", "exponent_ci95_low", "exponent_ci95_high"):
            self.assertAlmostEqual(result_[name], 0.8)
        self.assertAlmostEqual(result_["bridge_factor"], 6)
        self.assertLess(result_["observed_speed_target_p95_percent"], 1e-10)
        self.assertLess(result_["estimated_89_target_p95_percent"], 1e-10)
        self.assertEqual({r["target_kind"] for r in predictions}, {"observed_speed_target", "estimated_89_target"})

    def test_spec89_row_dropped_where_specint92_is_reported(self):
        rows = [result("x", "sys:x", {D: 4, W: 4, "SPECint89": 5, "SPECint92": 6}, scope="historical-spec:spec89-bridge")]
        targets = {r["target"] for r in composite_rows(rows, ("SPECint89", "SPECint92"), cohorts=("same_system",))}
        self.assertEqual(targets, {"SPECint92"})

    def test_speed_bridge_uses_only_the_int89_edge(self):
        evidence = [
            dict(edge="int89_to_int92", model_key="a", log_ratio=math.log(2)),
            dict(edge="int92_to_rate92", model_key="a", log_ratio=math.log(5)),
        ]
        edges = speed_edges(evidence)
        self.assertEqual(list(edges), ["int89_to_int92"])
        self.assertAlmostEqual(math.exp(bridge_log(edges)), 2)
        with self.assertRaises(ValueError):
            speed_edges(evidence[1:])

    def test_holdout_removed_from_both_edges_and_composite_training(self):
        edges, rows = self.edges(), self.rows()
        baseline = coefficient(rows, edges, 0.0, exclude="a")
        for edge in edges.values():
            edge["a"] = 100
        for r in rows:
            if r["model_key"] == "a":
                r["ly"] = 100
        self.assertEqual(coefficient(rows, edges, 0.0, exclude="a"), baseline)

    def test_anchored_exponent_is_the_model_weighted_moment_ratio(self):
        rows = [dict(model_key=k, generation="92", lx=math.log(x), ly=y) for k, x, y in (("a", 3, 0.4), ("b", 9, 1.9))]
        c = math.log(0.7)
        beta, _ = coefficient(rows, {}, c)
        dx = [math.log(3) - c, math.log(9) - c]
        self.assertAlmostEqual(beta, (dx[0] * 0.4 + dx[1] * 1.9) / (dx[0] ** 2 + dx[1] ** 2))

    def test_shared_bridge_model_resampling_preserves_edge_correlation(self):
        edges = {"first": {"a": -1, "b": 1}, "second": {"a": 1, "b": -1}}
        _, draws, _ = joint_bootstrap([], edges, 500, 1)
        self.assertTrue(all(abs(x - 1) < 1e-12 for x in draws))

    def test_estimated_target_repetition_does_not_shrink_common_bridge_uncertainty(self):
        rows = [r for r in self.rows() if r["generation"] == "89"]
        edges = {"one": {"p": -0.2, "q": 0.2}, "two": {"r": 0, "s": 0}}
        a, _, _ = joint_bootstrap(rows, edges, 500, 1)
        b, _, _ = joint_bootstrap(rows * 10, edges, 500, 1)
        np.testing.assert_allclose(a, b)
        self.assertGreater(max(a), min(a))


if __name__ == "__main__":
    unittest.main()
