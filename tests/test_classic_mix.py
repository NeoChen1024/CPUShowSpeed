import json
import unittest
from pathlib import Path

from cpushowspeed.classic_mix import SOURCE, weights


class MixDefinitionTests(unittest.TestCase):
    @unittest.skipUnless(SOURCE.exists(), "Local instruction-mix source unavailable")
    def test_source_definitions_remain_distinct(self):
        source = json.loads(SOURCE.read_text())
        rows = weights(source)
        for name, count in [("Gibson Mix", 12), ("ADP Mix", 7)]:
            subset = [r for r in rows if r["mix"] == name]
            self.assertEqual(len(subset), count)
            self.assertAlmostEqual(sum(r["weight"] for r in subset), 1)
        self.assertAlmostEqual(sum(r["weight"] for r in rows if r["mix"] == "Gibson Mix" and "Floating" in r["operation"]), 0.129)
        self.assertFalse(any("Floating" in r["operation"] for r in rows if r["mix"] == "ADP Mix"))
        broken = json.loads(json.dumps(source))
        broken["blocks"][0]["html"] = broken["blocks"][0]["html"].replace("0.330", "0.430")
        with self.assertRaises(ValueError):
            weights(broken)
