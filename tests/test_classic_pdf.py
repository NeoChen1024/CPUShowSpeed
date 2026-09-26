"""Published table examples, blank preservation and auditable corrections."""

import unittest

from cpushowspeed.classic_pdf import correct, parse_table, scalar


class ClassicPdfTests(unittest.TestCase):
    def test_single_digit_cells_do_not_merge_and_blanks_stay(self):
        recipe = dict(
            table_id="fixture",
            orientation="metrics_as_rows",
            label_cut=10,
            column_ends=[15, 25, 35],
            columns=[{}, {}, {}],
            start_line=1,
            end_line=2,
            expected_rows=2,
        )
        text = "SPEC92        6         3         4\nSPECbase               12"
        table = parse_table(recipe, text)
        self.assertEqual(table["rows"][0]["cells"], ["6", "3", "4"])
        self.assertEqual(table["rows"][1]["cells"], ["", "12", ""])

    def test_tomari_row_and_missing_scores(self):
        recipe = dict(
            source_id="tomari",
            table_id="results",
            orientation="records_as_rows",
            fields=["machine", "os", "compiler", "Dhrystone", "NPB", "CINT", "CFP"],
            start_line=1,
            end_line=1,
        )
        row = "Intergraph TDZ 2000 GX1     Linux 2.6.33.3       GCC 4.4.4               770.92    0.78    1.87    1.31"
        table = parse_table(recipe, row)
        self.assertEqual(table["rows"][0]["cells"][3:], ["770.92", "0.78", "1.87", "1.31"])

    def test_original_dec_cell_correction_is_explicit(self):
        row = dict(line=59, cells=["333.0"], text_layer_cells=["333.0"])
        tables = [dict(source_id="dec", table_id="p26", rows=[row])]
        patch = dict(source_id="dec", table_id="p26", line=59, column=1, before="333.0", after="330.0")
        correct(tables, [patch])
        self.assertEqual(row["text_layer_cells"], ["333.0"])
        self.assertEqual(row["cells"], ["330.0"])
        with self.assertRaises(ValueError):
            correct(tables, [patch])

    def test_no_imputed_suffixes_or_qualifiers(self):
        self.assertEqual(scalar("364K"), 364000)
        self.assertEqual(scalar("213"), 213)
        for s in ["—", "", "1.9 est.", "(4.9)", "7.*192.", "64/cpu"]:
            self.assertIsNone(scalar(s))


class DecInterpretationTests(unittest.TestCase):
    def test_scoped_policy_preserves_literals(self):
        from cpushowspeed.classic_pdf import interpret_dec

        policy = dict(
            source_id="dec",
            pdf_blake3="hash",
            decision_date="2026-09-26",
            authority="user",
            whetstone=dict(rule_id="mwips", unit="MWIPS", mwips_per_interpreted_unit=1),
            dhrystone=dict(rule_id="missing-k", missing_suffix_multiplier=1000, dmips_divisor=1757),
        )
        base = dict(
            source_id="dec", pdf_blake3="hash", value_status="numeric_literal", pdf_page=27, table="table", row_line=1, column=1
        )
        rows = [
            dict(base, id="a", metric="Dhrystone 1.1 instr/sec", value_raw="213", value=213),
            dict(base, id="b", metric="Dhrystone 1.1 instr/sec", value_raw="248K", value=248000),
            dict(base, id="c", metric="Whetstone KWIPS sp", value_raw="189.4", value=189.4),
            dict(base, id="d", metric="Dhrystone 2.1 instr/sec", value_raw="", value=None, value_status="missing"),
        ]
        out = interpret_dec(rows, policy)
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0]["interpreted_value"], 213000)
        self.assertEqual(out[1]["interpreted_value"], 248000)
        self.assertAlmostEqual(out[2]["normalized_value"], 189.4)
        self.assertEqual(rows[0]["value"], 213)
        self.assertTrue(out[0]["assumed_missing_suffix"])
        rows[0]["pdf_blake3"] = "different"
        with self.assertRaises(ValueError):
            interpret_dec(rows, policy)
