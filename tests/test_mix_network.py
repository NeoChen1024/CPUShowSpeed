import math
import unittest

from cpushowspeed.classic_network_model import metric_weights, train
from cpushowspeed.mix_network import attach


class MixNetworkTests(unittest.TestCase):
    def test_latent_bridge_recovers_known_coefficient(self):
        nodes = [
            dict(
                node_id="anchor", model_key="a", target_kind="observed_rate", target=4, log_scores={"Whetstone:MWIPS": math.log(2)}
            ),
            dict(
                node_id="old",
                model_key="b",
                target_kind="unanchored",
                target=None,
                log_scores={"Whetstone:MWIPS": math.log(3), "InstructionMix:Gibson_KIPS": math.log(100)},
            ),
        ]
        alpha, _ = train(nodes, {}, False)
        self.assertAlmostEqual(math.exp(alpha["InstructionMix:Gibson_KIPS"]), 0.06)
        held, _ = train(nodes, {}, False, exclude="b")
        self.assertNotIn("InstructionMix:Gibson_KIPS", held)
        self.assertIsNone(nodes[1]["target"])

    def test_correlated_mixes_share_one_family_vote(self):
        weights = metric_weights(["InstructionMix:Gibson_KIPS", "InstructionMix:ADP_KIPS", "Whetstone:MWIPS"])
        self.assertEqual(weights["InstructionMix:Gibson_KIPS"], 0.25)
        self.assertEqual(weights["InstructionMix:ADP_KIPS"], 0.25)
        self.assertEqual(weights["Whetstone:MWIPS"], 0.5)

    def test_reused_mix_observation_closes_holdout_groups(self):
        nodes = [
            dict(
                node_id=k,
                model_key=k,
                observations=[dict(observation_id=k, metric="Whetstone:MWIPS")],
                log_scores={"Whetstone:MWIPS": 0},
                target_kind="unanchored",
                target=None,
            )
            for k in ["a", "b"]
        ]
        obs = [dict(configuration_id=k, observation_id=k, metric="Whetstone:MWIPS") for k in ["a", "b"]]
        pairs = [
            dict(classical_configuration_id=k, metric="Whetstone:MWIPS", mix="Gibson Mix", mix_id="one-source-row", mix_kips=100)
            for k in ["a", "b"]
        ]
        extended, baseline, audit, closure = attach(nodes, pairs + pairs, obs)
        self.assertEqual(closure["a"], closure["b"])
        self.assertEqual(extended[0]["mix_ids"], ["one-source-row"])
        self.assertEqual(extended[0]["model_key"], extended[1]["model_key"])
        self.assertNotIn("InstructionMix:Gibson_KIPS", baseline[0]["log_scores"])
        self.assertNotIn("InstructionMix:Gibson_KIPS", nodes[0]["log_scores"])
