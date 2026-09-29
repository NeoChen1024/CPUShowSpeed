"""Guard separate targets, legacy layouts, and missing peak values."""

import unittest
from pathlib import Path

from cpushowspeed.classic_network_data import build
from cpushowspeed.classic_network_model import train
from cpushowspeed.spec_dual_track import chain_intervals, parse_speed92
from cpushowspeed.spec_rate_fit import collect_integer


class DualTrackTests(unittest.TestCase):
    def document(self, base_only=False):
        rows = []
        for name, ref in [
            ("008.espresso", 2270),
            ("022.li", 6210),
            ("023.eqntott", 1100),
            ("026.compress", 2770),
            ("072.sc", 4530),
            ("085.gcc", 5460),
        ]:
            rows.append(f"{name} - {ref / 10} - 10" if base_only else f"{name} {ref} {ref / 10} 10")
        metric = "<DD>SPECint92: -\n<DD>SPECbase_int92: 10" if base_only else "Geometric Mean (SPECint92): 10"
        return (
            "<H3>Vendor</H3><H3>System</H3>\n"
            + "\n".join(rows)
            + "\n"
            + metric
            + "\n<DD>CPU: 50 MHz CPU\n<DD>Number of CPUs: 1\n<DD>Memory: 32MB\n"
        )

    def test_legacy_reference_time_column_and_base_only(self):
        peak = parse_speed92(self.document(), "https://example/result", "digest")
        self.assertEqual(peak.peak, 10)
        self.assertIsNone(peak.base)
        base = parse_speed92(self.document(True), "https://example/result", "digest")
        self.assertIsNone(base.peak)
        self.assertEqual(base.base, 10)
        with self.assertRaisesRegex(ValueError, "disagrees"):
            parse_speed92(
                self.document().replace("Geometric Mean (SPECint92): 10", "Geometric Mean (SPECint92): 20"), "url", "hash"
            )
        with self.assertRaises(ValueError):
            parse_speed92("SPECrate_int92 " + self.document(), "url", "hash")

    def test_observed_speed_is_an_independent_anchor(self):
        nodes = [dict(model_key="a", target_kind="observed_speed", target=20, log_scores={"Dhrystone:v1.1_DMIPS": 0})]
        speed, _ = train(nodes, {}, False)
        rate, _ = train([dict(nodes[0], target_kind="observed_rate", target=200)], {}, False)
        import math

        self.assertAlmostEqual(math.exp(speed["Dhrystone:v1.1_DMIPS"]), 20)
        self.assertAlmostEqual(math.exp(rate["Dhrystone:v1.1_DMIPS"]), 200)
        with self.assertRaisesRegex(ValueError, "separate fits"):
            train(nodes + [dict(nodes[0], model_key="b", target_kind="observed_rate")], {}, False)

    def test_source_column_speed_does_not_receive_rate_unit_factor(self):
        v = dict(
            id="v",
            model_key="m",
            machine="M",
            targets={"SPECint92": 100, "SPECrate_int92": 10000},
            scores={"Dhrystone:v1.1_DMIPS": 2},
            observation_ids={"Dhrystone:v1.1_DMIPS": "o"},
            source_url="url",
        )
        speed, *_ = build({}, {}, [], [v], [], [], False, target_metric="SPECint92")
        rate, *_ = build({}, {}, [], [v], [], [], False)
        self.assertEqual(speed[0]["target"], 100)
        self.assertEqual(speed[0]["target_kind"], "observed_speed")
        self.assertAlmostEqual(rate[0]["target"], 10000 * 25500 / 604800)

    def test_shared_configuration_chain_bootstrap_preserves_cancellation(self):
        import math

        pairs = []
        generations = ["cpu92", "cpu95", "cpu2000", "cpu2006", "cpu2017", "cpu2026"]
        for i, (old, new) in enumerate(zip(generations, generations[1:])):
            for j in range(3):
                z = (j - 1) * (1 if i == 0 else -1 if i == 1 else 0)
                pairs.append(
                    dict(
                        old_generation=old,
                        new_generation=new,
                        match_tier="hardware_near",
                        system_key=str(j),
                        processor_key=str(j),
                        chips=1,
                        old_clock_mhz=100,
                        base_ratio=math.exp(z),
                        peak_ratio=math.exp(z),
                    )
                )
        rows, arrays = chain_intervals(pairs, draws=100, seed=1)
        for mode in ("base", "peak"):
            self.assertTrue(all(abs(x - 1) < 1e-12 for x in arrays[mode][:, -1]))

    def test_invalid_track_rejected(self):
        with self.assertRaises(ValueError):
            collect_integer(Path("/unused"), "mixed")
