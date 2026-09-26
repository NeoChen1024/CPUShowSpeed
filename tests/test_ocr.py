"""Invariants for OCR page conversion and crash recovery."""

import io
import json
import tempfile
import unittest
from pathlib import Path

import blake3
from cpushowspeed.ocr import (
    PageETAColumn,
    _convert_page,
    _finalize,
    _read_stage,
    _record_page,
    _stage_path,
    _verify_final,
    _write_atomic,
)
from PIL import Image
from rich.console import Console
from rich.progress import Progress


class OCRTests(unittest.TestCase):
    def test_completed_resumed_progress_has_zero_eta(self):
        column = PageETAColumn()
        with Progress(column, auto_refresh=False, console=Console(file=io.StringIO())) as progress:
            progress.add_task("OCR", total=2, completed=2)
            self.assertEqual(column.render(progress.tasks[0]).plain, "0:00:00")

    def test_visual_and_table_keep_chunk_positions(self):
        raw = (
            '<div data-label="Text" data-bbox="0 0 200 100">Intro</div>'
            '<div data-label="Table" data-bbox="0 100 500 400">'
            "<table><tr><th>Name</th></tr><tr><td>A</td></tr></table></div>"
            '<div data-label="Image" data-bbox="100 400 600 900"><img alt="device"/></div>'
            '<div data-label="Diagram" data-bbox="600 400 900 900"><pre>graph TD\nA --> B</pre></div>'
        )
        image = Image.new("RGB", (1000, 1000), "white")
        encoded = io.BytesIO()
        image.save(encoded, format="PNG")
        with tempfile.TemporaryDirectory() as temporary:
            pool = Path(temporary)
            page, chunks, assets = _convert_page(raw, encoded.getvalue(), 1, pool)
            self.assertEqual(len(chunks), len(page["blocks"]))
            self.assertEqual([block["kind"] for block in page["blocks"]], ["text", "table", "visual", "diagram"])
            self.assertEqual(page["blocks"][1]["table"]["cells"][1]["text"], "A")
            self.assertNotIn("markdown", page["blocks"][1])
            self.assertEqual(page["blocks"][3]["diagram"]["format"], "mermaid")
            self.assertEqual(len(assets), 2)
            for asset in assets:
                data = (pool / asset["path"]).read_bytes()
                self.assertEqual(blake3.blake3(data).hexdigest(), asset["blake3"])

    def test_failed_page_is_not_resumed_as_completed_or_published(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = "a/b.pdf"
            identity = {"run_id": "run", "relative_path": relative, "source_blake3": "hash", "pages": 2}
            _write_atomic(_stage_path(root, relative), (json.dumps(identity) + "\n").encode())
            _record_page(root, relative, {"page": 1, "status": "ok"}, {"page": 1, "status": "ok", "blocks": []})
            _record_page(root, relative, {"page": 2, "status": "error"}, {"page": 2, "status": "error", "blocks": []})
            self.assertEqual(_read_stage(root, relative, "run", "hash", 2), {1})
            with self.assertRaises(ValueError):
                _finalize(
                    root,
                    relative,
                    {"type": "document", "run_id": "run", "source_pdf": relative, "source_blake3": "hash", "pages": 2},
                    2,
                )
            self.assertFalse((root / "a/b.docir.jsonl").exists())
            _record_page(root, relative, {"page": 2, "status": "ok"}, {"page": 2, "status": "blank", "blocks": []})
            self.assertEqual(_read_stage(root, relative, "run", "hash", 2), {1, 2})
            _finalize(
                root,
                relative,
                {"type": "document", "run_id": "run", "source_pdf": relative, "source_blake3": "hash", "pages": 2},
                2,
            )
            raw = [json.loads(line) for line in (root / "a/b.raw.jsonl").read_text().splitlines()]
            docir = [json.loads(line) for line in (root / "a/b.docir.jsonl").read_text().splitlines()]
            self.assertEqual([record["page"] for record in raw[1:]], [1, 2])
            self.assertEqual([record["status"] for record in docir], ["ok", "blank"])
            self.assertFalse(_stage_path(root, relative).exists())
            _verify_final(root / "a/b.raw.jsonl", root / "a/b.docir.jsonl", relative, "hash", 2, "run")
            with self.assertRaises(ValueError):
                _verify_final(root / "a/b.raw.jsonl", root / "a/b.docir.jsonl", relative, "wrong", 2, "run")


if __name__ == "__main__":
    unittest.main()
