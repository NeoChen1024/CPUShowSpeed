import unittest

from cpushowspeed.timeline_dates import CPUChronology, candidate, select_date


class DateSelectionTests(unittest.TestCase):
    def test_cpu_overrides_hardware_and_publication_but_keeps_all(self):
        dates = [
            candidate("submission", "2002-03", "publication", "reported"),
            candidate("hardware", "2000", "hardware", "reported"),
            candidate("cpu", "1999", "cpu", "reviewed"),
        ]
        result = select_date(dates)
        self.assertEqual((result["year"], result["date_kind"]), (1999, "cpu"))
        self.assertEqual(len(result["date_candidates"]), 3)
        self.assertEqual(select_date(dates[:2])["year"], 2000)
        self.assertEqual(select_date(dates[:1])["year"], 2002)
        self.assertEqual(select_date([])["date_kind"], "unknown")

    def test_conflicts_do_not_average_across_different_date_kinds(self):
        dates = [
            candidate("cpu", "1994", "a", "reviewed"),
            candidate("cpu", "1996", "b", "reviewed"),
            candidate("hardware", "2005", "c", "reported"),
        ]
        r = select_date(dates)
        self.assertEqual((r["year"], r["year_low"], r["year_high"]), (1995, 1994, 1996))
        self.assertIsNone(candidate("cpu", "circa 1994", "x", "unknown"))

    def test_submission_era_veto_keeps_record_evidence_and_priority(self):
        sub = candidate("submission", "2025", "result", "reported")
        review = dict(
            submission_date="2025",
            decision="reject",
            reason="Retrospective test of 1960s hardware",
            source_url="historical-source",
            reviewed_on="2026-09-27",
        )
        result = select_date([sub], review)
        self.assertEqual(result["date_kind"], "unknown")
        self.assertFalse(result["date_candidates"][0]["eligible"])
        self.assertEqual(sub.get("eligible"), None)  # source candidate is immutable
        cpu = candidate("cpu", "1965", "cpu", "reviewed")
        self.assertEqual(select_date([sub, cpu], review)["year"], 1965)
        with self.assertRaises(ValueError):
            select_date([candidate("submission", "2024", "result", "reported")], review)
        self.assertEqual(select_date([sub], dict(review, decision="accept"))["year"], 2025)

    def test_cpu_match_requires_clock_and_preserves_manufacturer(self):
        proxy = dict(
            configuration_id="known",
            system="PC",
            cpu="AMD 5x86",
            clock_mhz="133",
            release_date="1995",
            source_url="source",
            notes="reviewed",
        )
        c = CPUChronology([proxy])
        row = dict(configuration_id="other", system="Clone", cpu="AMD 5x86", clock_mhz=133)
        self.assertEqual(c.lookup(row)[0]["year"], 1995)
        self.assertEqual(c.lookup(dict(row, cpu="Cyrix 5x86")), [])
        self.assertEqual(c.lookup(dict(row, clock_mhz="")), [])
        with self.assertRaises(ValueError):
            c.lookup(dict(row, configuration_id="known", cpu="Cyrix 5x86"))
