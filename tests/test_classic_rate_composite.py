import json
import math
import unittest

from cpushowspeed.classic_fit import ANCHOR
from cpushowspeed.classic_rate_composite import calculate, prepare


class RateCompositeTests(unittest.TestCase):
    def source(self):
        rows = []
        for model, scale in [("a", 1), ("b", 2), ("c", 4)]:
            for target in ("SPECint89", "SPECint92", "SPECrate_int92", "SPECrate_base_int92"):
                for a, b in [("Dhrystone:d", "Whetstone:w"), ("Dhrystone:d", "LINPACK:l"), ("LINPACK:l", "Whetstone:w")]:
                    rows.append(
                        dict(
                            stage="within_source",
                            target=target,
                            model_key=model,
                            spec_id=model + target,
                            origin="within_DEC",
                            y=str(8 * scale),
                            pattern=a + "+" + b,
                            first_id=model + a,
                            second_id=model + b,
                            first=str(4 * scale),
                            second=str(4 * scale),
                            provenance="{}",
                        )
                    )
        return rows

    def test_rate_only_no_second_normalization_and_complete_triples(self):
        rows = prepare(self.source(), "within_source")
        self.assertEqual(len(rows), 24)
        self.assertEqual({r["target"] for r in rows}, {"SPECrate_int92", "SPECrate_base_int92"})
        self.assertEqual(sum(len(json.loads(r["member_ids"])) == 3 for r in rows), 6)
        for r in rows:
            self.assertAlmostEqual(r["y_vaxen"] / r["x"], 2)
            self.assertAlmostEqual(r["rate_score_reconstructed_from_input"] * ANCHOR, r["y_vaxen"])

    def test_known_rate_factor_and_separate_variants(self):
        rows = prepare(self.source(), "within_source")
        for r in rows:
            if r["variant"] == "base":
                r["y_vaxen"] *= 0.5
        summaries, predictions = calculate(rows, 100, 20260927)
        for r in summaries:
            expected = 1 if r["variant"] == "base" else 2
            self.assertAlmostEqual(r["factor"], expected)
            self.assertAlmostEqual(r["factor_ci95_low"], expected)
            self.assertAlmostEqual(r["factor_ci95_high"], expected)
            self.assertLess(r["loo_model_p95_percent"], 1e-10)
        self.assertTrue(all(abs(r["signed_error_percent"]) < 1e-10 for r in predictions))

    def test_single_baselines_share_the_same_observations(self):
        summaries, predictions = calculate(prepare(self.source(), "within_source"), 100, 1)
        contexts = {(r["target"], r["pattern"]) for r in summaries}
        for target, pattern in contexts:
            groups = {}
            for r in predictions:
                if (r["target"], r["pattern"]) == (target, pattern):
                    groups.setdefault(r["predictor"], []).append((r["model_key"], r["spec_id"], r["member_ids"]))
            self.assertTrue(all(sorted(g) == sorted(groups["equal_weight"]) for g in groups.values()))
