"""Parse OCR HTML tables into span-preserving cells; render Markdown on demand."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from html.parser import HTMLParser

MAX_TABLE_ROWS = 4096
MAX_TABLE_COLUMNS = 512
MAX_GRID_SLOTS = 1_000_000


class TableConversionError(ValueError):
    """A table cannot be converted without losing or inventing cells."""


@dataclass(frozen=True)
class TableCell:
    row: int
    column: int
    rowspan: int
    colspan: int
    text: str
    header: bool


@dataclass(frozen=True)
class TableProjection:
    cells: tuple[TableCell, ...]
    row_count: int
    column_count: int
    caption: str | None

    def as_dict(self) -> dict:
        return {
            "cells": [asdict(cell) for cell in self.cells],
            "row_count": self.row_count,
            "column_count": self.column_count,
            "caption": self.caption,
        }


@dataclass(frozen=True)
class _ParsedCell:
    text: str
    rowspan: int
    colspan: int
    header: bool


def _clean(parts: list[str]) -> str:
    lines = [" ".join(line.split()) for line in "".join(parts).splitlines()]
    return "<br>".join(line for line in lines if line)


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.seen_table = False
        self.in_table = False
        self.rows: list[list[_ParsedCell]] = []
        self.row: list[_ParsedCell] | None = None
        self.cell_parts: list[str] | None = None
        self.cell_tag: str | None = None
        self.rowspan = 1
        self.colspan = 1
        self.caption_parts: list[str] | None = None
        self.caption: str | None = None

    @staticmethod
    def _span(attrs: dict[str, str | None], name: str) -> int:
        value = attrs.get(name)
        if value is None:
            return 1
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise TableConversionError(f"invalid {name}: {value!r}") from exc
        if number < 1 or number > MAX_TABLE_ROWS:
            raise TableConversionError(f"invalid {name}: {value!r}")
        return number

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = dict(attrs)
        if tag == "table":
            if self.seen_table:
                raise TableConversionError("expected exactly one non-nested table")
            self.seen_table = True
            self.in_table = True
        elif not self.in_table:
            return
        elif tag == "caption":
            if self.caption_parts is not None or self.row is not None:
                raise TableConversionError("misplaced or nested table caption")
            self.caption_parts = []
        elif tag == "tr":
            if self.row is not None or self.cell_parts is not None:
                raise TableConversionError("nested or unclosed table row")
            self.row = []
        elif tag in {"td", "th"}:
            if self.row is None or self.cell_parts is not None:
                raise TableConversionError("cell outside row or nested cell")
            self.cell_parts = []
            self.cell_tag = tag
            self.rowspan = self._span(attributes, "rowspan")
            self.colspan = self._span(attributes, "colspan")
        elif self.cell_parts is not None:
            if tag == "img":
                raise TableConversionError("image in table cell needs an explicit asset mapping")
            if tag == "br":
                self.cell_parts.append("\n")
            elif tag in {"p", "div", "li"}:
                if self.cell_parts and self.cell_parts[-1] != "\n":
                    self.cell_parts.append("\n")
            elif tag in {"sup", "sub"}:
                self.cell_parts.append(f"<{tag}>")
            elif tag == "math":
                self.cell_parts.append("$")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"br", "img"}:
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"}:
            if self.cell_parts is None or self.row is None or tag != self.cell_tag:
                raise TableConversionError("unmatched table cell end tag")
            self.row.append(_ParsedCell(_clean(self.cell_parts), self.rowspan, self.colspan, tag == "th"))
            self.cell_parts = None
            self.cell_tag = None
        elif tag == "tr":
            if self.row is None or self.cell_parts is not None:
                raise TableConversionError("unmatched or unfinished table row")
            self.rows.append(self.row)
            if len(self.rows) > MAX_TABLE_ROWS:
                raise TableConversionError("table has too many rows")
            self.row = None
        elif tag == "caption":
            if self.caption_parts is None:
                raise TableConversionError("unmatched table caption")
            self.caption = _clean(self.caption_parts) or None
            self.caption_parts = None
        elif tag == "table":
            if not self.in_table or self.row is not None or self.cell_parts is not None or self.caption_parts is not None:
                raise TableConversionError("unbalanced table tags")
            self.in_table = False
        elif self.cell_parts is not None:
            if tag in {"p", "div", "li"}:
                if self.cell_parts and self.cell_parts[-1] != "\n":
                    self.cell_parts.append("\n")
            elif tag in {"sup", "sub"}:
                self.cell_parts.append(f"</{tag}>")
            elif tag == "math":
                self.cell_parts.append("$")

    def handle_data(self, data: str) -> None:
        if self.cell_parts is not None:
            self.cell_parts.append(data)
        elif self.caption_parts is not None:
            self.caption_parts.append(data)
        elif data.strip() and not self.in_table:
            raise TableConversionError("content outside table must be converted as a separate block")

    def finish(self) -> tuple[list[list[_ParsedCell]], str | None]:
        self.close()
        if not self.seen_table or self.in_table or self.row is not None or self.cell_parts is not None:
            raise TableConversionError("missing or unclosed table")
        if self.caption_parts is not None or not self.rows or not any(self.rows):
            raise TableConversionError("missing cells or unclosed caption")
        return self.rows, self.caption


def _render_row(row: list[str]) -> str:
    return "| " + " | ".join(cell.replace("|", r"\|") for cell in row) + " |"


def convert_html_table(html: str) -> TableProjection:
    """Parse one table into source cells and spans without storing Markdown."""
    parser = _TableParser()
    try:
        parser.feed(html)
        rows, caption = parser.finish()
    except TableConversionError:
        raise
    except Exception as exc:
        raise TableConversionError(f"cannot parse table: {exc}") from exc

    occupied: list[list[TableCell | None]] = [[] for _ in rows]
    cells: list[TableCell] = []
    for row_index, source_row in enumerate(rows):
        column = 0
        for source in source_row:
            while column < len(occupied[row_index]) and occupied[row_index][column] is not None:
                column += 1
            if row_index + source.rowspan > len(rows):
                raise TableConversionError("rowspan extends beyond the table")
            if column + source.colspan > MAX_TABLE_COLUMNS:
                raise TableConversionError("table has too many columns")
            cell = TableCell(row_index, column, source.rowspan, source.colspan, source.text, source.header)
            for target_row in range(row_index, row_index + source.rowspan):
                while len(occupied[target_row]) < column + source.colspan:
                    occupied[target_row].append(None)
                for target_column in range(column, column + source.colspan):
                    if occupied[target_row][target_column] is not None:
                        raise TableConversionError("overlapping table spans")
                    occupied[target_row][target_column] = cell
            cells.append(cell)
            column += source.colspan

    columns = max(map(len, occupied))
    if columns == 0:
        raise TableConversionError("table contains no cells")
    if len(rows) * columns > MAX_GRID_SLOTS:
        raise TableConversionError("table grid is too large")
    return TableProjection(tuple(cells), len(rows), columns, caption)


def render_markdown_table(table: TableProjection) -> str:
    """Generate a pipe-table reading view from stored cells and shape."""
    if (
        table.row_count < 1
        or table.row_count > MAX_TABLE_ROWS
        or table.column_count < 1
        or table.column_count > MAX_TABLE_COLUMNS
        or table.row_count * table.column_count > MAX_GRID_SLOTS
    ):
        raise TableConversionError("invalid stored table dimensions")
    occupied: list[list[TableCell | None]] = [[None] * table.column_count for _ in range(table.row_count)]
    for cell in table.cells:
        if (
            cell.row < 0
            or cell.column < 0
            or cell.row + cell.rowspan > table.row_count
            or cell.column + cell.colspan > table.column_count
        ):
            raise TableConversionError("stored table cell lies outside the table grid")
        for row in range(cell.row, cell.row + cell.rowspan):
            for column in range(cell.column, cell.column + cell.colspan):
                if occupied[row][column] is not None:
                    raise TableConversionError("stored table cells overlap")
                occupied[row][column] = cell

    grid = [
        [
            cell.text if cell is not None and cell.row == row and cell.column == column else ""
            for column, cell in enumerate(occupied[row])
        ]
        for row in range(table.row_count)
    ]
    natural_header = all(cell is not None and cell.header for cell in occupied[0])
    header = grid[0] if natural_header else [""] * table.column_count
    body = grid[1:] if natural_header else grid
    markdown_rows = [_render_row(header), _render_row(["---"] * table.column_count)]
    markdown_rows.extend(_render_row(row) for row in body)
    markdown = "\n".join(markdown_rows)
    return table.caption + "\n\n" + markdown if table.caption else markdown
