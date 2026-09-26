"""Atomic, repeatable caption materialization."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cpushowspeed.caption_backfill import backfill_document


class BackfillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "sample.docir.jsonl"
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE captions(image_blake3 TEXT, caption TEXT)")
        self.db.executemany("INSERT INTO captions VALUES (?, ?)", [("a", "New caption"), ("b", ""), ("c", None)])
        self.page = {
            "page": 1,
            "status": "ok",
            "blocks": [
                {"kind": "visual", "image_blake3": "a", "caption": "Old", "bbox_px": [1, 2, 3, 4]},
                {"kind": "visual", "image_blake3": "a", "caption": None},
                {"kind": "visual", "image_blake3": "b", "caption": None},
                {"kind": "visual", "image_blake3": "c", "caption": None},
                {"kind": "text", "markdown": "unchanged"},
            ],
        }
        self.path.write_text(json.dumps(self.page) + "\n")

    def test_only_matching_captions_change_and_second_run_does_not_rewrite(self):
        self.assertEqual(backfill_document(self.path, 1, self.db), (2, 2))
        result = json.loads(self.path.read_text())
        self.page["blocks"][0]["caption"] = self.page["blocks"][1]["caption"] = "New caption"
        self.assertEqual(result, self.page)
        before = self.path.stat()
        content = self.path.read_bytes()
        self.assertEqual(backfill_document(self.path, 1, self.db), (2, 0))
        self.assertEqual(self.path.stat().st_ino, before.st_ino)
        self.assertEqual(self.path.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(self.path.read_bytes(), content)

    def test_dry_run_keeps_original_bytes(self):
        original = self.path.read_bytes()
        self.assertEqual(backfill_document(self.path, 1, self.db, True), (2, 2))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob(".*.tmp")), [])

    def test_bad_later_page_preserves_whole_original_document(self):
        with self.path.open("a") as stream:
            stream.write("{broken json\n")
        original = self.path.read_bytes()
        with self.assertRaises(ValueError):
            backfill_document(self.path, 2, self.db)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob(".*.tmp")), [])

    def test_page_count_mismatch_preserves_original(self):
        original = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "expected 2 pages"):
            backfill_document(self.path, 2, self.db)
        self.assertEqual(self.path.read_bytes(), original)

    def test_interrupted_replace_preserves_original_and_removes_temporary(self):
        original = self.path.read_bytes()
        with patch("cpushowspeed.caption_backfill.os.replace", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                backfill_document(self.path, 1, self.db)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob(".*.tmp")), [])
