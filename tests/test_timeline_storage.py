import tempfile
import unittest
from pathlib import Path

import pyarrow.parquet as pq
from cpushowspeed.timeline.parquet_export import WebExport, read_table, write_table


class ParquetTests(unittest.TestCase):
    def test_lossless_evidence_and_missing_values(self):
        rows = [
            dict(score=1.2345678901234567, year="", text="VAX μ", detail={"copies": None}, flag=True, empty=None),
            dict(score=0.0000000000003, year=1977, text="</script>", detail=[1, "", False], flag=False),
            dict(score=1e12, year=None, text="", detail={}, flag=None, empty=""),
        ]
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "records.parquet"
            write_table(p, rows)
            self.assertEqual(read_table(p), rows)
            meta = pq.read_metadata(p)
            self.assertEqual(meta.row_group(0).column(0).compression, "ZSTD")

    def test_draws_alignment_and_external_arrays(self):
        with tempfile.TemporaryDirectory() as root:
            export = WebExport(Path(root))
            original = {"a": [i / 7 for i in range(10000)], "b": [-i / 13 for i in range(10000)]}
            manifest = export.finish(
                [], {"experiments": [{"score": i} for i in range(2000)]}, {"networks": {"test": {"draws": original}}}
            )
            pointer = manifest["calibration"]["networks"]["test"]["draws"]
            rows = read_table(Path(root) / pointer["$parquet"])
            self.assertEqual({key: [r[key] for r in rows] for key in original}, original)
            self.assertEqual(manifest["lineage"]["experiments"]["shape"], "rows")
            self.assertLess((Path(root) / "manifest.json").stat().st_size, 10000)

    def test_reject_nonfinite_or_inexact_browser_numbers(self):
        with tempfile.TemporaryDirectory() as root:
            for value in [float("inf"), float("nan"), 2**53 + 1]:
                with self.assertRaises(ValueError):
                    write_table(Path(root) / "bad.parquet", [{"score": value}, {"score": ""}])
