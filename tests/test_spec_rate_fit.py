"""The rate fitter must keep rate submissions separate and preserve its own scale."""

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cpushowspeed.spec_rate_fit import GENERATIONS, _chain, _fit_edges, collect_rate


class RateFitTests(unittest.TestCase):
    def test_rate_only_and_separate_cpu95_relative_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, generation in enumerate(GENERATIONS):
                folder = root / generation
                folder.mkdir()
                path = folder / "bulk.csv"
                rows = []
                for cpu in range(3):
                    for suffix, score in (("rate", 100 / 2**index), ("", 999999)):
                        rows.append(
                            {
                                "Benchmark": "CINT" + generation[3:] + suffix,
                                "System": f"System {cpu}",
                                "Result": str(score),
                                "Baseline": str(score),
                                "# chips": "1",
                                "# Cores": "2",
                                "# Enabled Threads Per Core": "1",
                                "Processor": f"CPU {cpu}",
                                "Processor MHz": "1000",
                                "Memory": "8 GB",
                                "Disclosure": f'<A HREF="/{generation}/results/{generation}-{suffix or "speed"}-{cpu}.html">HTML</A>',
                            }
                        )
                with path.open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
                (folder / "bulk.csv.meta.json").write_text(
                    json.dumps(
                        {
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "source_url": "https://www.spec.org/cgi-bin/osgresults?field=rate",
                        }
                    )
                )
            results = collect_rate(root)
            self.assertEqual(
                {generation: len(rows) for generation, rows in results.items()}, {generation: 3 for generation in GENERATIONS}
            )
            pairs, edges = _fit_edges(results)
            self.assertEqual(len(pairs), 12)
            for edge in edges:
                self.assertAlmostEqual(edge["strict", "base"]["factor_old_per_new"], 2)
                self.assertEqual(edge["strict", "base"]["processor_configs"], 3)
            chain = _chain(edges, "strict", "base")
            self.assertEqual(chain["relative_to"], "CPU95 integer rate score")
            self.assertAlmostEqual(chain["factors"]["cpu2026"], 16)


if __name__ == "__main__":
    unittest.main()
