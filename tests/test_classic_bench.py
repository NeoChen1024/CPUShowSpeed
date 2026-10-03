import json
import unittest

from click.testing import CliRunner
from cpushowspeed.classic_bench import ISSUE_BODY_LIMIT, bench, issue_title, render_issue


def result(benchmark="dhrystone-2.1", valid=True, copies=1):
    return {
        "benchmark": benchmark,
        "copies": copies,
        "family": "Dhrystone",
        "unit": "DMIPS",
        "precision": None,
        "variant": "2.1",
        "start_utc": "2026-10-03T00:00:00Z",
        "end_utc": "2026-10-03T00:00:12Z",
        "valid": valid,
        "errors": [] if valid else ["copy 0: result check failed"],
        "aggregate_score": 30101.0 * copies,
        "per_copy": [],
        "intervals": {"length_s": 1.0, "complete": 10, "median": 30228.0, "minimum": 29796.0, "maximum": 30287.0},
        "frequency": {"cpus": [0], "samples": 11, "mean_mhz": 4042.0},
    }


def document(profile="reference", copies=(1,), pinned=True, results=None):
    return {
        "schema": "classic-bench-v1",
        "tool": {
            "name": "classic-bench",
            "version": "0.1.0",
            "build": {
                "c_compiler": "GNU",
                "c_compiler_version": "16.2.1",
                "kernel_c_flags": "-O2" if profile == "reference" else "-O3 -march=native",
                "kernel_c_dialect": "gnu89",
                "profile": profile,
            },
        },
        "host": {"os": "Linux", "release": "7.2", "machine": "x86_64", "cpu_model": "Test CPU", "logical_cpus": 16},
        "settings": {
            "copies": list(copies),
            "pinned": pinned,
            "cpus": list(range(max(copies))) if pinned else None,
            "duration_s": 10.0,
            "warmup_s": 2.0,
            "interval_s": 1.0,
        },
        "results": results if results is not None else [result(copies=n) for n in copies],
    }


class RenderIssueTests(unittest.TestCase):
    def test_reference_run_embeds_json_without_warnings(self):
        doc = document()
        body, embedded = render_issue(doc, "run.json")
        self.assertTrue(embedded)
        self.assertIn("| `dhrystone-2.1` | 1 | DMIPS | 30,101 | 30,228 | 29,796 | 30,287 | 4,042 | passed |", body)
        self.assertNotIn("## Warnings", body)
        payload = body.split("```json\n", 1)[1].split("\n```", 1)[0]
        self.assertEqual(json.loads(payload), doc)

    def test_warnings_for_custom_profile_copies_unpinned_and_invalid(self):
        doc = document(profile="custom", copies=(1, 4), pinned=False, results=[result(), result(valid=False, copies=4)])
        body, _ = render_issue(doc, "run.json")
        warnings = body.split("## Warnings", 1)[1]
        self.assertIn("Custom build profile (`-O3 -march=native`)", warnings)
        self.assertIn("Results with copies = 4 are throughput results", warnings)
        self.assertIn("not pinned", warnings)
        self.assertIn("`dhrystone-2.1` with copies = 4 is invalid: copy 0: result check failed.", warnings)
        self.assertIn("| `dhrystone-2.1` | 4 | DMIPS | 120,404 |", body)
        self.assertIn("**failed**", body)

    def test_oversized_json_is_left_for_attachment(self):
        doc = document()
        body, embedded = render_issue(doc, "run.json", limit=500)
        self.assertFalse(embedded)
        self.assertNotIn("```json", body)
        self.assertIn("`run.json.gz` is attached instead", body)
        self.assertLess(len(body), ISSUE_BODY_LIMIT)

    def test_title(self):
        self.assertEqual(issue_title(document(copies=(1, 16))), "[classic-bench] Test CPU, GNU 16.2.1, copies=1,16")


class ReportCommandTests(unittest.TestCase):
    def test_rejects_other_schema(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("x.json", "w") as f:
                json.dump({"schema": "other"}, f)
            out = runner.invoke(bench, ["report", "x.json"])
        self.assertEqual(out.exit_code, 1)
        self.assertIn("expected schema classic-bench-v1", out.output)


if __name__ == "__main__":
    unittest.main()
