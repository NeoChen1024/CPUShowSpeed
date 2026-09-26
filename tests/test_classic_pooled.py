import math
import unittest

from cpushowspeed.classic_pooled import (
    bootstrap_factors,
    composites,
    evaluate,
    log_factor,
)


class PooledTests(unittest.TestCase):
    def test_shared_bridge_multiplier_and_identity(self):
        rows = [
            dict(model_key=m, z=0.0, generation="89", x=1.0, raw_target=1.0, target="SPECint89", spec_id=m, member_ids="[]")
            for m in ("a", "b", "c")
        ]
        bridge = {m: math.log(2) for m in ("a", "b", "c")}
        result, predictions = evaluate(rows, bridge, 100, 1)
        self.assertAlmostEqual(result["factor"], 2)
        self.assertAlmostEqual(result["factor_ci95_low"], 2)
        self.assertAlmostEqual(result["loo_model_p95_percent"], 0)
        self.assertTrue(all(abs(p["predicted"] - 2) < 1e-10 for p in predictions))
        identity, _ = evaluate(rows, bridge, 100, 1, True)
        self.assertAlmostEqual(identity["factor"], 1)

    def test_heldout_bridge_and_outcome_cannot_leak_into_training(self):
        rows = [dict(model_key=m, z=z, generation="89") for m, z in [("a", 20), ("b", 0), ("c", 0)]]
        bridge = {"a": 30, "b": 0, "c": 0}
        self.assertEqual(log_factor(rows, bridge, exclude="a"), (0, 0))

    def test_bridge_uncertainty_is_shared_not_averaged_per_observation(self):
        rows = [dict(model_key=m, z=0, generation="89") for m in ("x", "y")]
        bridge = {"a": math.log(0.5), "b": math.log(2)}
        a = bootstrap_factors(rows, bridge, 500, 1)
        b = bootstrap_factors(rows * 10, bridge, 500, 1)
        self.assertEqual(a, b)
        self.assertGreater(max(a), min(a))

    def test_triple_requires_complete_compatible_record_edges(self):
        rows = []
        for a, b in [("Dhrystone:d", "Whetstone:w"), ("Dhrystone:d", "LINPACK:l"), ("LINPACK:l", "Whetstone:w")]:
            rows.append(
                dict(
                    stage="test",
                    target="SPECint92",
                    model_key="a",
                    spec_id="s",
                    origin="source",
                    y="8",
                    pattern=a + "+" + b,
                    first_id=a,
                    second_id=b,
                    first="4",
                    second="4",
                    provenance="{}",
                )
            )
        result = composites(rows, "test")
        self.assertEqual(len(result), 4)
        self.assertAlmostEqual(result[-1]["x"], 4)
        self.assertEqual(len(composites(rows[:2], "test")), 2)
        # Repeated source observations remain in pair output; joining a triangle
        # itself must not multiply the same three observation identities.
        repeated = composites(rows + [rows[0]], "test")
        self.assertEqual(len(repeated), 5)


if __name__ == "__main__":
    unittest.main()
