"""Infinity wire-format, spatial mapping, and request regressions."""

import asyncio
import base64
import io
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import click
from cpushowspeed import infinity
from cpushowspeed.documents import _connect
from cpushowspeed.ocr import (
    PagePayload,
    _convert_page,
    _prepare_page,
    _request,
    _run_ocr,
    _stage_path,
)
from PIL import Image


class InfinityTests(unittest.TestCase):
    def test_strict_complete_json(self):
        item = {"bbox": [0, 0, 1000, 1000], "category": "text", "text": "x" * 70000}
        raw = json.dumps([item])
        self.assertEqual(infinity.parse_layout(raw), [item])
        self.assertEqual(infinity.parse_layout("```json\n" + raw + "\n```"), [item])
        self.assertEqual(infinity.parse_layout("[]"), [])
        for bad in [
            raw[:-1],
            "{}",
            "[null]",
            json.dumps([{**item, "bbox": [0, 0, 1001, 1000]}]),
            json.dumps([{**item, "bbox": [0, 0, True, 1000]}]),
            json.dumps([{**item, "category": "unknown"}]),
        ]:
            with self.subTest(bad=bad[:80]), self.assertRaises(ValueError):
                infinity.parse_layout(bad)

    def test_mapping_and_raw_preservation(self):
        items = [
            {"bbox": [0, 0, 1000, 100], "category": "formula", "text": "$x^2$"},
            {"bbox": [0, 100, 1000, 500], "category": "table", "text": "<table><tr><td>A</td></tr></table>"},
            {"bbox": [100, 500, 600, 900], "category": "figure", "text": ""},
        ]
        raw = json.dumps(items)
        encoded = io.BytesIO()
        Image.new("RGB", (800, 1000), "white").save(encoded, format="PNG")
        payload = PagePayload(None, 1, encoded.getvalue(), "", 800, 1000)
        with tempfile.TemporaryDirectory() as temp:
            record, page, assets = _prepare_page(payload, raw, 100, "stop", Path(temp), "infinity")
            self.assertEqual(record["raw"], raw)
            self.assertEqual(record["chunks"], items)
            self.assertEqual(record["top_p"], 1.0)
            self.assertEqual([b["kind"] for b in page["blocks"]], ["text", "table", "visual"])
            self.assertNotIn("markdown", page["blocks"][1])
            self.assertEqual(page["blocks"][2]["bbox_px"], [80, 500, 480, 900])
            with Image.open(Path(temp) / assets[0]["path"]) as crop:
                self.assertEqual(crop.size, (400, 400))
            blank, _, assets = _convert_page("[]", encoded.getvalue(), 2, Path(temp), "infinity")
            self.assertEqual(blank["status"], "blank")
            self.assertEqual(assets, [])

    def test_resize_and_repeat(self):
        for size in [(100, 101), (5000, 5000), (8, 8)]:
            image = infinity.resize(Image.new("RGB", size))
            self.assertEqual(image.width % 32, 0)
            self.assertEqual(image.height % 32, 0)
            self.assertLessEqual(image.width * image.height, infinity.MAX_PIXELS)
            self.assertGreaterEqual(image.width * image.height, infinity.MIN_PIXELS)
        self.assertTrue(infinity.has_repeat("broken JSON " + "loop " * 500))
        self.assertFalse(infinity.has_repeat('[{"text":"hello"}]'))

    def test_request_uses_infinity_protocol(self):
        create = AsyncMock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="[]"), finish_reason="stop")], usage=None
            )
        )
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        payload = PagePayload(None, 1, b"", base64.b64encode(b"png").decode(), 1, 1)
        self.assertEqual(asyncio.run(_request(client, infinity.MODEL, payload, 30, "infinity")), ("[]", 0, "stop", None))
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs["messages"][0]["content"][1]["text"], infinity.PROMPT)
        self.assertEqual(kwargs["max_tokens"], 32768)
        self.assertEqual(kwargs["top_p"], 1.0)
        self.assertNotIn("extra_body", kwargs)

    def test_invalid_layout_retries_and_resume_is_backend_specific(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "input"
            root.mkdir()
            source = root / "sample.pdf"
            source.write_bytes(b"renderer is mocked")
            stat = source.stat()
            database = Path(temp) / "inventory.sqlite"
            with _connect(database, root) as db:
                db.execute(
                    "INSERT INTO files (relative_path,size_bytes,mtime_ns,ctime_ns,blake3,pages,status,seen_run) "
                    "VALUES (?,?,?,?,?,1,'ok','test')",
                    (source.name, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, "hash"),
                )
            output = Path(temp) / "output"
            png = io.BytesIO()
            Image.new("RGB", (100, 100), "white").save(png, format="PNG")
            args = (database, root, output, "http://localhost:1/v1", infinity.MODEL, 1, 1, 32, None, "", None, 30, 1, 0)
            request = AsyncMock(side_effect=[("[{", 10, "stop", None), ("[]", 2, "stop", None)])

            def pool(**kwargs):
                return ThreadPoolExecutor(max_workers=kwargs["max_workers"])

            with (
                patch("cpushowspeed.ocr.ProcessPoolExecutor", side_effect=pool),
                patch("cpushowspeed.ocr._render_page", return_value=(png.getvalue(), "", 100, 100)),
                patch("cpushowspeed.ocr._request", request),
            ):
                asyncio.run(_run_ocr(*args, backend="infinity"))
                self.assertEqual(request.await_count, 2)
                raw_path = output / "sample.raw.jsonl"
                saved = raw_path.read_bytes()
                record = json.loads(saved.splitlines()[1])
                self.assertEqual(record["attempts"], 2)
                self.assertIn("invalid Infinity layout", record["retry_reasons"][0])
                asyncio.run(_run_ocr(*args, backend="infinity"))
                self.assertEqual(request.await_count, 2)
                self.assertEqual(raw_path.read_bytes(), saved)
                with self.assertRaisesRegex(click.ClickException, "different OCR settings"):
                    asyncio.run(_run_ocr(*args, backend="chandra"))

                for backend in ("infinity", "chandra"):
                    with self.subTest(backend=backend):
                        failed_output = Path(temp) / f"failed-{backend}"
                        retry_args = list(args)
                        retry_args[2] = failed_output
                        retry_args[12] = 5
                        request.reset_mock()
                        request.side_effect = None
                        request.return_value = ("invalid layout", 2, "stop", None)
                        with self.assertRaisesRegex(click.ClickException, "unfinished pages"):
                            asyncio.run(_run_ocr(*retry_args, backend=backend))
                        self.assertEqual(request.await_count, 6)
                        self.assertFalse((failed_output / "sample.docir.jsonl").exists())
                        failed = json.loads(_stage_path(failed_output, "sample.pdf", 1).read_text())
                        self.assertEqual(failed["raw"]["attempts"], 6)
                        self.assertEqual(len(failed["raw"]["retry_reasons"]), 6)
                        self.assertEqual(failed["docir"]["status"], "error")
