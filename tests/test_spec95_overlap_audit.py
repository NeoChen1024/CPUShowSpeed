"""Explain matching losses without silently admitting unsafe configurations."""

import unittest
from dataclasses import replace

from cpushowspeed.spec95_overlap_audit import (
    SCENARIOS,
    blockers,
    candidate_system_key,
    disclosure_fields,
)
from cpushowspeed.spec_overlap import Result, automatic_pairs, normalized


def machine(system="AlphaServer GS160 6/731", **kwargs):
    r = Result(
        "cpu95", "id", system, normalized(system), "Alpha 21264A", "21264a", 1, 1, 1, 731, 4096, "OS", "CC", 10, 9, "url", "hash"
    )
    return replace(r, **kwargs)


class OverlapAuditTests(unittest.TestCase):
    def test_ram_is_isolated_from_identity_and_clock(self):
        a, b = machine(), machine(memory_mib=8192)
        self.assertEqual(blockers(a, b), {"memory_mismatch"})
        self.assertTrue(blockers(a, b) <= SCENARIOS["memory_relaxed"])
        self.assertFalse(blockers(a, machine(memory_mib=8192, clock_mhz=800)) <= SCENARIOS["memory_and_candidate_aliases"])

    def test_lexical_model_alias_preserves_family_and_clock(self):
        a, b = machine(), machine("AlphaServer GS160 Model 6/731")
        self.assertEqual(blockers(a, b), {"system_name"})
        self.assertEqual(candidate_system_key(a), candidate_system_key(b))
        self.assertIn("unresolved_system", blockers(a, machine("AlphaServer GS320 Model 6/731")))
        self.assertNotEqual(
            candidate_system_key(machine("Compaq AlphaServer DS20", clock_mhz=500)),
            candidate_system_key(machine("AlphaServer DS20E Model 6/500", clock_mhz=500)),
        )

    def test_resources_are_not_alias_or_memory_relaxations(self):
        a, b = machine(), machine(chips=2, cores=2)
        self.assertEqual(blockers(a, b), {"chips", "cores"})
        self.assertFalse(blockers(a, b) <= SCENARIOS["memory_and_candidate_aliases"])
        self.assertTrue(blockers(a, b) <= SCENARIOS["ignore_resources_diagnostic"])

    def test_strict_flags_agree_with_existing_matcher(self):
        a = machine()
        for b in [
            machine(),
            machine(memory_mib=None),
            machine(clock_mhz=800),
            machine(cores=2),
            machine(enabled_threads_per_core=2),
        ]:
            pair = automatic_pairs({"a": [a], "b": [b]}, "a", "b")[0]
            self.assertEqual(not blockers(a, b), pair["match_tier"] == "hardware_near")

    def test_disclosure_fields_support_legacy_unclosed_cells(self):
        old = "<TABLE><TR><TH>CPU:<TD>731 MHz 21264A<TR><TH>Memory:<TD>4GB</TABLE>"
        new = "<TABLE><TR><TH>CPU(s) enabled:</TH><TD>1 core, 1 chip</TD></TR></TABLE>"
        self.assertEqual(disclosure_fields(old)["Memory:"], "4GB")
        self.assertEqual(disclosure_fields(old)["CPU:"], "731 MHz 21264A")
        self.assertEqual(disclosure_fields(new)["CPU(s) enabled:"], "1 core, 1 chip")
