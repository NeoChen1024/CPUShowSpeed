import json
import math
import unittest

import numpy as np
from cpushowspeed.mix.network_fit import attach, estimates


def node(node_id, model, scores, kind="unanchored", target=None):
    return dict(node_id=node_id, model_key=model, system=model, target_kind=kind, target=target, log_scores=dict(scores))


def mix(result_id, system_id, metric, kips):
    return dict(
        result_id=result_id,
        row_id=result_id.rsplit(":", 1)[0],
        system=system_id,
        system_id=system_id,
        metric=metric,
        kips=kips,
        source_url="https://example.org/mix",
    )


G, A = "InstructionMix:Gibson_KIPS", "InstructionMix:ADP_KIPS"


class AttachTests(unittest.TestCase):
    def setUp(self):
        self.nodes = [
            node("n1", "sys:a", {"Whetstone:MWIPS": 0.0}),
            node("n2", "sys:a", {"Whetstone:MWIPS_DP": 0.0}),
            node("n3", "sys:b", {"Whetstone:MWIPS": 1.0}),
        ]
        self.edges = {"int89_to_int92": {"sys:a": 0.1, "sys:b": 0.3}}

    def test_rating_attaches_to_every_node_of_its_system_only(self):
        extended, baseline, _, audit = attach(self.nodes, self.edges, [mix("m:tr:1:G", "sys:a", G, 4.0)], {}, "resolved_system")
        self.assertEqual([n["mix_metrics"] for n in extended], [[G], [G], []])
        self.assertAlmostEqual(extended[0]["log_scores"][G], math.log(4.0))
        self.assertNotIn(G, baseline[0]["log_scores"])
        self.assertEqual(audit[0]["attached_nodes"], 2)

    def test_pending_links_attach_only_in_their_scenario_and_merge_clusters(self):
        links = {"sys:a": {"sys:b"}, "sys:b": {"sys:a"}}
        ratings = [mix("m:tr:1:G", "sys:a", G, 4.0)]
        resolved = attach(self.nodes, self.edges, ratings, links, "resolved_system")
        self.assertEqual({n["model_key"] for n in resolved[0]}, {"sys:a", "sys:b"})
        extended, baseline, edges, _ = attach(self.nodes, self.edges, ratings, links, "plus_pending_links")
        self.assertEqual({n["model_key"] for n in extended}, {"sys:a"})
        self.assertEqual({n["model_key"] for n in baseline}, {"sys:a"})
        self.assertAlmostEqual(edges["int89_to_int92"]["sys:a"], 0.2)

    def test_unresolved_rating_attaches_nowhere(self):
        _, _, _, audit = attach(self.nodes, self.edges, [mix("m:tr:1:G", "", G, 4.0)], {}, "resolved_system")
        self.assertEqual(audit[0]["status"], "no_classical_node")


class EstimateTests(unittest.TestCase):
    def test_combined_row_uses_aligned_draws(self):
        ratings = [
            mix("m:tr:1:Gibson Mix", "sys:a", G, 4.0),
            mix("m:tr:1:ADP Mix", "sys:a", A, 9.0),
            mix("m:tr:2:ADP Mix", "sys:b", A, 1.0),
        ]
        # One shared mix exponent with per-mix intercepts.
        calib = {G: (math.log(0.5), 0.5), A: (math.log(2.0), 0.5)}
        # Perfectly anticorrelated intercept draws cancel in the two-mix combination.
        t = np.linspace(-1, 1, 101)
        intercepts = np.column_stack([t + calib[G][0], -t + calib[A][0]])
        exponents = np.full_like(intercepts, 0.5)
        rows = {r["record_id"]: r for r in estimates(ratings, calib, [G, A], intercepts, exponents, {})}
        combined = rows["m:tr:1"]
        self.assertAlmostEqual(combined["estimated_vaxen"], math.sqrt(0.5 * 4.0**0.5 * 2.0 * 9.0**0.5))
        self.assertAlmostEqual(combined["ci95_low"], combined["ci95_high"])
        self.assertEqual(json.loads(combined["result_ids"]), ["m:tr:1:Gibson Mix", "m:tr:1:ADP Mix"])
        self.assertEqual(rows["m:tr:2"]["combination"], "single_available")
        self.assertAlmostEqual(rows["m:tr:2"]["estimated_vaxen"], rows["m:tr:2:ADP Mix"]["estimated_vaxen"])


if __name__ == "__main__":
    unittest.main()
