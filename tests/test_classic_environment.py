import unittest

from cpushowspeed.classic_environment import cells, evaluate, predict, train


class EnvironmentTests(unittest.TestCase):
    def rows(self):
        return [
            dict(
                model_key=m,
                environment=e,
                z=z,
                x=1,
                y=str(__import__("math").exp(z)),
                origin="source",
                spec_id=m + e,
                first_id=m + e + "a",
                second_id=m + e + "b",
            )
            for m in ["a", "b", "c"]
            for e, z in [("os1", 0.0), ("os2", 1.0)]
        ]

    def test_equal_model_and_environment_weight_and_shrinkage(self):
        rows = self.rows()
        self.assertAlmostEqual(sum(w for m, e, z, w in cells(rows)), 3)
        self.assertEqual(train(rows + [rows[0]] * 20, "pooled"), train(rows, "pooled"))
        pooled = train(rows, "pooled")
        grouped = train(rows, "grouped")
        shrunk = train(rows, "shrinkage", 4)
        self.assertAlmostEqual(predict(pooled, "os1"), 0.5)
        self.assertAlmostEqual(predict(grouped, "os1"), 0)
        self.assertTrue(0 < predict(shrunk, "os1") < 0.5)
        self.assertAlmostEqual(predict(shrunk, "new_os"), 0.5)

    def test_nested_selection_never_uses_heldout_model_outcome(self):
        rows = self.rows()
        _, _, a = evaluate(rows)
        for r in rows:
            if r["model_key"] == "a":
                r["z"] += 2
                r["y"] = str(float(r["y"]) * __import__("math").exp(2))
        _, _, b = evaluate(rows)
        first = [r["predicted"] for r in a if r["scheme"] == "leave_model_out" and r["heldout"] == "a"]
        second = [r["predicted"] for r in b if r["scheme"] == "leave_model_out" and r["heldout"] == "a"]
        self.assertEqual(first, second)
        self.assertEqual(len(first), 6)
