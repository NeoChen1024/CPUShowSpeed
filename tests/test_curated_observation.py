"""Observation sources resolve by hash, cited registry key, unique address, then dataset prefix."""

import unittest

from cpushowspeed.database.observations import SourceIndex

H = "a" * 64
SOURCES = [
    dict(source_id="src:hashed", hash=H, url="https://shared.example/x", legacy_ids=["r:1"]),
    dict(source_id="src:other", url="https://shared.example/x", legacy_ids=["pkg:S02"]),
    dict(source_id="src:unique", url="https://unique.example/y", legacy_ids=["r:3"]),
    dict(source_id="src:pages", url="https://pages.example/", member_url_prefix="https://pages.example/spec.", legacy_ids=["r:4"]),
]


class SourceIndexTests(unittest.TestCase):
    def test_resolution_order(self):
        index = SourceIndex(SOURCES)
        self.assertEqual(index.resolve(dict(url="https://shared.example/x", sha256=H)), ("src:hashed", "hash"))
        self.assertEqual(index.resolve(dict(url="https://shared.example/x", legacy_id="pkg:S02")), ("src:other", "registry_key"))
        self.assertEqual(index.resolve(dict(url="https://shared.example/x")), (None, None))
        self.assertEqual(index.resolve(dict(url="https://unique.example/y")), ("src:unique", "url"))
        self.assertEqual(index.resolve(dict(url="https://pages.example/spec.a.html")), ("src:pages", "dataset_member"))
        self.assertEqual(index.resolve(dict(url="https://pages.example/other.html")), (None, None))


if __name__ == "__main__":
    unittest.main()
