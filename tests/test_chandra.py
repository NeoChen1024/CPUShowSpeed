"""Local adapter regressions captured from the Chandra 0.2.0 baseline."""

import unittest

from cpushowspeed.documents import chandra
from cpushowspeed.documents.ocr_backends import compatible_settings, sampling
from PIL import Image


class ChandraTests(unittest.TestCase):
    def test_markdown_math_code_and_preserved_newlines(self):
        cases = [
            ("<p>Math <math>x_1+2</math> $100 &amp; y</p>", "Math  $x_1+2$  \\$100 & y"),
            ('<math display="block">x^2</math>', "$$x^2$$"),
            ("<ul><li>A<ul><li>B</li></ul></li></ul>", "- A\n  - B"),
            ("<pre>a\n b</pre>", "```\na\n b\n```"),
            ("<p>a\n   b</p>", "a\n b"),
            ('<p>hello<img alt="hallucinated"/></p>', "hello"),
        ]
        for html, expected in cases:
            with self.subTest(html=html):
                self.assertEqual(chandra.markdown(html, "Text"), expected)

    def test_chunk_order_boxes_and_nested_attributes(self):
        raw = (
            '<div data-label="Blank-Page"></div>'
            '<div data-label="Text" data-bbox="100 200 500 600"><p data-bbox="1 2 3 4">A</p></div>'
            '<div data-label="Image" data-bbox="invalid"><img alt="B"/></div>'
        )
        chunks, blocks = chandra.parse_page(raw, 800, 1000)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], {"bbox": [80, 200, 400, 600], "label": "Text", "content": "<p>A</p>"})
        self.assertEqual(blocks[0]["bbox_px"], [80, 200, 400, 600])
        self.assertIsNone(blocks[1]["bbox_px"])
        self.assertEqual(chunks[1]["bbox"], [0, 0, 0, 1])
        with self.assertRaises(ValueError):
            chandra.parse_page("not layout HTML", 800, 1000)

    def test_resize_baseline(self):
        for size, expected in [((100, 101), (224, 224)), ((2480, 3509), (2100, 2968)), ((15, 9), (280, 168))]:
            with self.subTest(size=size):
                self.assertEqual(chandra.resize(Image.new("RGB", size)).size, expected)

    def test_sampling_and_legacy_resume(self):
        self.assertEqual(sampling("chandra", 0), {"temperature": 0.0, "top_p": 0.1})
        self.assertEqual(sampling("chandra", 5), {"temperature": 0.8, "top_p": 0.95})
        current = {**chandra.CONFIG, "model": "chandra", "prompt_blake3": "prompt"}
        legacy = dict(current)
        legacy.pop("backend")
        legacy.pop("adapter_version")
        legacy["chandra_version"] = "0.2.0"
        self.assertTrue(compatible_settings(legacy, current))
        self.assertIn("chandra_version", legacy)
        for key, value in [("prompt_blake3", "changed"), ("model", "changed"), ("backend", "infinity"), ("adapter_version", 2)]:
            self.assertFalse(compatible_settings(legacy, {**current, key: value}))
        self.assertFalse(compatible_settings({**legacy, "chandra_version": "other"}, current))
