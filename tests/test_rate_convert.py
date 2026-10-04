"""The rate converter used by the timeline must preserve score scaling and reject stale CI snapshots."""

import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from cpushowspeed.spec.rate_convert import convert_rate


class RateConvertTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.chain = self.root / "integer-rate-cpu92-vaxen-chain.csv"
        self.chain.write_text("generation,mode,scenario,vaxen_per_rate_score\ncpu2017,base,same_os,2\n")
        self.row = {
            "generation": "cpu2017",
            "mode": "base",
            "scenario": "same_os",
            "vaxen_per_rate_score": 2,
            "bootstrap_95_low": 1.5,
            "bootstrap_95_high": 2.5,
            "confidence_level": 0.95,
            "scope": "conditional_chain_mean_scale_pointwise_ci",
            "method_version": "test",
            "factor_chain_sha256": hashlib.sha256(self.chain.read_bytes()).hexdigest(),
        }
        self.write_intervals([self.row])

    def write_intervals(self, rows):
        with (self.root / "integer-rate-chain-intervals.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.row))
            writer.writeheader()
            writer.writerows(rows)

    def convert(self, score=10, generation="cpu2017"):
        return convert_rate(generation, "base", score, "same_os", self.root)

    def test_score_and_ci_use_same_scalar(self):
        value = self.convert()
        self.assertEqual(value["vaxen"], 20)
        self.assertEqual(value["ci95"], {"low": 15, "high": 25})
        self.assertEqual(value["reported_score"], 10)

    def test_invalid_score_and_generation(self):
        for score in (0, -1, float("nan"), float("inf"), 1e308):
            with self.assertRaises(ValueError):
                self.convert(score)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            self.convert(generation="cpu2018")

    def test_stale_and_duplicate_tables(self):
        self.chain.write_text(self.chain.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "stale"):
            self.convert()
        self.chain.write_text(self.chain.read_text().rstrip("\n") + "\n")
        self.write_intervals([self.row, self.row])
        with self.assertRaisesRegex(ValueError, "exactly one"):
            self.convert()

    def test_factor_disagreement(self):
        self.write_intervals([{**self.row, "vaxen_per_rate_score": 3}])
        with self.assertRaisesRegex(ValueError, "differs"):
            self.convert()


if __name__ == "__main__":
    unittest.main()
