"""Rich tables preserve real archival structures without silently repairing data."""

import copy
import json
import re
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from cpushowspeed.docir_rich_table import (
    convert_rich_table,
    render_table_block,
    validate_rich_table,
    walk_content,
)
from cpushowspeed.docir_table import TableConversionError, convert_html_table
from cpushowspeed.table_migrate import migrate_document


class RichTablesTests(unittest.TestCase):
    def test_real_nine_failures_and_roundtrip(self):
        cases = json.loads((Path(__file__).parent / "fixtures/honeywell-rich-tables.json").read_text())["cases"]
        self.assertEqual(len(cases), 9)
        for case in cases:
            with self.subTest(page=case["pdf_page"]):
                with self.assertRaises(TableConversionError):
                    convert_html_table(case["html"])
                b = convert_rich_table(case["html"])
                self.assertEqual(render_table_block(b), render_table_block(json.loads(json.dumps(b))))
                self.assertTrue(render_table_block(b))
                texts = [n["text"] for n in walk_content(b) if n.get("kind") == "text"]
                texts += [n["caption"] for n in walk_content(b) if n.get("kind") == "table" and n.get("caption")]
                original = Counter(re.findall(r"\w+", BeautifulSoup(case["html"], "html.parser").get_text(" ")))
                rebuilt = Counter(re.findall(r"\w+", BeautifulSoup(" ".join(texts), "html.parser").get_text(" ")))
                self.assertEqual(original, rebuilt)
        b = convert_rich_table(cases[0]["html"])
        self.assertEqual(len([n for n in walk_content(b) if n.get("kind") == "table"]), 2)
        rendered = render_table_block(b)
        self.assertIn("T1.r4.c2.t1", rendered)
        self.assertIn("| 11 | 1 |", rendered)
        self.assertIn("| 13 | 3 |", rendered)
        b = convert_rich_table(next(c["html"] for c in cases if c["pdf_page"] == 83))
        self.assertTrue(b["content"][-1]["text"].startswith("*Consult"))

    def test_surrounding_text_siblings_images_and_math(self):
        html = '<p>before</p><table><tr><td>x<math>n_2</math><img alt="arrow"/>y</td></tr></table><p>between</p><table><tr><td>last</td></tr></table><p>after</p>'
        b = convert_rich_table(html)
        self.assertEqual([n["kind"] for n in b["content"]], ["text", "table", "text", "table", "text"])
        contents = b["content"][1]["cells"][0]["content"]
        self.assertEqual([n["kind"] for n in contents], ["text", "image", "text"])
        self.assertIsNone(contents[1]["image_blake3"])
        self.assertIsNone(contents[1]["bbox_px"])
        text = render_table_block(b)
        self.assertIn("$n_2$", text)
        self.assertLess(text.index("before"), text.index("Table T1"))
        self.assertLess(text.index("between"), text.index("Table T2"))
        self.assertIn("unverified OCR alt: arrow", text)

    def test_span_header_geometry_and_projection(self):
        b = convert_rich_table(
            '<table><thead><tr><th rowspan="2">Model</th><th colspan="2">Time</th></tr><tr><th>Min</th><th>Max</th></tr></thead><tbody><tr><td>X</td><td>1</td><td>2</td></tr></tbody></table>'
        )
        t = b["content"][0]
        self.assertEqual(
            t["row_groups"], [{"kind": "thead", "start_row": 0, "row_count": 2}, {"kind": "tbody", "start_row": 2, "row_count": 1}]
        )
        text = render_table_block(b)
        self.assertIn("| Model | Time |  |", text)
        self.assertIn("|  | Min | Max |", text)
        self.assertEqual(text.count("Model"), 1)

    def test_malformed_and_limits(self):
        for html in [
            "<table><tr><td>x</tr></table>",
            '<table><tr><td rowspan="0">x</td></tr></table>',
            '<table><tr><td rowspan="2">x</td></tr></table>',
            "<div>" * 34 + "x" + "</div>" * 34,
            "<table>lost<tr><td>x</td></tr></table>",
        ]:
            with self.subTest(html=html), self.assertRaises(TableConversionError):
                convert_rich_table(html)
        b = convert_rich_table("<table><tr><td>x</td></tr></table>")
        for value in [0, -1, True, 1.2]:
            bad = copy.deepcopy(b)
            bad["content"][0]["cells"][0]["rowspan"] = value
            with self.assertRaises(TableConversionError):
                validate_rich_table(bad)
        bad = copy.deepcopy(b)
        bad["content"][0]["cells"] *= 2
        with self.assertRaises(TableConversionError):
            validate_rich_table(bad)

    def test_nested_images_are_traversed_without_claiming_unresolved_completion(self):
        import sqlite3

        from cpushowspeed.caption import _eligible_images
        from cpushowspeed.caption_backfill import backfill_document
        from cpushowspeed.document_report import _image_occurrences

        block = convert_rich_table('<table><tr><td><img alt="resolved later"/><img alt="no crop"/></td></tr></table>')
        block.update(kind="table", source_label="Table")
        images = [n for n in walk_content(block) if n.get("kind") == "image"]
        images[0].update(image_blake3="a" * 64, asset_status="resolved")
        with tempfile.TemporaryDirectory() as tmp, sqlite3.connect(":memory:") as db:
            path = Path(tmp) / "sample.docir.jsonl"
            path.write_text(json.dumps({"page": 1, "status": "ok", "blocks": [block]}) + "\n")
            self.assertEqual(list(_eligible_images(path, 1)), ["a" * 64])
            total, counts, unresolved = _image_occurrences([(path, 1)])
            self.assertEqual((total, unresolved), (1, 1))
            db.execute("CREATE TABLE captions (image_blake3 TEXT, caption TEXT)")
            db.execute("INSERT INTO captions VALUES (?, ?)", ("a" * 64, "saved caption"))
            self.assertEqual(backfill_document(path, 1, db), (1, 1))
            restored = json.loads(path.read_text())["blocks"][0]
            nodes = [n for n in walk_content(restored) if n.get("kind") == "image"]
            self.assertEqual(nodes[0]["caption"], "saved caption")
            self.assertNotIn("caption", nodes[1])

    def test_late_conversion_failure_does_not_partially_replace_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc, raw = Path(tmp) / "d.jsonl", Path(tmp) / "r.jsonl"
            pages = [
                {"page": i, "status": "ok", "blocks": [{"kind": "table", "source_label": "Table", "table": None}]} for i in (1, 2)
            ]
            doc.write_text("".join(json.dumps(p) + "\n" for p in pages))
            htmls = ["<table><tr><td>valid</td></tr></table>", "<table><tr><td>broken</tr></table>"]
            raw.write_text(
                json.dumps({"source_pdf": "a.pdf", "source_blake3": "h", "pages": 2})
                + "\n"
                + "".join(
                    json.dumps({"page": i, "status": "ok", "chunks": [{"label": "Table", "content": h}]}) + "\n"
                    for i, h in enumerate(htmls, 1)
                )
            )
            before = doc.read_bytes()
            with self.assertRaises(TableConversionError):
                migrate_document(doc, raw, 2, "h", "a.pdf")
            self.assertEqual(doc.read_bytes(), before)
            self.assertFalse(list(Path(tmp).glob("*.tmp")))

    def test_v1_reader(self):
        t = convert_html_table("<table><tr><td>A</td><td>B</td></tr></table>")
        self.assertIn("| A | B |", render_table_block({"table": t.as_dict()}))

    def test_migration_preserves_raw_captions_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "a.docir.jsonl"
            raw = Path(tmp) / "a.raw.jsonl"
            html = "<table><tr><td>x</td></tr></table><p>note</p>"
            block = {
                "kind": "table",
                "source_label": "Table",
                "bbox_px": [0, 0, 1, 1],
                "table": None,
                "conversion_status": "failed",
                "error": "old",
            }
            page = {"page": 1, "status": "ok", "blocks": [block, {"kind": "visual", "source_label": "Image", "caption": "keep"}]}
            doc.write_text(json.dumps(page) + "\n")
            raw.write_text(
                json.dumps({"source_pdf": "a.pdf", "source_blake3": "hash", "pages": 1})
                + "\n"
                + json.dumps(
                    {"page": 1, "status": "ok", "chunks": [{"label": "Table", "content": html}, {"label": "Image", "content": ""}]}
                )
                + "\n"
            )
            original = raw.read_bytes()
            before = doc.read_bytes()
            self.assertEqual(migrate_document(doc, raw, 1, "hash", "a.pdf", True), 1)
            self.assertEqual(doc.read_bytes(), before)
            self.assertEqual(migrate_document(doc, raw, 1, "hash", "a.pdf"), 1)
            self.assertEqual(raw.read_bytes(), original)
            self.assertEqual(json.loads(doc.read_text())["blocks"][1], page["blocks"][1])
            stamp = doc.stat().st_mtime_ns
            self.assertEqual(migrate_document(doc, raw, 1, "hash", "a.pdf"), 0)
            self.assertEqual(doc.stat().st_mtime_ns, stamp)
            before = doc.read_bytes()
            with self.assertRaises(ValueError):
                migrate_document(doc, raw, 1, "wrong", "a.pdf")
            self.assertEqual(doc.read_bytes(), before)
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
