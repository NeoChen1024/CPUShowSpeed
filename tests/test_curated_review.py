"""Review rows validate against schema.json and resolve their selectors at build time."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cpushowspeed import curated_review
from cpushowspeed.curated import load_schema, row_validator


def review(**fields):
    return dict(reason="checked", reviewed_on="2026-10-02", legacy_ids=["test"], **fields)


DATE = review(
    review_id="rev:test/date",
    target_kind="result_date",
    target=dict(scope="classical:a", system="Elliott 905"),
    field="table_year",
    decision="reject",
)
PAIR = review(
    review_id="rev:test/pair",
    target_kind="result_pair",
    target=dict(left=dict(result_id="spec:cpu92:speed:x"), right=dict(result_id="spec:cpu95:speed:missing")),
    decision="accept",
)
LINK = review(
    review_id="rev:test/link",
    target_kind="system_link",
    target=dict(left=dict(scope="mix:m", system="CDC 6600"), right=dict(scope="classical:a", system="Control Data 6600")),
    decision="needs_review",
)


class ReviewSchemaTests(unittest.TestCase):
    def setUp(self):
        schema = load_schema()
        self.validator = row_validator(schema, schema["x-tables"]["review"]["row"])

    def test_valid_rows(self):
        for row in (DATE, PAIR, LINK):
            self.assertEqual(list(self.validator.iter_errors(row)), [], row["review_id"])

    def test_field_only_on_result_dates(self):
        self.assertTrue(list(self.validator.iter_errors({k: v for k, v in DATE.items() if k != "field"})))
        self.assertTrue(list(self.validator.iter_errors(dict(PAIR, field="table_year"))))

    def test_selector_shapes(self):
        self.assertTrue(list(self.validator.iter_errors(dict(DATE, target=dict(scope="classical:a")))))
        self.assertTrue(
            list(self.validator.iter_errors(dict(LINK, target=dict(left=dict(result_id="x"), right=LINK["target"]["right"]))))
        )


class BuildReviewTests(unittest.TestCase):
    def test_selectors_resolve_and_misses_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / "results.jsonl"
            rows = [
                dict(result_id="classical:a:1:MWIPS", scope="classical:a", system="Elliott 905"),
                dict(result_id="classical:a:1:MWIPS_DP", scope="classical:a", system="Elliott 905"),
                dict(result_id="spec:cpu92:speed:x", scope="spec:cpu92", system="HP 715/100"),
            ]
            results.write_text("".join(json.dumps(r) + "\n" for r in rows))
            db = sqlite3.connect(":memory:")
            db.execute("CREATE TABLE hardware_record (scope TEXT, system TEXT, system_id TEXT)")
            db.executemany(
                "INSERT INTO hardware_record VALUES (?, ?, ?)",
                [("mix:m", "CDC 6600", "sys:cdc6600"), ("classical:a", "Control Data 6600", "sys:cdc6600")],
            )
            with mock.patch.object(curated_review, "RESULTS", results):
                meta = curated_review.build_reviews(db, dict(review=[DATE, PAIR, LINK]))
            self.assertEqual(
                curated_review.rejected_dates(db),
                {("classical:a:1:MWIPS", "table_year"): "rev:test/date", ("classical:a:1:MWIPS_DP", "table_year"): "rev:test/date"},
            )
            findings = db.execute("SELECT review_id, finding FROM review_finding ORDER BY 1").fetchall()
            self.assertEqual(findings, [("rev:test/link", "unreviewed_link_merged_by_rule"), ("rev:test/pair", "target_unmatched")])
            self.assertEqual(meta["reviews:result_pair:accept"], "1")
            self.assertEqual(db.execute("SELECT same_model FROM review_system_link").fetchone(), (1,))


if __name__ == "__main__":
    unittest.main()
