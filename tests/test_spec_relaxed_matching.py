"""Relaxed predictors retain resource/clock boundaries and explicit evidence tiers."""

import unittest
from dataclasses import replace

from cpushowspeed.spec_joint_tracks import ELIGIBLE_MATCH_TIERS, match, triangles
from cpushowspeed.spec_overlap import Result, _normalized


def machine(generation, rid, name="AlphaServer GS160 6/731", **kwargs):
    return replace(
        Result(
            generation,
            rid,
            name,
            _normalized(name),
            "Alpha 21264A",
            "21264a",
            1,
            1,
            1,
            731,
            4096,
            "OS",
            "CC",
            10,
            9,
            "url/" + rid,
            "hash",
        ),
        **kwargs,
    )


class RelaxedMatchTests(unittest.TestCase):
    def test_ram_and_lexical_alias_admitted_with_qualification(self):
        a = machine("cpu95", "a")
        b = machine("cpu2000", "b", "AlphaServer GS160 Model 6/731", memory_mib=8192)
        self.assertFalse(match([a], [b]))
        r = match([a], [b], "ram-aliases")[0]
        self.assertEqual(r["match_tier"], "platform_alias_ram_relaxed")
        self.assertIn("memory_mismatch", r["matching_blockers"])
        self.assertEqual(r["old_memory_mib"], 4096)
        self.assertEqual(r["new_memory_mib"], 8192)

    def test_cross_platform_requires_its_own_scenario(self):
        a = machine("cpu95", "a")
        b = machine("cpu2000", "b", "AlphaServer GS320 Model 6/731")
        c = machine("cpu2000", "c", "AlphaServer GS80 Model 6/731")
        self.assertFalse(triangles([a], [b], [c], "ram-aliases")[0])
        rows, _, pairs, _ = triangles([a], [b], [c], "cpu-clock")
        self.assertEqual(len(rows), 2)
        self.assertIn("unresolved_system", rows[0]["relaxed_fields"])
        self.assertEqual(pairs[0]["match_tier"], "cpu_clock_resources")

    def test_loose_policies_do_not_scale_or_merge_resources(self):
        a = machine("cpu95", "a")
        for policy in ("ram-aliases", "cpu-clock"):
            for b in (
                machine("cpu2000", "b", chips=2, cores=2),
                machine("cpu2000", "b", clock_mhz=800),
                machine("cpu2000", "b", processor_key="21264"),
            ):
                self.assertFalse(any(p["match_tier"] in ELIGIBLE_MATCH_TIERS for p in match([a], [b], policy)))

    def test_processor_alias_preserves_fold_identity(self):
        a = machine("cpu95", "a", "SGI 2200", processor_key="mipsr12000")
        b = machine("cpu2000", "b", "SGI 2200", processor_key="r12000")
        c = machine("cpu2000", "c", "SGI 2200", processor_key="r12000")
        rows, _, _, _ = triangles([a], [b], [c], "ram-aliases")
        self.assertEqual({r["model_key"] for r in rows}, {"r12000"})
