import copy
import tempfile
import unittest
from pathlib import Path

from cpushowspeed.research_registry import render, validate


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        (self.root / "docs/guide.md").write_text("# Guide\n")
        self.registry = dict(
            tracks=[dict(id="track", path="docs/guide.md")],
            metrics=[dict(id="metric", title="Score", mode="rate", unit="points", status="recorded")],
            datasets=[dict(id="data", path="data/derived/missing.csv", optional=True, owner="docs/guide.md")],
            models=[
                dict(
                    id="fit",
                    track="track",
                    owner="docs/guide.md",
                    input_metrics=["metric"],
                    target_metric="metric",
                    dataset_ids=["data"],
                    depends_on=[],
                    outputs=[],
                    relationship="empirical-fit",
                    role="primary",
                    status="implemented-conditional",
                )
            ],
            documents=[dict(path="docs/guide.md", title="Guide", role="guide", status="current")],
        )

    def test_optional_derived_data_and_required_evidence(self):
        self.assertEqual(validate(self.registry, self.root), [])
        self.registry["datasets"][0]["optional"] = False
        self.assertTrue(any("missing required path" in e for e in validate(self.registry, self.root)))

    def test_cycle_and_unknown_metric(self):
        self.registry["models"][0]["depends_on"] = ["fit"]
        self.registry["models"][0]["target_metric"] = "absent"
        errors = validate(self.registry, self.root)
        self.assertTrue(any("cycle" in e for e in errors))
        self.assertTrue(any("unknown metric" in e for e in errors))

    def test_unregistered_document_and_escape(self):
        (self.root / "docs/new.md").write_text("# New")
        self.registry["datasets"][0]["path"] = "../outside"
        errors = validate(self.registry, self.root)
        self.assertTrue(any("unregistered document" in e for e in errors))
        self.assertTrue(any("escapes repository" in e for e in errors))

    def test_duplicate_ids_and_deterministic_render(self):
        self.registry["metrics"].append(copy.deepcopy(self.registry["metrics"][0]))
        self.assertTrue(any("duplicate metrics" in e for e in validate(self.registry, self.root)))
        self.assertEqual(render(self.registry), render(copy.deepcopy(self.registry)))
        self.assertIn("flowchart TD", render(self.registry))
