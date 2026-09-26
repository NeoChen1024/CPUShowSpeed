"""Scoped OCR and caption progress must follow published DocIR, not pool-wide assets."""

import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from cpushowspeed.document_report import (
    _percent,
    collect_caption_stats,
    collect_ocr_stats,
    print_document_report,
)
from cpushowspeed.documents import _connect
from cpushowspeed.ocr import _init_state, _select_inventory


class DocumentReportTests(unittest.TestCase):
    def test_partial_progress_never_displays_as_complete(self):
        self.assertEqual(_percent(2212, 2213), "99.9%")
        self.assertEqual(_percent(2213, 2213), "100.0%")
        self.assertEqual(_percent(84, 2213), "3.7%")
        self.assertEqual(_percent(295, 6_346_386), "0.0046%")

    def test_selected_ocr_and_caption_denominators(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "pdf"
            source.mkdir()
            output = base / "ocr"
            with _connect(base / "inventory.sqlite", source) as inventory:
                _init_state(inventory)
                inventory.execute("INSERT INTO ocr_runs VALUES ('run', ?, '{}', 'now')", (str(output),))
                for relative, pages in [("a.pdf", 2), ("b.pdf", 3), ("c.pdf", 4)]:
                    inventory.execute(
                        "INSERT INTO files (relative_path,size_bytes,mtime_ns,ctime_ns,blake3,pages,status,seen_run) "
                        "VALUES (?,100,0,0,?,?,'ok','test')",
                        (relative, f"hash-{relative}", pages),
                    )
                    status = "active" if relative == "b.pdf" else "published"
                    completed = 1 if relative == "b.pdf" else pages
                    inventory.execute(
                        "INSERT INTO ocr_documents (run_id,relative_path,source_blake3,source_pages,started_at,status,"
                        "completed_pages,updated_at) VALUES ('run',?,?,?,'now',?,?,'now')",
                        (relative, f"hash-{relative}", pages, status, completed),
                    )
                selected_list = base / "selected.txt"
                selected_list.write_text("b.pdf\na.pdf\n", encoding="utf-8")
                selected = _select_inventory(inventory, source, selected_list, "", None)
                self.assertEqual([row["relative_path"] for row in selected], ["b.pdf", "a.pdf"])

                for relative, pages in [("a.pdf", 2), ("c.pdf", 4)]:
                    (output / relative.replace(".pdf", ".raw.jsonl")).parent.mkdir(parents=True, exist_ok=True)
                    (output / relative.replace(".pdf", ".raw.jsonl")).write_text("header\n", encoding="utf-8")
                    blocks = (
                        [
                            {"source_label": "Image", "image_blake3": "a"},
                            {"source_label": "Figure", "image_blake3": "a"},
                            {"source_label": "Diagram", "kind": "diagram", "diagram": {"code": "graph TD"}, "image_blake3": "b"},
                            {"source_label": "Image", "image_blake3": "c"},
                            {"source_label": "Image", "image_blake3": "d"},
                        ]
                        if relative == "a.pdf"
                        else [{"source_label": "Image", "image_blake3": "other"}]
                    )
                    with (output / relative.replace(".pdf", ".docir.jsonl")).open("w", encoding="utf-8") as stream:
                        for page in range(1, pages + 1):
                            stream.write(json.dumps({"page": page, "blocks": blocks if page == 1 else []}) + "\n")

                stats = collect_ocr_stats(inventory, "run", output, selected)
                self.assertEqual((stats.target_documents, stats.target_pages), (2, 5))
                self.assertEqual((stats.published_documents, stats.published_pages), (1, 2))
                self.assertEqual((stats.staged_pages, stats.completed_pages), (1, 3))
                self.assertEqual(stats.statuses["active"], 1)
                self.assertEqual(len(stats.published), 1)

                catalog = base / "catalog.sqlite"
                with sqlite3.connect(catalog) as captions:
                    captions.execute("CREATE TABLE images (blake3 TEXT PRIMARY KEY)")
                    for digest in ["a", "b", "c", "d", "other"]:
                        captions.execute("INSERT INTO images VALUES (?)", (digest,))
                uninitialized = collect_caption_stats(catalog, stats.published)
                self.assertEqual(uninitialized.images, 5)
                self.assertFalse(uninitialized.initialized)
                without_caption = io.StringIO()
                with redirect_stdout(without_caption):
                    print_document_report(inventory, base / "inventory.sqlite", output, selected_list, False, None)
                self.assertNotIn("Image captioning", without_caption.getvalue())
                with_caption = io.StringIO()
                with redirect_stdout(with_caption):
                    print_document_report(inventory, base / "inventory.sqlite", output, selected_list, False, catalog)
                self.assertIn("Image captioning", with_caption.getvalue())
                self.assertIn("not started", with_caption.getvalue())
                with sqlite3.connect(catalog) as captions:
                    captions.execute("CREATE TABLE captions (image_blake3 TEXT PRIMARY KEY, caption TEXT, last_error TEXT)")
                    captions.executemany(
                        "INSERT INTO captions VALUES (?,?,?)",
                        [("a", "caption", None), ("c", None, "request failed"), ("other", "unrelated", None)],
                    )
                caption_stats = collect_caption_stats(catalog, stats.published)
                self.assertEqual(caption_stats.images, 5)
                self.assertEqual(
                    (caption_stats.captioned, caption_stats.skipped, caption_stats.failed, caption_stats.pending),
                    (2, 1, 1, 1),
                )
                self.assertEqual(caption_stats.processed, 3)
                all_selected = _select_inventory(inventory, source, None, "", None)
                all_stats = collect_ocr_stats(inventory, "run", output, all_selected)
                self.assertEqual((all_stats.target_documents, all_stats.target_pages), (3, 9))
                self.assertEqual((all_stats.published_documents, all_stats.published_pages), (2, 6))
                all_captions = collect_caption_stats(catalog, all_stats.published)
                self.assertEqual(all_captions.images, 6)
                self.assertEqual(all_captions.captioned, 3)

                inventory.execute("UPDATE files SET blake3 = 'changed' WHERE relative_path = 'b.pdf'")
                selected = _select_inventory(inventory, source, selected_list, "", None)
                stale = collect_ocr_stats(inventory, "run", output, selected)
                self.assertEqual(stale.stale_sources, 1)
                self.assertEqual(stale.completed_pages, 2)


if __name__ == "__main__":
    unittest.main()
