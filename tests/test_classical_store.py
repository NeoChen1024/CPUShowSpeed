"""Classical results pair with SPEC targets only over resolved systems, with explicit clock policy."""

import unittest

from classical_fixture import result
from cpushowspeed.classical_store import pair, pairings, target_value

D, L = "Dhrystone:v1.1_DMIPS", "LINPACK:n100_MFLOPS"


class PairingTests(unittest.TestCase):
    def test_same_result_and_same_system_only(self):
        dec = result("dec", "sys:a", {D: 10, "SPECrate_int92": 20}, scope="reviewed-vector:dec")
        other = result("c1", "sys:a", {D: 12})
        stranger = result("c2", "sys:b", {D: 99})
        unresolved = result("c3", "", {D: 99})
        rows = [dec, other, stranger, unresolved]
        found = {(p["target"].result_id, p["classical"].result_id): p["status"] for p in pairings(rows)}
        self.assertEqual(found, {("dec", "dec"): "same_result", ("dec", "c1"): "clock_unknown"})

    def test_clock_conflict_is_excluded_without_scaling(self):
        target = result("t", "sys:a", {"SPECint92": 20}, clock=50, entity="cpu:x")
        c = result("c", "sys:a", {D: 10, L: 2}, clock=25, entity="cpu:x")
        self.assertEqual(pair(c, target, False), ({}, "clock_conflict"))
        self.assertEqual(pair(result("c", "sys:a", {D: 10}, clock=50.4), target, False)[1], "clock_compatible")

    def test_scaling_needs_one_processor_and_never_scales_linpack(self):
        target = result("t", "sys:a", {"SPECint92": 20}, clock=50, entity="cpu:x")
        c = result("c", "sys:a", {D: 10, L: 2}, clock=25, entity="cpu:x")
        self.assertEqual(pair(c, target, True), ({D: 20}, "linear_clock_scaled"))
        upgraded = result("u", "sys:a", {D: 10}, clock=25, entity="cpu:y")
        self.assertEqual(pair(upgraded, target, True), ({}, "clock_conflict_processor_unverified"))
        only_linpack = result("l", "sys:a", {L: 2}, clock=25, entity="cpu:x")
        self.assertEqual(pair(only_linpack, target, True), ({}, "clock_conflict"))

    def test_multiprocessor_classical_and_reference_targets_are_rejected(self):
        target = result("t", "sys:a", {"SPECint92": 20})
        self.assertEqual(pair(result("c", "sys:a", {D: 10}, cpus=2), target, False)[1], "classical_cpu_count_not_one")
        reference = result("r", "sys:a", {"SPECint89": 1}, reference=True)
        self.assertEqual(pair(result("c", "sys:a", {D: 10}), reference, False)[1], "reference_definition")

    def test_rate_needs_one_cpu_when_the_count_is_reported(self):
        self.assertIsNone(target_value(result("t", "s", {"SPECrate_int92": 9}, cpus=2), "SPECrate_int92"))
        self.assertEqual(target_value(result("t", "s", {"SPECrate_int92": 9}), "SPECrate_int92"), 9)
        self.assertEqual(target_value(result("t", "s", {"SPECint92": 9}, cpus=2), "SPECint92"), 9)


if __name__ == "__main__":
    unittest.main()
