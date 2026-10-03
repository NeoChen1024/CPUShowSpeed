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
from cpushowspeed.classical_store import vax780_anchor


def node(key, scores, target=None, kind=None):
    return dict(
        node_id=key,
        model_key=key,
        log_scores={k: math.log(v) for k, v in scores.items()},
        target=target,
        target_kind=kind or ("observed_speed" if target else "unanchored"),
    )


class NetworkTests(unittest.TestCase):
    def test_processor_upgrade_is_not_clock_scaled_into_an_anchor(self):
        target = result("s", "sys:hp715", {"SPECint92": 100}, clock=100, entity="cpu:7100lc", scope="spec:cpu92")
        c = result("c", "sys:hp715", {"Dhrystone:v1.1_DMIPS": 10}, clock=33, entity="cpu:7100")
        nodes, _, audit = build([target, c], True)
        self.assertFalse(any(n["target_kind"] == "observed_speed" for n in nodes))
        self.assertEqual(
            audit,
            [dict(target_result_id="s", classical_result_id="c", status="clock_conflict_processor_unverified", included=False)],
        )
        self.assertEqual([n["target_kind"] for n in nodes], ["unanchored"])

    def test_specint89_targets_come_from_any_source_but_the_bridge_table(self):
        c = result("c", "sys:rc3360", {"LINPACK:n100_MFLOPS": 5})
        curated = result("t", "sys:rc3360", {"SPECint89": 27.1}, scope="reviewed-vector:mashey")
        bridge = result("b", "sys:rc3360", {"SPECint89": 27.1}, scope="historical-spec:spec89-bridge")
        nodes, _, _ = build([c, curated], True)
        self.assertEqual([(n["node_id"], n["target_kind"], n["target"]) for n in nodes], [("t", "estimated_89", 27.1)])
        nodes, _, _ = build([c, bridge], True)
        self.assertEqual([n["target_kind"] for n in nodes], ["unanchored"])

    def test_versions_share_family_weight(self):
        w = metric_weights(["Dhrystone:1", "Dhrystone:2", "Whetstone:SP", "Whetstone:DP", "LINPACK:100"])
        self.assertAlmostEqual(w["Dhrystone:1"] + w["Dhrystone:2"], 1 / 3)
        self.assertAlmostEqual(w["LINPACK:100"], 1 / 3)

    def test_anchored_power_law_is_recovered_through_the_780(self):
        # Exact y = 0.8 (log x - log 0.5): the 780 scores 0.5 and predicts 1 speed-VAXen.
        anchor = {"Dhrystone:1": math.log(0.5)}
        rows = [node(k, {"Dhrystone:1": x}, (2 * x) ** 0.8) for k, x in [("a", 4), ("b", 16), ("c", 64)]]
        calib, _ = train(rows, {}, False, anchor)
        a, b = calib["Dhrystone:1"]
        self.assertAlmostEqual(b, 0.8)
        self.assertAlmostEqual(a + b * anchor["Dhrystone:1"], 0)

    def test_variants_of_a_family_share_one_exponent(self):
        anchor = {"Dhrystone:1": 0.0, "Dhrystone:2": math.log(2)}
        rows = [node(k, {"Dhrystone:1": x, "Dhrystone:2": 2 * x}, x**0.9) for k, x in [("a", 3), ("b", 9), ("c", 27)]]
        calib, _ = train(rows, {}, False, anchor)
        self.assertAlmostEqual(calib["Dhrystone:1"][1], calib["Dhrystone:2"][1])
        self.assertAlmostEqual(calib["Dhrystone:1"][1], 0.9)
        self.assertAlmostEqual(calib["Dhrystone:2"][0], -0.9 * math.log(2))

    def test_whetstone_precisions_have_their_own_exponents(self):
        anchor = {"Whetstone:SP": 0.0, "Whetstone:DP": 0.0}
        rows = [node(k, {"Whetstone:SP": x, "Whetstone:DP": x}) for k, x in [("u", 2), ("v", 8)]]
        rows += [node(k, {"Whetstone:SP": x}, x**0.9) for k, x in [("a", 3), ("b", 9)]]
        rows += [node(k, {"Whetstone:DP": x}, x**0.6) for k, x in [("c", 3), ("d", 9)]]
        calib, _ = train(rows, {}, False, anchor, latent=False)
        self.assertAlmostEqual(calib["Whetstone:SP"][1], 0.9)
        self.assertAlmostEqual(calib["Whetstone:DP"][1], 0.6)

    def test_one_family_unanchored_nodes_do_not_set_exponents(self):
        anchor = {"Whetstone:SP": 0.0, "Whetstone:DP": 0.0}
        rows = [node(k, {"Whetstone:SP": x}, x**0.9) for k, x in [("a", 3), ("b", 9)]]
        rows += [node(k, {"Whetstone:DP": x}, x**0.6) for k, x in [("c", 3), ("d", 9)]]
        rows.append(node("u", {"Whetstone:SP": 2, "Whetstone:DP": 50}))
        calib, _ = train(rows, {}, False, anchor)
        self.assertAlmostEqual(calib["Whetstone:SP"][1], 0.9)
        self.assertAlmostEqual(calib["Whetstone:DP"][1], 0.6)

    def test_one_family_unanchored_nodes_still_set_free_intercepts(self):
        # The mix exponent comes from the cross-family nodes alone; both free intercepts are
        # re-solved with the mix-only node included.
        anchor = {"Dhrystone:1": 0.0}
        rows = [
            node("a", {"Dhrystone:1": 5}, 5),
            node("b", {"Dhrystone:1": 10}, 10),
            node("c", {"Dhrystone:1": 6, "InstructionMix:G": 3, "InstructionMix:A": 1}),
            node("d", {"Dhrystone:1": 12, "InstructionMix:G": 6, "InstructionMix:A": 2}),
            node("e", {"InstructionMix:G": 3, "InstructionMix:A": 3}),
        ]
        without, _ = train(rows[:-1], {}, False, anchor)
        self.assertAlmostEqual(without["InstructionMix:G"][1], 1)
        self.assertAlmostEqual(math.exp(without["InstructionMix:G"][0]), 2)
        calib, _ = train(rows, {}, False, anchor)
        for m in ("InstructionMix:G", "InstructionMix:A"):
            self.assertAlmostEqual(calib[m][1], without[m][1])
            self.assertNotAlmostEqual(calib[m][0], without[m][0])

    def test_unanchored_overlap_identifies_a_free_intercept(self):
        # Dhrystone is anchored at the 780 (score 1, exponent 1 from a and b); LINPACK has no
        # 780 rating and no target pair, so its free intercept comes from unanchored overlap
        # with a shared LINPACK exponent identified by two overlap nodes.
        anchor = {"Dhrystone:1": 0.0}
        rows = [
            node("a", {"Dhrystone:1": 5}, 5),
            node("b", {"Dhrystone:1": 10}, 10),
            node("c", {"Dhrystone:1": 6, "LINPACK:100": 3}),
            node("d", {"Dhrystone:1": 12, "LINPACK:100": 6}),
            node("disconnected", {"Unknown:one": 1, "Unknown:two": 2}),
        ]
        calib, _ = train(rows, {}, False, anchor)
        a, b = calib["LINPACK:100"]
        self.assertAlmostEqual(b, 1)
        self.assertAlmostEqual(math.exp(a), 2)
        self.assertNotIn("Unknown:one", calib)
        baseline, _ = train(rows, {}, False, anchor, latent=False)
        self.assertNotIn("LINPACK:100", baseline)

    def test_removing_holdout_also_removes_its_bridge_information(self):
        rows = [
            node("a", {"Dhrystone:1": 1}, 1, "estimated_89"),
            node("b", {"Dhrystone:1": 2}, 2, "estimated_89"),
            node("c", {"Dhrystone:1": 4}, 4, "estimated_89"),
        ]
        edges = {"first": {"a": 0, "b": math.log(2), "c": math.log(2)}}
        anchor = {"Dhrystone:1": math.log(0.5)}
        calib, _ = train(rows, edges, True, anchor, exclude="a")
        rows[0]["log_scores"]["Dhrystone:1"] = 100
        edges["first"]["a"] = 100
        changed, _ = train(rows, edges, True, anchor, exclude="a")
        self.assertEqual(calib, changed)
        # Bridged targets 4 and 8 at scores 2 and 4, through (0.5, 1): exponent 1, intercept log 2.
        self.assertAlmostEqual(calib["Dhrystone:1"][1], 1)
        self.assertAlmostEqual(math.exp(calib["Dhrystone:1"][0]), 2)

    def test_one_measurement_and_partial_predictions(self):
        n = node("a", {"Dhrystone:1": 10, "LINPACK:100": 3})
        calib = {"Dhrystone:1": (math.log(2), 1.0), "LINPACK:100": (math.log(4), 0.5)}
        r = estimates(n, calib)
        full = next(x for x in r if x["subset"] == "all_available")
        self.assertAlmostEqual(math.exp(full["predicted_log"]), math.sqrt(20 * 4 * math.sqrt(3)))
        partial = estimates(n, {"Dhrystone:1": calib["Dhrystone:1"]})
        self.assertNotIn("all_available", {r["subset"] for r in partial})

    def test_joint_bootstrap_uses_correlated_bridge_edges_and_anchor_draws(self):
        rows = [node(k, {"Dhrystone:1": v}, v, "estimated_89") for k, v in [("a", 1), ("b", 2), ("c", 3)]]
        edges = {"one": {"a": -1, "b": 1, "c": 0}, "two": {"a": 1, "b": -1, "c": 0}}
        anchor = {"Dhrystone:1": math.log(0.5)}
        metrics, intercepts, exponents = bootstrap(rows, edges, True, anchor, {}, 300, 5)
        self.assertEqual(metrics, ["Dhrystone:1"])
        self.assertEqual(intercepts.shape, exponents.shape)
        # Without anchor error every draw passes through the 780 anchor.
        self.assertTrue(np.allclose(intercepts[:, 0] + exponents[:, 0] * anchor["Dhrystone:1"], 0))
        _, noisy, slopes = bootstrap(rows, edges, True, anchor, {"Dhrystone:1": 0.2}, 300, 5)
        self.assertGreater(np.std(noisy[:, 0] + slopes[:, 0] * anchor["Dhrystone:1"]), 0.01)

    def test_vax780_anchor_is_the_median_of_distinct_runs(self):
        rows = [
            result("r1", "sys:vax11/780", {"Dhrystone:v1.1_DMIPS": 0.8}, clock=5),
            result("r2", "sys:vax11/780", {"Dhrystone:v1.1_DMIPS": 1.0}, clock=5),
            result("r3", "sys:vax11/780", {"Dhrystone:v1.1_DMIPS": 0.9}, clock=5),
            result("x", "sys:other", {"Dhrystone:v1.1_DMIPS": 5, "LINPACK:n100_MFLOPS": 1}, clock=5),
        ]
        anchor, sd, audit = vax780_anchor(rows)
        self.assertEqual(set(anchor), {"Dhrystone:v1.1_DMIPS"})
        self.assertAlmostEqual(anchor["Dhrystone:v1.1_DMIPS"], math.log(0.9))
        self.assertGreater(sd["Dhrystone:v1.1_DMIPS"], 0)
        self.assertEqual(audit[0]["vax780_runs"], 3)

    def test_vax780_anchor_spread_ignores_a_wildly_inconsistent_group(self):
        metric = "Whetstone:MWIPS"
        rows = [result(f"v{i}", "sys:vax11/780", {metric: s}, clock=5) for i, s in enumerate((0.9, 1.0, 1.1))]
        rows += [result(f"o{i}", "sys:other", {metric: s}, clock=5) for i, s in enumerate((9, 10, 11))]
        _, sd, _ = vax780_anchor(rows)
        baseline = sd[metric]
        rows += [result(f"b{i}", "sys:basic", {metric: s}, clock=5) for i, s in enumerate((0.001, 0.5, 0.45))]
        _, sd, _ = vax780_anchor(rows)
        self.assertLess(sd[metric], 1.5 * baseline)


if __name__ == "__main__":
    unittest.main()
