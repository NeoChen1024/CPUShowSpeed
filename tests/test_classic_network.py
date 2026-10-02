import math
import unittest

import numpy as np
from classical_fixture import result
from cpushowspeed.classic_network import build
from cpushowspeed.classic_network_model import (
    bootstrap,
    estimates,
    metric_weights,
    train,
)


def node(key, scores, target=None, kind=None):
    return dict(
        node_id=key,
        model_key=key,
        log_scores={k: math.log(v) for k, v in scores.items()},
        target=target,
        target_kind=kind or ("observed_rate" if target else "unanchored"),
    )


class NetworkTests(unittest.TestCase):
    def test_processor_upgrade_is_not_clock_scaled_into_an_anchor(self):
        target = result("s", "sys:hp715", {"SPECrate_int92": 100}, clock=100, entity="cpu:7100lc", scope="spec:cpu92")
        c = result("c", "sys:hp715", {"Dhrystone:v1.1_DMIPS": 10}, clock=33, entity="cpu:7100")
        nodes, _, audit = build([target, c], True)
        self.assertFalse(any(n["target_kind"] == "observed_rate" for n in nodes))
        self.assertEqual(
            audit,
            [dict(target_result_id="s", classical_result_id="c", status="clock_conflict_processor_unverified", included=False)],
        )
        self.assertEqual([n["target_kind"] for n in nodes], ["unanchored"])

    def test_versions_share_family_weight(self):
        w = metric_weights(["Dhrystone:1", "Dhrystone:2", "Whetstone:SP", "Whetstone:DP", "LINPACK:100"])
        self.assertAlmostEqual(w["Dhrystone:1"] + w["Dhrystone:2"], 1 / 3)
        self.assertAlmostEqual(w["LINPACK:100"], 1 / 3)

    def test_unanchored_overlap_identifies_missing_benchmark_coefficient(self):
        # D coefficient = 2 from measured target; no L/target pair exists.
        # Common unanchored hardware gives D=6, L=3, so L coefficient must be 4.
        rows = [
            node("a", {"Dhrystone:1": 5}, 10),
            node("b", {"Dhrystone:1": 6, "LINPACK:100": 3}),
            node("disconnected", {"Unknown:one": 1, "Unknown:two": 2}),
        ]
        alpha, _ = train(rows, {}, False)
        self.assertAlmostEqual(math.exp(alpha["Dhrystone:1"]), 2)
        self.assertAlmostEqual(math.exp(alpha["LINPACK:100"]), 4)
        self.assertNotIn("Unknown:one", alpha)
        baseline, _ = train(rows, {}, False, latent=False)
        self.assertNotIn("LINPACK:100", baseline)

    def test_removing_holdout_also_removes_its_bridge_information(self):
        rows = [
            node("a", {"Dhrystone:1": 1}, 1, "estimated_89"),
            node("b", {"Dhrystone:1": 2}, 2, "estimated_89"),
            node("c", {"Dhrystone:1": 3}, 3, "estimated_89"),
        ]
        edges = {"first": {"a": 0, "b": math.log(2), "c": math.log(2)}}
        alpha, _ = train(rows, edges, True, exclude="a")
        rows[0]["log_scores"]["Dhrystone:1"] = 100
        edges["first"]["a"] = 100
        changed, _ = train(rows, edges, True, exclude="a")
        self.assertEqual(alpha, changed)
        self.assertAlmostEqual(math.exp(alpha["Dhrystone:1"]), 2)

    def test_one_measurement_and_partial_predictions(self):
        n = node("a", {"Dhrystone:1": 10, "LINPACK:100": 3})
        r = estimates(n, {"Dhrystone:1": math.log(2), "LINPACK:100": math.log(4)})
        full = next(x for x in r if x["subset"] == "all_available")
        self.assertAlmostEqual(math.exp(full["predicted_log"]), math.sqrt(20 * 12))
        partial = estimates(n, {"Dhrystone:1": math.log(2)})
        self.assertNotIn("all_available", {r["subset"] for r in partial})

    def test_joint_bootstrap_uses_correlated_bridge_edges(self):
        rows = [node(k, {"Dhrystone:1": v}, v, "estimated_89") for k, v in [("a", 1), ("b", 2), ("c", 3)]]
        edges = {"one": {"a": -1, "b": 1, "c": 0}, "two": {"a": 1, "b": -1, "c": 0}}
        metrics, draws = bootstrap(rows, edges, True, 300, 5)
        self.assertEqual(metrics, ["Dhrystone:1"])
        self.assertTrue(np.allclose(draws, 0, atol=1e-12))
