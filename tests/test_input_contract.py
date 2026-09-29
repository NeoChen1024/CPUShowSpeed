import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cpushowspeed.benchmark_records import observation, read_jsonl, write_jsonl
from cpushowspeed.execution_policy import agreement
from cpushowspeed.spec_overlap import Result, _pair


def result(copies, peak=None, track="rate"):
    modes = {
        m: dict(status="reported", quantity="copies" if track == "rate" else "threads", minimum=n, maximum=n)
        for m, n in (("base", copies), ("peak", peak or copies))
    }
    return Result(
        "cpu2017",
        "id",
        "system",
        "system",
        "CPU",
        "cpu",
        1,
        8,
        2,
        1000,
        1024,
        "OS",
        "CC",
        10,
        9,
        "https://example/result",
        "hash",
        track=track,
        execution=dict(modes=modes),
    )


class InputContractTests(unittest.TestCase):
    def test_conflict_is_mode_specific_and_preserves_scores_and_ratio(self):
        a, b = result(8, 1), result(1)
        p = _pair(a, b, "hardware_near")
        self.assertEqual(p["base_execution_status"], "confirmed_count_conflict")
        self.assertEqual(p["base_ratio"], "")
        self.assertEqual(p["base_unfiltered_ratio"], 1)
        self.assertEqual(p["old_base"], 9)
        self.assertEqual(p["peak_ratio"], 1)

    def test_unknown_nonuniform_and_different_quantities_are_not_assumed_equal(self):
        a = result(8)
        self.assertEqual(agreement(a, replace(a, execution={}), "base"), "unverified")
        b = result(8)
        b.execution["modes"]["base"]["minimum"] = 1
        self.assertEqual(agreement(a, b, "base"), "nonuniform_requires_review")
        self.assertEqual(agreement(a, result(8, track="speed"), "base"), "different_or_unspecified_track")

    def test_shared_contract_roundtrip_and_validation(self):
        r = observation(
            "id",
            "Dhrystone:v1.1_DMIPS",
            1,
            unit="DMIPS",
            track="classical",
            mode="reported",
            system="VAX",
            source=dict(url="https://example"),
        )
        self.assertIsNone(r["execution"]["observed_worker_count"])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "records.jsonl"
            write_jsonl(p, [r])
            self.assertEqual(list(read_jsonl(p)), [r])
            with self.assertRaises(ValueError):
                write_jsonl(p, [r, r])
        with self.assertRaises(ValueError):
            observation(
                "id", "metric", float("inf"), unit="u", track="speed", mode="base", system="s", source=dict(url="https://example")
            )
