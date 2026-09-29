"""Model discovery selects formats without rewriting the served model ID."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import click
from cpushowspeed.ocr import _resolve_model
from cpushowspeed.ocr_backends import detect_backend


class DetectionTests(unittest.TestCase):
    def test_family_tokens_allow_paths_case_and_unlisted_quantization(self):
        for name, expected in [
            ("chandra", "chandra"),
            ("datalab-to/chandra-ocr-2", "chandra"),
            ("/models/chandra-ocr-2-FP8-dynamic", "chandra"),
            ("publisher/Chandra_OCR_2-NEW-QUANT-v7", "chandra"),
            ("infly/Infinity-Parser2-Flash", "infinity"),
            ("/models/INFINITY-PARSER-2-FLASH-Q4_K_M.gguf", "infinity"),
            ("Infinity_Parser2_Flash-FP8-dynamic", "infinity"),
        ]:
            with self.subTest(name=name):
                self.assertEqual(detect_backend(name), expected)

    def test_unknown_or_ambiguous_names_require_override(self):
        for name in [
            "ocr",
            "notchandra",
            "Infinity-Parser-7B",
            "Infinity-Parser2-Pro",
            "Infinity-Parser20-Flash",
            "/chandra/unknown",
            "chandra-Infinity-Parser2-Flash",
            "",
        ]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                detect_backend(name)

    def test_explicit_model_skips_discovery_and_override_allows_alias(self):
        with patch("cpushowspeed.ocr.AsyncOpenAI") as client:
            self.assertEqual(asyncio.run(_resolve_model("http://unused/v1", "chandra-FP8", "auto")), ("chandra-FP8", "chandra"))
            self.assertEqual(asyncio.run(_resolve_model("http://unused/v1", "custom", "infinity")), ("custom", "infinity"))
            with self.assertRaises(click.ClickException):
                asyncio.run(_resolve_model("http://unused/v1", "custom", "auto"))
            client.assert_not_called()

    def test_discovery_preserves_exact_id_and_rejects_multiple_models(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        with patch("cpushowspeed.ocr.AsyncOpenAI", return_value=client):
            for names in [["infly/Infinity-Parser2-Flash-FP8"], [], ["chandra", "chandra-FP8"], ["custom"]]:
                client.models.list.return_value = SimpleNamespace(data=[SimpleNamespace(id=name) for name in names])
                if len(names) == 1 and names[0] != "custom":
                    self.assertEqual(asyncio.run(_resolve_model("http://unused/v1", None, "auto")), (names[0], "infinity"))
                else:
                    with self.assertRaises(click.ClickException):
                        asyncio.run(_resolve_model("http://unused/v1", None, "auto"))
            client.models.list.side_effect = RuntimeError("endpoint unavailable")
            with self.assertRaisesRegex(click.ClickException, "specify --model"):
                asyncio.run(_resolve_model("http://unused/v1", None, "auto"))
