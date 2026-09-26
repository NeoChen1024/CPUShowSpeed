"""Cross-generation fitting must preserve hardware identity and clustered calibration."""

import math
import unittest

from cpushowspeed.spec_fit import (
    Result,
    _automatic_pairs,
    _graph_fit,
    _memory_mib,
    _processor_key,
    _statistics,
)


class SpecFitTests(unittest.TestCase):
    def test_processor_prose_normalizes_without_merging_distinct_skus(self):
        self.assertEqual(_processor_key("Intel Xeon Processor 5130 (2.0 GHz, 4MB L2)"), _processor_key("Intel Xeon 5130"))
        self.assertNotEqual(_processor_key("Intel Xeon 5130"), _processor_key("Intel Xeon 5150"))

    def test_memory_parser_uses_total_capacity(self):
        self.assertEqual(_memory_mib("384 GB (24 x 16 GB DIMMs)"), 384 * 1024)
        self.assertEqual(_memory_mib("8 x 16 GB DIMMs"), 128 * 1024)
        self.assertIsNone(_memory_mib("unknown"))

    def test_core_or_smt_change_demotes_candidate(self):
        def result(generation, cores, threads):
            return Result(
                generation,
                generation,
                "Same System",
                "samesystem",
                "Intel Xeon 8180",
                "xeon8180",
                2,
                cores,
                threads,
                2500.0,
                65536.0,
                "Linux",
                "Compiler",
                10.0,
                9.0,
                f"https://www.spec.org/{generation}/results/{generation}.html",
                "hash",
            )

        good = _automatic_pairs(
            {"cpu2006": [result("cpu2006", 56, 2)], "cpu2017": [result("cpu2017", 56, 2)]}, "cpu2006", "cpu2017"
        )
        self.assertEqual(good[0]["match_tier"], "hardware_near")
        changed = _automatic_pairs(
            {"cpu2006": [result("cpu2006", 56, 2)], "cpu2017": [result("cpu2017", 54, 1)]}, "cpu2006", "cpu2017"
        )
        self.assertEqual(changed[0]["match_tier"], "name_cpu_chips_only")

    def test_repeated_submissions_do_not_multiply_processor_weight(self):
        rows = []
        for number, ratio in enumerate((2.0, 3.0, 4.0), 1):
            for _ in range(20 if number == 1 else 1):
                rows.append(
                    {
                        "match_tier": "hardware_near",
                        "peak_ratio": ratio,
                        "old_peak": ratio * 10,
                        "new_peak": 10.0,
                        "system_key": f"system{number}",
                        "processor_key": f"cpu{number}",
                        "chips": 1,
                        "old_clock_mhz": 1000.0,
                    }
                )
        fit = _statistics(rows, "peak")
        self.assertEqual(fit["processor_configs"], 3)
        self.assertAlmostEqual(fit["factor_old_per_new"], 24 ** (1 / 3))

    def test_three_generation_direct_edge_checks_chain(self):
        generations = ("cpu92", "cpu95", "cpu2000", "cpu2006", "cpu2017", "cpu2026")
        factors = (2, 3, 4, 5, 6)
        edges = [
            {
                "old_generation": generations[i],
                "new_generation": generations[i + 1],
                "base": {"log_factor": math.log(factor), "processor_configs": 4},
            }
            for i, factor in enumerate(factors)
        ]
        edges.append(
            {"old_generation": "cpu92", "new_generation": "cpu2000", "base": {"log_factor": math.log(6), "processor_configs": 4}}
        )
        result = _graph_fit(edges, "base")
        self.assertEqual(result["independent_cycle_constraints"], 1)
        self.assertAlmostEqual(result["vaxen_per_score"]["cpu2026"], 720)
        self.assertLess(max(abs(value) for value in result["edge_log_residuals"].values()), 1e-10)
        edges[-1]["base"]["log_factor"] = math.log(7)
        inconsistent = _graph_fit(edges, "base")
        self.assertGreater(max(abs(value) for value in inconsistent["edge_log_residuals"].values()), 0.01)


if __name__ == "__main__":
    unittest.main()
