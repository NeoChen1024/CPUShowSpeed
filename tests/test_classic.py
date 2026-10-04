"""Preserve archive identity and layout without interpreting historical scores."""

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cpushowspeed.classical.collect import extract_html, fetch_source, immutable_write, load_sources, normalize_url


class ClassicTests(unittest.TestCase):
    def test_spaces_fragments_and_unsafe_urls(self):
        self.assertEqual(normalize_url("http://example.org/old results.htm#table"), "http://example.org/old%20results.htm")
        for url in ["file:///etc/passwd", "https://user:secret@example.org/", "relative.htm"]:
            with self.assertRaises(ValueError):
                normalize_url(url)

    def test_layout_links_and_no_score_invention(self):
        data = b'<title>Old results</title><table><tr><th colspan="2">Timing</th></tr><tr><td>Machine</td><td>1.25</td></tr></table><pre>CPU   us\nA     1.25\n</pre><a href="test code.zip#readme">Code</a>'
        result = extract_html(data, "http://example.org/index.htm")
        self.assertEqual(result["blocks"][1]["text"], "CPU   us\nA     1.25\n")
        table = result["blocks"][0]["content"][0]
        self.assertEqual(table["cells"][0]["colspan"], 2)
        self.assertEqual(table["cells"][-1]["content"][0]["text"], "1.25")
        self.assertEqual(result["links"][0]["fragment"], "readme")
        self.assertEqual(result["links"][0]["url"], "http://example.org/test%20code.zip")
        self.assertNotIn("vaxen", result)

    def test_immutable_conflict_and_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "blob"
            immutable_write(p, b"one")
            stamp = p.stat().st_mtime_ns
            immutable_write(p, b"one")
            self.assertEqual(p.stat().st_mtime_ns, stamp)
            with self.assertRaises(ValueError):
                immutable_write(p, b"two")
            self.assertEqual(p.read_bytes(), b"one")
            f = Path(tmp) / "sources.csv"
            f.write_text("source_id,url,provider,lineage,family,role\nx,http://example.org,A,B,C,D\nx,http://example.org,A,B,C,D\n")
            with self.assertRaises(ValueError):
                load_sources(f)

    def test_fetch_size_limit_and_network_error_are_recorded(self):
        class Response(io.BytesIO):
            url = "http://example.org/final"
            status = 200
            headers = {"Content-Type": "text/plain"}

        source = {"source_id": "example", "url": "http://example.org/", "lineage": "one"}
        with tempfile.TemporaryDirectory() as tmp:
            with patch("cpushowspeed.classical.collect.urlopen", return_value=Response(b"abc")):
                r = fetch_source(source, Path(tmp), 2, 3)
            self.assertEqual(r["status"], "downloaded")
            self.assertEqual(Path(r["blob_path"]).read_bytes(), b"abc")
            with patch("cpushowspeed.classical.collect.urlopen", return_value=Response(b"abcd")):
                self.assertEqual(fetch_source(source, Path(tmp), 2, 3)["status"], "failed")
            with patch("cpushowspeed.classical.collect.urlopen", side_effect=TimeoutError("offline")):
                self.assertIn("offline", fetch_source(source, Path(tmp), 2, 3)["error"])


if __name__ == "__main__":
    unittest.main()
