import itertools
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
from cpushowspeed.classic_predict import (
    OPTIONS,
    predict_scores,
    write_prediction_manifest,
)
from cpushowspeed.research_io import write_csv


class PredictionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.metrics = sorted(m for m, u in OPTIONS.values())
        self.coefficients = {m: float(2 ** (i + 1)) for i, m in enumerate(self.metrics)}
        self.exponent = 0.8
        t = np.linspace(-0.3, 0.3, 300)
        columns = [math.log(self.coefficients[m]) + (t if m.startswith("Dhrystone") else -t) for m in self.metrics]
        self.draws = np.array(columns).T
        np.savez_compressed(
            self.root / "coefficient-log-draws.npz",
            linear_clock__with_spec89__intercept=self.draws,
            linear_clock__with_spec89__exponent=np.full_like(self.draws, self.exponent),
        )
        rows = [
            dict(
                scenario="linear_clock",
                cohort="with_spec89",
                metric=m,
                exponent=self.exponent,
                vaxen_at_unit_score=self.coefficients[m],
                valid_bootstrap_draws=300,
                score_unit=next(u for metric, u in OPTIONS.values() if metric == m),
            )
            for m in self.metrics
        ]
        write_csv(self.root / "coefficients.csv", rows)
        write_prediction_manifest(self.root, [dict(scenario="linear_clock", cohort="with_spec89", calibrated_metrics=self.metrics)])

    def test_every_nonempty_subset_and_speed_unit(self):
        for n in range(1, 7):
            for subset in itertools.combinations(self.metrics, n):
                r = predict_scores({m: 1.0 for m in subset}, self.root)
                self.assertEqual((r["target_metric"], r["unit"]), ("SPECint92", "speed-VAXen"))
                self.assertAlmostEqual(sum(c["weight"] for c in r["components"]), 1)
                self.assertEqual(len(r["components"]), n)

    def test_variants_share_family_weight(self):
        keys = ["Dhrystone:v1.1_DMIPS", "Dhrystone:v2.1_DMIPS", "LINPACK:n100_MFLOPS"]
        r = predict_scores(dict.fromkeys(keys, 1), self.root)
        w = {c["metric"]: c["weight"] for c in r["components"]}
        self.assertEqual(w, dict(zip(keys, [0.25, 0.25, 0.5])))
        expected = (self.coefficients[keys[0]] * self.coefficients[keys[1]]) ** 0.25 * self.coefficients[keys[2]] ** 0.5
        self.assertAlmostEqual(r["vaxen"], expected)

    def test_power_law_in_the_score(self):
        metric = self.metrics[0]
        r = predict_scores({metric: 4.0}, self.root)
        self.assertAlmostEqual(r["vaxen"], self.coefficients[metric] * 4**self.exponent)
        self.assertEqual(r["components"][0]["exponent"], self.exponent)

    def test_opposite_correlated_draws_cancel(self):
        keys = ["Dhrystone:v1.1_DMIPS", "LINPACK:n100_MFLOPS"]
        r = predict_scores(dict.fromkeys(keys, 1), self.root)
        expected = math.sqrt(self.coefficients[keys[0]] * self.coefficients[keys[1]])
        self.assertAlmostEqual(r["vaxen_ci95"]["low"], expected)
        self.assertAlmostEqual(r["vaxen_ci95"]["high"], expected)

    def test_invalid_inputs_and_stale_bundle(self):
        for value in [0, -1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                predict_scores({self.metrics[0]: value}, self.root)
        with self.assertRaises(ValueError):
            predict_scores({}, self.root)
        with self.assertRaises(ValueError):
            predict_scores({"unknown": 1}, self.root)
        with (self.root / "coefficients.csv").open("a") as f:
            f.write("\n")
        with self.assertRaisesRegex(ValueError, "changed"):
            predict_scores({self.metrics[0]: 1}, self.root)
