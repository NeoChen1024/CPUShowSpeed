"""Fit arithmetic, selection contracts and independent PDF column examples."""

import unittest

from cpushowspeed.classic_fit import SCENARIOS, fit, linpack_n100, pair_rows


class ClassicFitTests(unittest.TestCase):
    def test_constant_factor_and_repeated_model(self):
        rows = [dict(model_key=k, x=x, y_vaxen=3 * x) for k, x in [("a", 1), ("b", 10), ("c", 100)]]
        result = fit(rows + [rows[0]] * 50, 200, 7)
        self.assertAlmostEqual(result["factor"], 3)
        self.assertAlmostEqual(result["factor_ci95_low"], 3)
        self.assertAlmostEqual(result["loo_model_p95_percent"], 0)
        self.assertAlmostEqual(result["loglog_slope_diagnostic"], 1)
        self.assertEqual(result["pairs"], 53)
        self.assertEqual(result["models"], 3)
        self.assertEqual(result, fit(rows + [rows[0]] * 50, 200, 7))

    def test_model_balance_and_insufficient_models(self):
        a = dict(model_key="a", x=1, y_vaxen=1)
        b = dict(model_key="b", x=1, y_vaxen=4)
        self.assertAlmostEqual(fit([a] * 100 + [b], 200, 7)["factor"], 2)
        self.assertNotIn("factor", fit([a] * 100, 200, 7))

    def test_linpack_page32_published_example_and_blank_column(self):
        header = "                                                                       n=100                “Theoritical"
        measured = "DEC 3000-900 (1 proc) 3.64 ns         3.6 -O5 -fast                      52       193           275"
        blank = "Convex SPP-1000(15 procs)100MHz                                                   965           3000"
        for raw, expected in [(measured, 52), (blank, None)]:
            record = dict(id="fixture", locator="pdf:page:1:line:2", raw_record=raw)
            self.assertEqual(linpack_n100(record, [header + "\n" + raw]), expected)

    def test_selection_preserves_conflicts_and_repeated_pairs(self):
        c = dict(benchmark="Dhrystone", metrics_raw={"v1.1_DMIPS": "10"}, source_blake3="hash", raw_record="source")
        s = dict(cpu_count=1, metrics_raw={"SPECrate_int92": "100"}, raw_record={})
        p = dict(classic_id="c", spec_id="s", spec_cohort="SPEC92 Netlib", clock_check="compatible_1pct", model_key="model")
        rows = pair_rows([p, p], {"c": c}, {"s": s}, [])
        self.assertEqual(sum(r["included"] for r in rows), 4)
        self.assertEqual(sum(r["included"] for r in rows if r["scenario"] == SCENARIOS[0]), 2)
        p["clock_check"] = "conflict"
        self.assertFalse(any(r["included"] for r in pair_rows([p], {"c": c}, {"s": s}, [])))
        p["clock_check"] = "compatible_1pct"
        s["cpu_count"] = 2
        self.assertFalse(any(r["included"] for r in pair_rows([p], {"c": c}, {"s": s}, [])))
