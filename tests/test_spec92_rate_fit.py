"""Checks for the direct CPU92/CPU95 integer-rate bridge."""

import sqlite3
import unittest

from cpushowspeed.database.observation_store import result_pair_reviews
from cpushowspeed.spec.cpu92_rate_fit import VAX_RATE92_REFERENCE, _software_near, selected_pairs


class Cpu92RateFitTests(unittest.TestCase):
    def test_vax_throughput_reference(self):
        self.assertAlmostEqual(VAX_RATE92_REFERENCE, 23.71764705882353)
        self.assertAlmostEqual(1 / VAX_RATE92_REFERENCE, 25500 / 604800)

    def test_os_tier_is_not_hardware_tier(self):
        self.assertTrue(_software_near({"old_os": "UnixWare 2.0", "new_os": "UnixWare 2.0, SDK"}))
        self.assertTrue(_software_near({"old_os": "HP-UX B.10.01", "new_os": "HP-UX B.10.01"}))
        self.assertFalse(_software_near({"old_os": "HP-UX B.10.01", "new_os": "HP-UX B.10.20"}))

    def test_only_reviewed_accepted_pairs_are_fitted(self):
        def pair(decision, tier, os="UnixWare 2.0"):
            return {"review_decision": decision, "match_tier": tier, "old_os": os, "new_os": os}

        pairs = [
            pair("accept", "hardware_near"),
            pair("accept", "hardware_near", "HP-UX B.10.01"),
            pair("reject", "hardware_near"),
            pair("unreviewed", "hardware_near"),
            pair("accept", "name_only"),
        ]
        self.assertEqual(selected_pairs(pairs, "hardware_near"), [pairs[0], pairs[1], pairs[4]])
        self.assertEqual(selected_pairs(pairs, "same_os"), [pairs[0], pairs[1], pairs[4]])
        pairs[1]["new_os"] = "HP-UX B.10.20"
        self.assertEqual(selected_pairs(pairs, "same_os"), [pairs[0], pairs[4]])

    def test_result_pair_reviews_strip_prefixes_and_ignore_other_suites(self):
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE review_result (review_id, target_kind, side, field, decision, result_id)")
        rows = [
            ("rev:a", "result_pair", "left", None, "reject", "spec:cpu92:rate:x.html"),
            ("rev:a", "result_pair", "right", None, "reject", "spec:cpu95:rate:res9509/p1"),
            ("rev:b", "result_pair", "left", None, "accept", "spec:cpu92:speed:x.html"),
            ("rev:b", "result_pair", "right", None, "accept", "spec:cpu95:speed:res9509/p2"),
        ]
        db.executemany("INSERT INTO review_result VALUES (?, ?, ?, ?, ?, ?)", rows)
        self.assertEqual(
            result_pair_reviews(db, "spec:cpu92:rate:", "spec:cpu95:rate:"), {("x.html", "res9509/p1"): ("rev:a", "reject")}
        )


if __name__ == "__main__":
    unittest.main()
