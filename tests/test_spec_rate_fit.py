"""The rate fitter must keep rate submissions separate, pair over resolved identity and preserve its own scale."""

import json
import sqlite3
import unittest

from cpushowspeed.spec_rate_fit import GENERATIONS, _chain, _fit_edges, collect_rate


def _database(processors: dict[str, tuple]) -> sqlite3.Connection:
    """Three systems per suite; `processors` maps processor text to its resolution row."""
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE observation (result_id, mode, record, system_id, scope, track)")
    db.execute("CREATE TABLE processor_resolution (scope, text, clock_mhz, level, entity_id, reason, detail)")
    db.execute("CREATE TABLE processor_family (family_id, clock_variants_only)")
    db.execute("INSERT INTO processor_family VALUES ('fam:clocked', 1), ('fam:broad', 0)")
    for index, generation in enumerate(GENERATIONS):
        scope = f"spec:{generation}"
        for text, (level, entity, reason, detail) in processors.items():
            db.execute(
                "INSERT INTO processor_resolution VALUES (?, ?, 1000, ?, ?, ?, ?)", (scope, text, level, entity, reason, detail)
            )
        for cpu, text in enumerate(processors):
            for track, score in (("rate", 100 / 2**index), ("speed", 999999)):
                result_id = f"spec:{generation}:{track}:{cpu}"
                record = dict(
                    system=f"System {cpu}" if text != "Broad CPU" else f"System {cpu} {generation}",
                    hardware=dict(processor=text, nominal_mhz=1000, enabled_chips=1, enabled_cores=2, memory_mib=8192),
                    run=dict(os="OS", compiler="CC"),
                    execution={},
                    source=dict(url=f"https://www.spec.org/{generation}/{track}-{cpu}.html", sha256="0" * 64),
                    raw={},
                )
                for mode in ("base", "peak"):
                    row = (result_id, mode, json.dumps(dict(record, value=score)), f"sys:{cpu}", scope, track)
                    db.execute("INSERT INTO observation VALUES (?, ?, ?, ?, ?, ?)", row)
    return db


class RateFitTests(unittest.TestCase):
    def test_rate_only_and_separate_cpu95_relative_chain(self):
        db = _database(
            {
                "CPU A": ("sku", "sku:a", "", ""),
                "CPU B": ("family", "fam:x", "sku_not_in_catalog", "X 100"),
                "CPU C": ("family", "fam:clocked", "", ""),
            }
        )
        results = collect_rate(db)
        self.assertEqual({generation: len(rows) for generation, rows in results.items()}, {g: 3 for g in GENERATIONS})
        self.assertTrue(all(r.base != 999999 for rows in results.values() for r in rows))
        self.assertEqual(
            {r.processor_key: r.processor_basis for r in results["cpu95"]},
            {"sku:a": "sku", "fam:x#x 100": "uncatalogued_model", "fam:clocked": "clock_variants_only"},
        )
        pairs, edges = _fit_edges(results)
        self.assertEqual(len(pairs), 12)
        for edge in edges:
            self.assertAlmostEqual(edge["strict", "base"]["factor_old_per_new"], 2)
            self.assertEqual(edge["strict", "base"]["processor_configs"], 3)
        chain = _chain(edges, "strict", "base")
        self.assertEqual(chain["relative_to"], "CPU95 integer rate score")
        self.assertAlmostEqual(chain["factors"]["cpu2026"], 16)

    def test_broad_family_and_unresolved_processors_do_not_establish_hardware(self):
        db = _database(
            {
                "CPU A": ("sku", "sku:a", "", ""),
                "Broad CPU": ("family", "fam:broad", "", ""),
                "Mystery CPU": ("unresolved", None, "", ""),
            }
        )
        results = collect_rate(db)
        self.assertEqual({r.processor_basis for r in results["cpu95"]}, {"sku", "broad_family", "unresolved"})
        pairs, _ = _fit_edges(results)
        near = {row["processor_key"] for row in pairs if row["match_tier"] == "hardware_near"}
        self.assertEqual(near, {"sku:a"})
        self.assertNotIn("", {row["processor_key"] for row in pairs})


if __name__ == "__main__":
    unittest.main()
