"""Table conversion protects OCR numbers and layout from silent losses."""

import unittest

from cpushowspeed.docir_table import (
    TableCell,
    TableConversionError,
    TableProjection,
    convert_html_table,
    render_markdown_table,
)


class TableConversionTests(unittest.TestCase):
    def test_explicit_header_and_numeric_cells(self):
        result = convert_html_table(
            "<table><tr><th>Model</th><th>Time (µs)</th></tr>" "<tr><td>11/70</td><td>0.05</td></tr></table>"
        )
        self.assertEqual(
            render_markdown_table(result),
            "| Model | Time (µs) |\n| --- | --- |\n| 11/70 | 0.05 |",
        )
        self.assertEqual(result.cells[-1].text, "0.05")

    def test_no_header_keeps_first_row_as_data(self):
        result = convert_html_table("<table><tr><td>1</td><td>2</td></tr><tr><td>3</td><td>4</td></tr></table>")
        self.assertEqual(render_markdown_table(result), "|  |  |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |")

    def test_spans_remain_in_cell_records(self):
        result = convert_html_table(
            "<table><tr><th colspan='2'>Timing</th></tr>"
            "<tr><td rowspan='2'>ADD</td><td>1.5</td></tr><tr><td>2.5</td></tr></table>"
        )
        self.assertEqual((result.row_count, result.column_count), (3, 2))
        self.assertEqual((result.cells[0].rowspan, result.cells[0].colspan), (1, 2))
        self.assertEqual((result.cells[1].rowspan, result.cells[1].colspan), (2, 1))
        self.assertIn("|  | 2.5 |", render_markdown_table(result))

    def test_row_fully_covered_by_rowspan(self):
        result = convert_html_table("<table><tr><td rowspan='2'>A</td></tr><tr></tr></table>")
        self.assertEqual(result.row_count, 2)
        self.assertIn("|  |", render_markdown_table(result))

    def test_inline_superscript_and_pipe(self):
        result = convert_html_table("<table><tr><th>Rate</th></tr><tr><td>1|2<sup>1</sup></td></tr></table>")
        self.assertEqual(result.cells[-1].text, "1|2<sup>1</sup>")
        self.assertIn(r"1\|2<sup>1</sup>", render_markdown_table(result))

    def test_inline_math_unit_keeps_delimiters(self):
        table = convert_html_table(r"<table><tr><th>Rate</th></tr><tr><td>2.5 <math>\mu</math>sec./wd.</td></tr></table>")
        self.assertEqual(table.cells[-1].text, r"2.5 $\mu$sec./wd.")
        self.assertIn(r"2.5 $\mu$sec./wd.", render_markdown_table(table))

    def test_serialized_table_regenerates_markdown(self):
        original = convert_html_table("<table><caption>Timing</caption><tr><td>ADD</td><td>1.5</td></tr></table>")
        record = original.as_dict()
        self.assertNotIn("markdown", record)
        self.assertNotIn("synthetic_header", record)
        restored = TableProjection(
            cells=tuple(TableCell(**cell) for cell in record["cells"]),
            row_count=record["row_count"],
            column_count=record["column_count"],
            caption=record["caption"],
        )
        self.assertEqual(render_markdown_table(restored), render_markdown_table(original))

    def test_malformed_and_image_tables_fail_explicitly(self):
        for html in (
            "<table><tr><td>x</tr></table>",
            "<table><tr><td rowspan='2'>x</td></tr></table>",
            "<table><tr><td><img src='x.png'></td></tr></table>",
            "<table><tr><td><table><tr><td>x</td></tr></table></td></tr></table>",
        ):
            with self.subTest(html=html), self.assertRaises(TableConversionError):
                convert_html_table(html)


if __name__ == "__main__":
    unittest.main()
