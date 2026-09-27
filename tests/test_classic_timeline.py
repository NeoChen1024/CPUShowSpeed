import json
import unittest
from pathlib import Path

from cpushowspeed.classic_timeline import (
    apply_cpu_release_proxy,
    choose_date,
    collect,
    date_key,
    source_identity,
    year,
)


class TimelineTests(unittest.TestCase):
    def test_cpu_release_fallback_respects_configuration_identity_and_known_dates(self):
        record = dict(configuration_id="a", system="Escom", cpu="Pentium", clock_mhz=100, year="", date_status="unknown")
        proxy = dict(
            system="Escom",
            cpu="Pentium",
            clock_mhz="100.0",
            release_date="1994",
            cpu_interpretation="Pentium 100",
            source_url="source",
            notes="CPU only",
        )
        apply_cpu_release_proxy(record, {"a": proxy})
        self.assertEqual(record["year"], 1994)
        self.assertEqual(record["date_method"], "reviewed_cpu_release_year_proxy")
        other = dict(configuration_id="a", system="Escom", cpu="486DX2", clock_mhz=66, year="", date_status="unknown")
        with self.assertRaises(ValueError):
            apply_cpu_release_proxy(other, {"a": proxy})
        for status in ("estimated", "unresolved_conflict"):
            known = dict(other, year=1996, date_status=status)
            apply_cpu_release_proxy(known, {"a": proxy})
            self.assertEqual(known["year"], 1996)

    def test_document_reviews_cover_batch_and_event_pages(self):
        import csv

        root = Path("research/data/historical")
        with (root / "year-document-reviews.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        reviews = {r["source_path"]: r for r in rows}
        self.assertEqual(len(rows), len(reviews))
        self.assertEqual(set(reviews), set(Path("inventories/hardware-year-ocr.txt").read_text().splitlines()))
        with (root / "hardware-date-evidence.csv").open() as stream:
            events = list(csv.DictReader(stream))
        for path, review in reviews.items():
            self.assertEqual(review["review_status"], "date_scope_review_complete")
            self.assertEqual(review["text_pages_screened"], review["total_pages"])
            pages = {int(p) for p in review["original_pdf_pages_checked"].split(";")}
            self.assertTrue(pages)
            self.assertTrue(all(1 <= p <= int(review["total_pages"]) for p in pages))
            associated = [e for e in events if e["source_path"] == path]
            self.assertEqual(set(filter(None, review["event_ids"].split(";"))), {e["id"] for e in associated})
            for event in associated:
                self.assertEqual(event["source_blake3"], review["source_blake3"])
                self.assertIn(int(event["pdf_page"]), pages)

    def test_dates_keep_actual_precision_and_no_publication_inference(self):
        assert year("1992-03") == 1992
        assert year("circa 1992") is None
        assert choose_date("Unknown machine", None, [], [])["year"] == ""
        assert date_key("DEC Alpha 3000/300", 150) == date_key("DEC 3000/300", 150)

    def test_date_conflicts_retained_and_review_override_wins(self):
        es = [
            dict(
                model_key=date_key("Machine"), priority=2, clock_mhz="", year=y, method="approximate", source_url="source", notes=""
            )
            for y in (1970, 1974)
        ]
        result = choose_date("Machine", None, es, [])
        assert (result["year"], result["year_low"], result["year_high"]) == (1972, 1970, 1974)
        rule = dict(system_regex="Machine", year="", method="conflict", source_url="review", notes="unresolved")
        assert choose_date("Machine", None, es, [rule])["date_status"] == "unresolved_conflict"

    def test_actual_linpack_wrapped_name_and_compiler_continuation(self):
        root = Path("data/derived/classic")
        if not (root / "netlib-linpack-report.txt").exists():
            self.skipTest("local source corpus unavailable")
        records = {r["id"]: r for r in map(json.loads, (root / "overlap-spec/classical-records.jsonl").read_text().splitlines())}
        pages = (root / "netlib-linpack-report.txt").read_text().split("\f")
        for locator, name, clock in [("7:line:31", "HP ProLiant BL20p G3", 3800), ("24:line:26", "DEC 500/400", 400)]:
            original = records["netlib-linpack-report:pdf:page:" + locator]
            fixed = source_identity(original, pages)
            assert fixed["system"].startswith(name)
            assert fixed["reported_processor_count"] == 1
            assert fixed["clock_mhz"] == clock
            assert fixed["raw_record"] == original["raw_record"]
            assert "original_system" not in original

    def test_repeat_scores_preserved_and_os_and_clocks_separate(self):
        records = []
        for i, (clock, os, score) in enumerate([(10, "A", 2), (10, "A", 8), (10, "B", 5), (20, "A", 7)]):
            records.append(
                dict(
                    id=str(i),
                    source_id="s",
                    system="M",
                    benchmark="Dhrystone",
                    clock_mhz=clock,
                    os_raw=os,
                    metrics_raw={"v1.1_DMIPS": score},
                    configuration_raw="",
                    processor_raw="cpu",
                    source_url="url",
                    locator=str(i),
                )
            )
        rows, observations, exclusions = collect(records, [], [], [], {})
        assert len(rows) == 3
        assert len(observations) == 4
        row = next(r for r in rows if r["clock_mhz"] == 10 and r["os"] == "A")
        assert row["observation_count"] == 2
        self.assertAlmostEqual(row["scores"]["Dhrystone:v1.1_DMIPS"], 4)
        assert not exclusions

    def test_reviewed_events_do_not_promote_forecast_deliveries(self):
        import csv
        import re

        path = Path("research/data/historical/hardware-date-evidence.csv")
        with path.open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len({r["id"] for r in rows}), len(rows))
        for row in rows:
            self.assertIsNotNone(year(row["date"]))
            if row["use_for_timeline"] == "true":
                self.assertEqual(row["event_status"], "reported")
                re.compile(row["system_regex"])
            if row["date_precision"] == "quarter":
                self.assertIn(row["quarter"], ("1", "2", "3", "4"))
                self.assertEqual(len(row["date"]), 4)

    def test_reviewed_model_pattern_has_priority_without_extending_to_other_models(self):
        row = dict(
            model_key="icl2966",
            system_regex=r"ICL\s+2966\b",
            priority=0,
            clock_mhz="",
            year=1981,
            method="reviewed_first_delivery_model_proxy",
            source_url="source",
            notes="option may be later",
        )
        self.assertEqual(choose_date("ICL 2966 PEF", None, [row], [])["year"], 1981)
        self.assertEqual(choose_date("ICL 29660", None, [row], [])["year"], "")

    def test_explicit_date_pattern_is_not_bypassed_by_normalized_model_key(self):
        row = dict(
            model_key=date_key("Machine (upgrade)"),
            system_regex=r"^Machine$",
            priority=0,
            clock_mhz="",
            year=1981,
            method="reviewed_model_proxy",
            source_url="source",
            notes="base model only",
        )
        self.assertEqual(choose_date("Machine", None, [row], [])["year"], 1981)
        self.assertEqual(choose_date("Machine (upgrade)", None, [row], [])["year"], "")
