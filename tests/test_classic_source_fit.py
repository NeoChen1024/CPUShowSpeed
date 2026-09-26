import math
import unittest

from cpushowspeed.classic_source_fit import calculate, os_key, pair_patterns, prepare


class SourceFitTests(unittest.TestCase):
    def test_pair_order_matches_legacy_and_precision_stays_separate(self):
        scores = {"LINPACK:n100_MFLOPS": 1, "Whetstone:MWIPS_DP": 2, "Whetstone:MWIPS_SP": 3, "Dhrystone:v1.1_DMIPS": 4}
        patterns = list(pair_patterns(scores))
        self.assertIn(("Whetstone:MWIPS_DP", "LINPACK:n100_MFLOPS"), patterns)
        self.assertNotIn(("Whetstone:MWIPS_DP", "Whetstone:MWIPS_SP"), patterns)
        self.assertEqual(os_key("OpenVMS 6.1"), "vms")
        self.assertIsNone(os_key(""))

    def test_source_column_no_invented_clock_and_os_rejection(self):
        v = dict(
            id="v",
            model_key="decmachine",
            machine="DEC machine",
            os="VMS",
            scores={"Dhrystone:v1.1_DMIPS": 4, "LINPACK:n100_MFLOPS": 9},
            targets={"SPECrate_int92": 100},
            observation_ids={"Dhrystone:v1.1_DMIPS": "d", "LINPACK:n100_MFLOPS": "l", "SPECrate_int92": "s"},
            qualification="unknown_cpu",
            source_url="fixture",
        )
        s = dict(
            id="archive",
            system="DEC machine",
            os_raw="OSF",
            cohort="SPEC92 rate Netlib",
            cpu_count=1,
            raw_record={},
            metrics_raw={"SPECrate_int92": 100},
            source_url="fixture",
        )
        rows, audit = prepare([v], [], [s])
        self.assertEqual(len(rows), 4)
        self.assertFalse(audit[0]["included"])
        self.assertIn("os_missing_or_conflict", audit[0]["exclusion_reasons"])
        self.assertTrue(all(r["first"] == 4 for r in rows))

    def test_whole_model_held_out_across_sources(self):
        rows = [
            dict(
                stage="within_source",
                target="t",
                pattern="p",
                model_key=m,
                first=4,
                second=9,
                y=y,
                origin=origin,
                spec_id=m + origin,
                first_id="a",
                second_id="b",
            )
            for m, y, origin in [("a", 6, "one"), ("a", 6, "two"), ("b", 12, "one"), ("c", 24, "one")]
        ]
        summary, folds, pred = calculate(rows, 100, 7)
        f = next(f for f in folds if f["predictor"] == "equal_weight" and f["heldout_model"] == "a")
        self.assertAlmostEqual(f["factor"], math.sqrt(8))
        self.assertEqual(f["training_models"], 2)
        self.assertTrue(all(s["models"] == 3 and s["pairs"] == 4 for s in summary))


class BootstrapEquivalenceTests(unittest.TestCase):
    def test_optimized_resampling_matches_reference(self):
        from cpushowspeed.classic_fit import fit as reference
        from cpushowspeed.classic_source_fit import fit

        rows = [dict(model_key=str(i), x=i + 1, y_vaxen=y) for i, y in enumerate([1, 4, 7, 10])]
        a, b = reference(rows, 500, 13), fit(rows, 500, 13)
        for key in ("factor", "factor_ci95_low", "factor_ci95_high", "loo_model_p95_percent"):
            self.assertAlmostEqual(a[key], b[key], places=12)
