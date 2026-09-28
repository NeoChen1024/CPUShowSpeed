import unittest

from cpushowspeed.mix_timeline import mix_dates
from cpushowspeed.timeline_dates import candidate


class Chronology:
    def __init__(self, dates=()):
        self.dates = list(dates)

    def lookup(self, row):
        return self.dates


class MixTimelineDatesTests(unittest.TestCase):
    def setUp(self):
        self.source = dict(introduction_year_raw="1968", source_url="source")
        self.row = dict(system="DEC PDP 8E")
        self.rule = dict(
            system_regex=r"PDP 8E",
            year="1970",
            source_url="review",
            method="reviewed_intro",
            notes="Correct source year",
            fallback="",
        )

    def test_reviewed_rule_retains_rejected_source_date(self):
        r = mix_dates(self.source, self.row, Chronology(), [self.rule], [])
        self.assertEqual(r["year"], 1970)
        self.assertFalse(next(c for c in r["date_candidates"] if c["year"] == 1968)["eligible"])

    def test_cpu_precedes_model_date(self):
        c = candidate("cpu", "1967", "cpu-source", "reviewed_cpu")
        r = mix_dates(self.source, self.row, Chronology([c]), [self.rule], [])
        self.assertEqual(r["date_kind"], "cpu")
        self.assertEqual(r["year"], 1967)

    def test_unresolved_rule_does_not_restore_source_date(self):
        r = mix_dates(self.source, self.row, Chronology(), [dict(self.rule, year="")], [])
        self.assertEqual(r["date_kind"], "unknown")


class CombinedMixIntervalTests(unittest.TestCase):
    def test_aligned_anticorrelated_draws_cancel_and_single_fallback(self):
        import numpy as np
        from cpushowspeed.mix_timeline import combined_mixes

        metrics = ["InstructionMix:Gibson_KIPS", "InstructionMix:ADP_KIPS"]

        def row(suffix, metric):
            return dict(
                source_record_ids=["source:table:1:" + suffix],
                source_snapshot_sha256="hash",
                source_url="source",
                benchmark_id=suffix,
                system="test",
                configuration="same",
                year=1960,
                year_low=1960,
                year_high=1960,
                scores={metric: 100},
                vaxen=100,
                limitation="",
            )

        rows = [row("Gibson Mix", metrics[0]), row("ADP Mix", metrics[1])]
        result = combined_mixes(rows, np.array([[-1.0, 1.0], [1.0, -1.0]]), metrics)[0]
        self.assertAlmostEqual(result["ci95_low"], 100)
        self.assertAlmostEqual(result["ci95_high"], 100)
        self.assertEqual(result["observation_count"], 2)
        single = combined_mixes(rows[:1], np.zeros((2, 2)), metrics)[0]
        self.assertEqual(single["observation_count"], 1)
        self.assertAlmostEqual(single["vaxen"], 100)
