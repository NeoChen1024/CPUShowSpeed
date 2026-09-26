import unittest

from cpushowspeed.classic_diagnostics import diagnostics


class DiagnosticTests(unittest.TestCase):
    def test_fixed_cohort_and_directional_offset(self):
        rows = []
        for origin, k, models in [("within_DEC", 1, ["a", "b", "c"]), ("legacy_cross_source", 2, ["a", "b"])]:
            for m in models:
                rows.append(dict(origin=origin, pattern="p", model_key=m, first=4, second=9, y=6 * k))
        summary, residuals, transfers = diagnostics(rows)
        f = next(
            r
            for r in transfers
            if r["train_origin"] == "within_DEC"
            and r["test_origin"] == "legacy_cross_source"
            and r["mode"] == "leave_test_model_out"
            and r["predictor"] == "equal_weight"
        )
        self.assertEqual(f["common_models"], 2)
        self.assertAlmostEqual(f["signed_median_percent"], -50)
        reverse = next(
            r
            for r in transfers
            if r["train_origin"] == "legacy_cross_source"
            and r["test_origin"] == "within_DEC"
            and r["mode"] == "leave_test_model_out"
            and r["predictor"] == "equal_weight"
        )
        self.assertAlmostEqual(reverse["signed_median_percent"], 100)
        self.assertTrue(all(r["model"] != "c" for r in residuals))
        row = next(
            r
            for r in residuals
            if r["train_origin"] == "within_DEC"
            and r["test_origin"] == "legacy_cross_source"
            and r["mode"] == "leave_test_model_out"
        )
        self.assertEqual(row["training_models"], 1)

    def test_single_common_model_has_no_heldout_training(self):
        rows = [dict(origin=o, pattern="p", model_key="a", first=1, second=1, y=1) for o in ["within_DEC", "legacy_cross_source"]]
        _, _, transfers = diagnostics(rows)
        t = next(
            t
            for t in transfers
            if t["train_origin"] == "within_DEC"
            and t["test_origin"] == "legacy_cross_source"
            and t["mode"] == "leave_test_model_out"
        )
        self.assertEqual(t["models"], 0)
        self.assertEqual(t["status"], "insufficient_models")
