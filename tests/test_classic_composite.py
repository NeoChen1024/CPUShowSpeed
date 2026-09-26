"""Composite candidates must be mutually compatible, not only match SPEC."""

import unittest
from unittest.mock import patch

from cpushowspeed.classic_composite import audit, clock_status


class CompositeTests(unittest.TestCase):
    def test_cross_source_clock_conflict(self):
        self.assertEqual(clock_status([{"clock_mhz": 182}, {"clock_mhz": 200}, {"clock_mhz": None}]), "conflict")
        self.assertEqual(clock_status([{"clock_mhz": 200}, {"clock_mhz": None}]), "unknown")
        self.assertEqual(clock_status([{"clock_mhz": 200}, {"clock_mhz": 199}]), "known")

    def records(self):
        records = {}
        for cid, family, metrics in [
            ("d", "Dhrystone", {"v1.1_DMIPS": "10"}),
            ("w", "Whetstone", {"MWIPS": "20", "MWIPS_DP": "15"}),
            ("l", "LINPACK", {}),
        ]:
            records[cid] = dict(
                id=cid, benchmark=family, metrics_raw=metrics, source_url="fixture", raw_record="fixture", clock_mhz=100
            )
        specs = {
            "s": dict(
                id="s", system="fixture", metrics_raw={"SPECmark89": "30"}, source_url="fixture", raw_record={}, clock_mhz=None
            )
        }
        pairs = [dict(spec_id="s", classic_id=cid, model_key="fixture") for cid in records]
        return records, specs, pairs

    @patch("cpushowspeed.classic_composite.linpack_n100", return_value=5)
    def test_no_cartesian_independence_and_reference_exclusion(self, _):
        records, specs, pairs = self.records()
        _, vectors, summaries = audit(records, specs, pairs + [pairs[0]], [])
        self.assertEqual(len(vectors), 2)  # Native and DP, not a duplicated source record.
        self.assertTrue(all(v["candidate_unknown_clock_allowed"] for v in vectors))
        self.assertFalse(any(v["candidate_known_clocks"] for v in vectors))
        specs["s"]["raw_record"] = {"measurement_type": "reference_definition"}
        _, vectors, _ = audit(records, specs, pairs, [])
        self.assertFalse(any(v["candidate_unknown_clock_allowed"] for v in vectors))
        self.assertIn("reference_definition_not_independent_measurement", vectors[0]["exclusion_reasons"])

    @patch("cpushowspeed.classic_composite.linpack_n100", return_value=5)
    def test_missing_metric_and_conflicting_constituents(self, _):
        records, specs, pairs = self.records()
        records["d"]["clock_mhz"] = 120
        _, vectors, _ = audit(records, specs, pairs, [])
        self.assertFalse(any(v["candidate_unknown_clock_allowed"] for v in vectors))
        self.assertTrue(all(v["candidate_linear_clock_scaling"] for v in vectors))
        self.assertAlmostEqual(vectors[0]["dhrystone_adjusted"], 10 * 100 / 120)
        self.assertEqual(vectors[0]["dhrystone"], 10)
        self.assertEqual(vectors[0]["normalization_clock_source"], "l")
        records["d"]["metrics_raw"] = {"v2.1_DMIPS": "10"}
        coverage, vectors, _ = audit(records, specs, pairs, [])
        self.assertEqual(vectors, [])
        self.assertFalse(any(r["complete_score_vector"] for r in coverage))
