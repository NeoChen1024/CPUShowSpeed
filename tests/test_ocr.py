"""Invariants for OCR page conversion and crash recovery."""

import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import blake3
import click
from click.testing import CliRunner
from cpushowspeed.documents.chandra import has_repeat as _has_bad_repeat
from cpushowspeed.documents.ocr import (
    PageETAColumn,
    _convert_page,
    _finalize,
    _read_file_list,
    _read_stage,
    _record_page,
    _stage_path,
    _verify_final,
    _write_atomic,
    ocr_command,
    select_inventory,
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

    def test_full_inventory_requires_explicit_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pdf"
            root.mkdir()
            database = Path(temporary) / "inventory.sqlite"
            with sqlite3.connect(database) as connection:
                connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                connection.execute("INSERT INTO metadata VALUES ('root', ?)", (str(root),))
            output = Path(temporary) / "output"
            result = CliRunner().invoke(ocr_command, ["--database", str(database), "--output-root", str(output)])
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("select PDFs with --file-list", result.output)
            self.assertFalse(output.exists())

    def test_file_list_selects_only_inventory_matches_in_list_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pdf"
            root.mkdir()
            file_list = Path(temporary) / "selected.txt"
            file_list.write_text(f"b/two.pdf\n{root / 'a/one.pdf'}\nb/two.pdf\n\n", encoding="utf-8")
            connection = sqlite3.connect(":memory:")
            connection.row_factory = sqlite3.Row
            connection.execute(
                "CREATE TABLE files (relative_path TEXT, pages INTEGER, size_bytes INTEGER, "
                "blake3 TEXT, mtime_ns INTEGER, ctime_ns INTEGER, status TEXT)"
            )
            connection.executemany(
                "INSERT INTO files VALUES (?, 1, 100, 'hash', 0, 0, ?)",
                [("a/one.pdf", "ok"), ("b/two.pdf", "ok"), ("c/unused.pdf", "ok")],
            )
            with patch("cpushowspeed.documents.ocr.CONSOLE") as console:
                self.assertEqual(_read_file_list(file_list, root), ["b/two.pdf", "a/one.pdf"])
                rows = select_inventory(connection, root, file_list, "", None)
                self.assertEqual(console.print.call_count, 2)
            self.assertEqual([row["relative_path"] for row in rows], ["b/two.pdf", "a/one.pdf"])
            file_list.write_text("c/unused.pdf\nb/two.pdf\n", encoding="utf-8")
            self.assertEqual(
                [row["relative_path"] for row in select_inventory(connection, root, file_list, "", None)],
                ["c/unused.pdf", "b/two.pdf"],
            )
            connection.execute("UPDATE files SET status = 'pdf_error' WHERE relative_path = 'c/unused.pdf'")
            with self.assertRaises(click.ClickException):
                select_inventory(connection, root, file_list, "", None)
            file_list.write_text("missing.pdf\n", encoding="utf-8")
            with self.assertRaises(click.ClickException):
                select_inventory(connection, root, file_list, "", None)
            file_list.write_text("../outside.pdf\n", encoding="utf-8")
            with self.assertRaises(click.ClickException):
                _read_file_list(file_list, root)
            connection.close()

    def test_binary_table_row_is_not_generation_repetition(self):
        bit_row = '<div data-label="Table"><table><tr><td>0 1 1 ' + ("0 " * 40) + "</td></tr></table></div>"
        self.assertFalse(_has_bad_repeat(bit_row))
        long_run = '<div data-label="Table"><table><tr><td>' + ("0 " * 500) + "</td></tr></table></div>"
        self.assertTrue(_has_bad_repeat(long_run))
        self.assertTrue(_has_bad_repeat("<div>" + ("loop " * 400) + "</div>"))

    def test_blank_or_zero_columns_in_a_finished_table_are_not_repetition(self):
        def row(label, cell, n):
            return f"<tr>\n<td>{label}</td>\n" + f"<td>{cell}</td>\n" * n + "</tr>\n"

        table = '<div data-label="Table"><table>\n' + row("1.", "", 19) + row("2.", "0", 15) + "<tr><td>3.</td><td>7</td></tr>\n"
        self.assertFalse(_has_bad_repeat(table + "</table>\n</div>"))
        self.assertTrue(_has_bad_repeat(table + row("4.", "0", 120) + "</table>\n</div>"))
        self.assertTrue(_has_bad_repeat('<div data-label="Table"><table>\n' + row("x", "", 3) * 40 + "</table>\n</div>"))

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
            self.assertEqual(page["blocks"][1]["content"][0]["cells"][1]["content"][0]["text"], "A")
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
