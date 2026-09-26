"""Caption selection, image integrity, and document dispatch tests."""

import asyncio
import base64
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import blake3
from cpushowspeed import caption


class FakeClient:
    starts = []
    active = 0
    peak = 0

    def __init__(self, **_kwargs):
        self.chat = SimpleNamespace(completions=self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def create(self, **kwargs):
        payload = kwargs["messages"][0]["content"]
        assert len(payload) == 2 and payload[1]["text"] == caption.PROMPT
        data = base64.b64decode(payload[0]["image_url"]["url"].split(",", 1)[1])
        FakeClient.starts.append(data)
        FakeClient.active += 1
        FakeClient.peak = max(FakeClient.peak, FakeClient.active)
        await asyncio.sleep(0.01)
        FakeClient.active -= 1
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=data.decode()))])


class CaptionTests(unittest.TestCase):
    def test_structured_diagrams_are_skipped_but_unparsed_images_remain(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "doc.docir.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "page": 1,
                        "status": "ok",
                        "blocks": [
                            {"source_label": "Diagram", "image_blake3": "structured", "diagram": {"code": "graph TD"}},
                            {"source_label": "Image", "image_blake3": "image", "alt": "old OCR"},
                            {"source_label": "Chart", "image_blake3": "unparsed"},
                            {"source_label": "Image", "image_blake3": "image"},
                        ],
                    }
                )
                + "\n"
            )
            self.assertEqual(list(caption._eligible_images(path, 1)), ["image", "unparsed"])

    def test_image_hash_is_checked_before_submission(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            digest = blake3.blake3(b"image").hexdigest()
            (root / "image.png").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "BLAKE3 mismatch"):
                caption._image_bytes(root, {"path": "image.png", "media_type": "image/png"}, digest)

    def test_oldest_started_document_fills_slots_and_resume_skips_successes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "out"
            pool = output / "ImagePool"
            pool.mkdir(parents=True)
            database = root / "inventory.sqlite"
            file_list = root / "files.txt"
            file_list.write_text("a.pdf\nb.pdf\n")
            with sqlite3.connect(database) as db:
                db.executescript(
                    "CREATE TABLE metadata(key TEXT, value TEXT);"
                    "CREATE TABLE files(relative_path TEXT, pages INTEGER, size_bytes INTEGER, blake3 TEXT, "
                    "mtime_ns INTEGER, ctime_ns INTEGER, status TEXT);"
                    "CREATE TABLE ocr_runs(run_id TEXT, output_root TEXT);"
                    "CREATE TABLE ocr_documents(run_id TEXT, relative_path TEXT, source_blake3 TEXT, "
                    "source_pages INTEGER, status TEXT, completed_pages INTEGER);"
                )
                db.execute("INSERT INTO metadata VALUES ('root', ?)", (str(root),))
                db.execute("INSERT INTO ocr_runs VALUES ('run', ?)", (str(output),))
                for name in ("a.pdf", "b.pdf"):
                    db.execute("INSERT INTO files VALUES (?, 1, 1, 'source', 1, 1, 'ok')", (name,))
                    db.execute("INSERT INTO ocr_documents VALUES ('run', ?, 'source', 1, 'published', 1)", (name,))
                    stem = output / name[:-4]
                    stem.with_name(stem.name + ".raw.jsonl").write_text("raw\n")
                    blocks = []
                    for number in (1, 2):
                        data = f"{name}-{number}".encode()
                        digest = blake3.blake3(data).hexdigest()
                        image = pool / f"{digest}.png"
                        image.write_bytes(data)
                        blocks.append({"source_label": "Image", "image_blake3": digest})
                    stem.with_name(stem.name + ".docir.jsonl").write_text(
                        json.dumps({"page": 1, "status": "ok", "blocks": blocks}) + "\n"
                    )
            with sqlite3.connect(pool / "catalog.sqlite") as db:
                db.execute("CREATE TABLE images(blake3 TEXT, path TEXT, media_type TEXT, width INTEGER, height INTEGER)")
                for image in pool.glob("*.png"):
                    db.execute("INSERT INTO images VALUES (?, ?, 'image/png', 1, 1)", (image.stem, image.name))
                db.execute("CREATE TABLE caption_documents(relative_path TEXT PRIMARY KEY, started_at TEXT NOT NULL)")
                db.execute("INSERT INTO caption_documents VALUES ('b.pdf', '2020-01-01T00:00:00')")
            FakeClient.starts = []
            FakeClient.active = FakeClient.peak = 0
            args = (database, output, file_list, "http://unused/v1", "fake", 2, 10.0, 0, 1.0, False)
            with patch.object(caption, "AsyncOpenAI", FakeClient):
                self.assertFalse(asyncio.run(caption._run(*args)))
                self.assertFalse(asyncio.run(caption._run(*args)))
            self.assertEqual(len(FakeClient.starts), 4)
            self.assertTrue(all(item.startswith(b"b.pdf") for item in FakeClient.starts[:2]))
            self.assertEqual(FakeClient.peak, 2)
            with sqlite3.connect(pool / "catalog.sqlite") as db:
                self.assertEqual(db.execute("SELECT count(*) FROM captions WHERE caption IS NOT NULL").fetchone()[0], 4)


if __name__ == "__main__":
    unittest.main()
