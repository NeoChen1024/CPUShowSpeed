"""Annual rate bins retain every eligible source result and deterministic leaders."""

import unittest

from cpushowspeed.annual_rate import _annual, _month


class AnnualRateTests(unittest.TestCase):
    def test_month_keeps_source_precision(self):
        self.assertEqual(_month("Aug-2019"), "2019-08")
        self.assertEqual(_month("2019-08"), "2019-08")
        self.assertEqual(_month(""), "")
        with self.assertRaises(ValueError):
            _month("2019")

    def test_all_dated_submissions_count_and_tie_source_is_deterministic(self):
        def row(url, score, year):
            return {
                "mode": "base",
                "year": year,
                "source_url": url,
                "vaxen_same_os": score,
                "vaxen_hardware_near": score * 1.1,
                "generation": "cpu92",
                "result_id": url,
                "benchmark_id": "SPECrate_base_int92",
                "reported_score": score,
                "system": url,
                "processor": "CPU",
                "chips": 1,
                "hardware_availability_month": year + "-03" if year else "",
                "test_month": "",
                "publication_month": "",
                "source_container_sha256": "digest",
            }

        rows = [
            row("https://example.com/z", 20, "1993"),
            row("https://example.com/a", 20, "1993"),
            row("https://example.com/low", 10, "1993"),
            row("https://example.com/undated", 999, ""),
        ]
        leaders, stats = _annual(rows, "same_os")
        self.assertEqual(len(leaders), 1)
        self.assertEqual(leaders[0]["year_submission_count"], 3)
        self.assertEqual(leaders[0]["tie_count"], 2)
        self.assertEqual(leaders[0]["source_url"], "https://example.com/a")
        self.assertEqual(stats[0]["median_vaxen"], 20)
        self.assertEqual(stats[0]["maximum_vaxen"], 20)


if __name__ == "__main__":
    unittest.main()
