"""Independent-target, masking and whole-model safeguards for joint predictors."""

import math
import unittest

import numpy as np
from cpushowspeed.spec_joint_tracks import (
    METHODS,
    bootstrap_means,
    configuration_centers,
    evaluate,
    predictor_log,
    triangles,
)
from cpushowspeed.spec_overlap import Result


def row(model, speed, rate, target, chips=1):
    return dict(
        model_key=model, system_key=model, chips=chips, clock_mhz=100, speed_score=speed, rate_score=rate, target_rate=target
    )


def result(generation, rid, score, cores=1, memory=1024):
    return Result(
        generation,
        rid,
        "machine",
        "machine",
        "CPU",
        "cpu",
        1,
        cores,
        1,
        100,
        memory,
        "OS",
        "CC",
        score,
        score,
        "https://example/" + rid,
        "hash",
    )


class JointTracksTests(unittest.TestCase):
    def test_equal_geometric_known_mapping_and_homogeneous_scale(self):
        rows = [row(m, s, r, 3 * math.sqrt(s * r)) for m, s, r in [("a", 1, 9), ("b", 4, 16), ("c", 25, 4)]]
        summary, heldout, _, _ = evaluate(rows, "equal_geometric", [], 0)
        self.assertAlmostEqual(summary["coefficient_older_rate"], 3)
        self.assertLess(summary["model_center_p95_percent"], 1e-10)
        self.assertTrue(all(abs(r["predicted_older_rate"] - r["target_rate"]) < 1e-10 for r in heldout))
        self.assertAlmostEqual(math.exp(predictor_log(row("d", 8, 32, 1), "equal_geometric")), 16)
        self.assertAlmostEqual(math.exp(predictor_log(row("d", 4, 16, 1), "equal_geometric")), 8)

    def test_masks_never_read_hidden_inputs(self):
        r = row("m", 4, 9, 20)
        self.assertEqual(predictor_log(dict(r, rate_score=None), "speed_only"), math.log(4))
        self.assertEqual(predictor_log(dict(r, speed_score=None), "rate_only"), math.log(9))
        rows = [row(m, 2, 8, 10) for m in ("a", "b", "c")]
        changed = [dict(r, rate_score=1e100) for r in rows]
        self.assertEqual(configuration_centers(rows, "speed_only"), configuration_centers(changed, "speed_only"))

    def test_holdout_removes_all_configurations_and_upstream_evidence(self):
        rows = [row("a", 1, 2, 4), row("a", 1, 2, 8, chips=2), row("b", 1, 2, 4), row("c", 1, 2, 4)]
        upstream = [{("a", 1, 100): 100, ("a", 2, 100): 200, ("b", 1, 100): math.log(3), ("c", 1, 100): math.log(3)}]
        _, predicted, _, _ = evaluate(rows, "speed_only", upstream, 1)
        a = [r for r in predicted if r["model_key"] == "a"]
        self.assertTrue(all(abs(r["training_coefficient_older_rate"] - 4) < 1e-12 for r in a))
        self.assertTrue(all(abs(r["training_prefix_vaxen_per_older_rate"] - 3 * 25500 / 604800) < 1e-12 for r in a))
        self.assertTrue(all(r["observed_target_vaxen"] is None for r in predicted))

    def test_duplicate_submissions_do_not_add_independent_config_weight(self):
        rows = [row(m, 2, 8, y) for m, y in [("a", 4), ("b", 8), ("c", 16)]]
        for method in METHODS:
            self.assertEqual(configuration_centers(rows, method), configuration_centers(rows + [rows[0]] * 100, method))

    def test_joint_sampling_preserves_shared_model_cancellation(self):
        weights = np.array([[1, 2, 3], [3, 1, 2], [0, 0, 6]])
        index = dict(a=0, b=1, c=2)
        logs = {(m, 1, 100): z for m, z in [("a", -1), ("b", 0), ("c", 1)]}
        a = bootstrap_means(logs, weights, index)
        b = bootstrap_means({k: -v for k, v in logs.items()}, weights, index)
        np.testing.assert_allclose(a + b, 0)

    def test_three_way_matching_and_target_reuse(self):
        t = result("cpu92", "target", 100, cores=None)
        s = result("cpu95", "speed", 2, cores=1)
        r = result("cpu95", "rate", 20, cores=2)
        rows, rejected, _, _ = triangles([t], [s], [r])
        self.assertFalse(rows)  # Both match unknown-core target; they contradict each other.
        self.assertIn("configuration_conflict", rejected[0]["reason"])
        r = result("cpu95", "rate", 20, cores=1)
        rows, _, _, _ = triangles([t], [s], [r])
        self.assertEqual(len(rows), 2)
        same = result("cpu95", "target", 20, cores=1)
        rows, rejected, _, _ = triangles([t], [s], [same])
        self.assertFalse(rows)
        self.assertTrue(any("reused_target" in x["reason"] for x in rejected))

    def test_insufficient_models_never_get_a_coefficient(self):
        summary, heldout, _, _ = evaluate([row("a", 1, 2, 3)] * 20, "equal_geometric", [], 0)
        self.assertEqual(summary["status"], "insufficient_models")
        self.assertNotIn("coefficient_vaxen", summary)
        self.assertFalse(heldout)
