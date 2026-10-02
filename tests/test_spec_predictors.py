import math
import unittest

import numpy as np
from cpushowspeed.spec_overlap import Result
from cpushowspeed.spec_predictors import (
    bootstrap_logs,
    configuration_logs,
    holdouts,
    log_factor,
    predictor_log,
    triangles,
)


def spec(generation, result_id, track, base, peak, *, system="sys:a", processor="sku:a", clock=2000.0, memory=65536.0):
    return Result(
        generation,
        result_id,
        "System " + system,
        system,
        "CPU " + processor,
        processor,
        2,
        16,
        2,
        clock,
        memory,
        "OS",
        "CC",
        peak,
        base,
        f"https://example.org/{generation}/{track}/{result_id}",
        "sha",
        track=track,
        processor_basis="sku",
    )


def row(model, target, speed, rate, *, system=None, clock=2000.0):
    return dict(
        model_key=model,
        system_key=system or "sys:" + model,
        chips=2,
        clock_mhz=clock,
        target_rate=target,
        speed_score=speed,
        rate_score=rate,
    )


class TriangleTests(unittest.TestCase):
    def test_tuple_needs_all_three_hardware_near_pairs(self):
        targets = [spec("cpu2006", "t1", "rate", 100, 110)]
        speeds = [spec("cpu2017", "s1", "speed", 5, 6), spec("cpu2017", "s2", "speed", 5, 6, memory=131072)]
        rates = [spec("cpu2017", "r1", "rate", 50, 55)]
        rows, rejected, within = triangles(targets, speeds, rates)
        self.assertEqual({(r["speed_id"], r["mode"]) for r in rows}, {("s1", "base"), ("s1", "peak")})
        self.assertEqual(set(within), {("r1", "s1")})
        self.assertEqual(rows[0]["target_rate"], 100)
        self.assertEqual(rejected, [])

    def test_reviewed_boundary_admits_only_accepted_target_rate_pairs(self):
        targets = [spec("cpu92", "t1", "rate", 100, 110)]
        speeds = [spec("cpu95", "s1", "speed", 5, 6)]
        rates = [spec("cpu95", "r1", "rate", 50, 55)]
        self.assertEqual(len(triangles(targets, speeds, rates, {"t1": {"r1": "accept"}})[0]), 2)
        self.assertEqual(triangles(targets, speeds, rates, {"t1": {"r1": "reject"}})[0], [])
        self.assertEqual(triangles(targets, speeds, rates, {})[0], [])

    def test_missing_mode_score_is_rejected_not_imputed(self):
        targets = [spec("cpu2006", "t1", "rate", 100, None)]
        rows, rejected, _ = triangles(targets, [spec("cpu2017", "s1", "speed", 5, 6)], [spec("cpu2017", "r1", "rate", 50, 55)])
        self.assertEqual([r["mode"] for r in rows], ["base"])
        self.assertEqual([r["reason"] for r in rejected], ["incomplete_positive_score_triplet"])


class PredictorTests(unittest.TestCase):
    def test_single_input_predictors_never_read_the_other_input(self):
        r = row("a", 10, 2, 8)
        self.assertEqual(predictor_log(dict(r, rate_score=None), "speed_only"), math.log(2))
        self.assertEqual(predictor_log(dict(r, speed_score=None), "rate_only"), math.log(8))
        self.assertAlmostEqual(predictor_log(r, "equal_geometric"), math.log(4))

    def test_configuration_median_then_model_mean(self):
        rows = [row("a", 10, 1, 5), row("a", 30, 1, 5, system="sys:a2"), row("b", 20, 1, 5), row("c", 40, 1, 5)]
        logs = configuration_logs(rows, "rate_only")
        self.assertEqual(len(logs), 3)
        a = (math.log(2) + math.log(6)) / 2  # log-median of the two systems' ratios
        self.assertAlmostEqual(logs["a", 2, 2000.0], a)
        self.assertAlmostEqual(log_factor(logs), (a + math.log(4) + math.log(8)) / 3)
        self.assertIsNone(log_factor({k: v for k, v in logs.items() if k[0] != "c"}))

    def test_holdout_excludes_the_whole_model(self):
        rows = [row("a", 10, 1, 5), row("b", 20, 1, 5), row("c", 40, 1, 5)]
        logs = configuration_logs(rows, "rate_only")
        predictions, _ = holdouts(rows, "rate_only", logs)
        a = next(p for p in predictions if p["model_key"] == "a")
        self.assertAlmostEqual(a["predicted_older_rate"], 5 * math.exp((math.log(4) + math.log(8)) / 2))

    def test_bootstrap_weights_whole_models(self):
        logs = {("a", 2, 1.0): 0.0, ("a", 2, 2.0): 2.0, ("b", 2, 1.0): 4.0}
        weights = np.array([[1, 0], [0, 2], [0, 0]])
        draws = bootstrap_logs(logs, weights, {"a": 0, "b": 1})
        np.testing.assert_allclose(draws[:2], [1.0, 4.0])
        self.assertTrue(np.isnan(draws[2]))


if __name__ == "__main__":
    unittest.main()
