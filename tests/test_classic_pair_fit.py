import unittest

from cpushowspeed.classic_pair_fit import PATTERNS, analyze, values, version_audit


class PairFitTests(unittest.TestCase):
    def test_only_distinct_families_and_separate_versions(self):
        self.assertEqual(len(PATTERNS), 8)
        self.assertTrue(all(a[0] != b[0] for a, b in PATTERNS))

    def test_scaling_without_third_benchmark(self):
        d = dict(id="d", benchmark="Dhrystone", clock_mhz=100)
        w = dict(id="w", benchmark="Whetstone", clock_mhz=200)
        scores, mult, dest, reasons = values([d, w], [10, 20], dict(id="s", clock_mhz=200), "linear_clock_scaling")
        self.assertEqual(scores, [20, 20])
        self.assertEqual(reasons, [])
        self.assertEqual(dest["id"], "s")
        self.assertIn("clock_conflict", values([d, w], [10, 20], dict(clock_mhz=200), "unknown_allowed")[3])

    def test_heldout_only_training_and_matched_baselines(self):
        pattern = "+".join(f"{f}:{m}" for f, m in PATTERNS[0])
        rows = [
            dict(
                pattern=pattern,
                target="SPECrate_int92",
                scenario="unknown_allowed",
                included=True,
                model_key=k,
                first=4,
                second=9,
                y=y,
                spec_id=k,
                first_id=k + "a",
                second_id=k + "b",
            )
            for k, y in [("a", 6), ("b", 12), ("c", 24)]
        ]
        summary, folds, pred = analyze(rows, 100, 3)
        f = next(f for f in folds if f["heldout_model"] == "a" and f["predictor"] == "equal_weight")
        self.assertAlmostEqual(f["factor"], (2 * 4) ** 0.5)
        rows[0]["y"] = 6000
        _, changed, _ = analyze(rows, 100, 3)
        self.assertEqual(
            f["factor"], next(x["factor"] for x in changed if x["heldout_model"] == "a" and x["predictor"] == "equal_weight")
        )
        self.assertEqual(len(pred), 9)
        selected = [r for r in summary if r["models"]]
        self.assertEqual([(r["models"], r["pairs"]) for r in selected], [(3, 3)] * 3)

    def test_version_pair_requires_both_on_same_record(self):
        common = dict(benchmark="Dhrystone", system="system", source_url="fixture", locator="line1", raw_record="raw")
        rows, stats = version_audit(
            {
                "a": dict(common, id="a", metrics_raw={"v1.1_DMIPS": "20", "v2.1_DMIPS": "10"}),
                "b": dict(common, id="b", metrics_raw={"v1.1_DMIPS": "100"}),
            }
        )
        self.assertEqual(stats["paired_source_rows"], 1)
        self.assertEqual(stats["median"], 2)
