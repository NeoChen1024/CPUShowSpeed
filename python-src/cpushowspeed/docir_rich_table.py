"""Versioned rich table blocks and a deliberately simplified reading projection."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser

from cpushowspeed.docir_table import (
    MAX_GRID_SLOTS,
    MAX_TABLE_COLUMNS,
    MAX_TABLE_ROWS,
    TableCell,
    TableConversionError,
    TableProjection,
    _clean,
    _render_row,
    render_markdown_table,
)

MAX_DEPTH = 32
MAX_NODES = 100_000
VOID = {"img", "br", "hr", "meta", "link", "input", "col", "wbr"}


@dataclass
class Element:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)


class TreeParser(HTMLParser):
    """Strict nesting, including table tags; never silently repair broken cells."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("root")
        self.stack = [self.root]
        self.nodes = 0

    def handle_starttag(self, tag, attrs):
        self.nodes += 1
        if self.nodes > MAX_NODES or len(self.stack) >= MAX_DEPTH:
            raise TableConversionError("HTML node/depth limit exceeded")
        e = Element(tag, dict(attrs))
        self.stack[-1].children.append(e)
        if tag not in VOID:
            self.stack.append(e)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if len(self.stack) == 1 or self.stack[-1].tag != tag:
            raise TableConversionError(f"unbalanced HTML end tag: {tag}")
        self.stack.pop()

    def handle_data(self, data):
        self.nodes += 1
        if self.nodes > MAX_NODES:
            raise TableConversionError("HTML node limit exceeded")
        self.stack[-1].children.append(data)


def _span(e, name):
    try:
        n = int(e.attrs.get(name, "1"))
    except (TypeError, ValueError) as exc:
        raise TableConversionError(f"invalid {name}") from exc
    if not 1 <= n <= MAX_TABLE_ROWS:
        raise TableConversionError(f"invalid {name}")
    return n


def _content(children, budget):
    result, text = [], []

    def flush():
        value = _clean(text)
        if value:
            result.append({"kind": "text", "text": value})
        text.clear()

    def visit(item):
        if isinstance(item, str):
            text.append(escape(item, quote=False))
            return
        tag = item.tag
        if tag == "table":
            flush()
            result.append(_table(item, budget))
        elif tag == "img":
            flush()
            result.append(
                {
                    "kind": "image",
                    "source_uri": item.attrs.get("src"),
                    "image_blake3": None,
                    "bbox_px": None,
                    "alt": item.attrs.get("alt"),
                    "asset_status": "unresolved",
                }
            )
        else:
            if tag in {"tr", "td", "th", "thead", "tbody", "tfoot", "caption"}:
                raise TableConversionError(f"misplaced {tag}")
            prefix, suffix = {"sup": ("<sup>", "</sup>"), "sub": ("<sub>", "</sub>"), "math": ("$", "$")}.get(tag, ("", ""))
            if tag in {"br", "p", "div", "li", "hr"}:
                text.append("\n")
            text.append(prefix)
            for child in item.children:
                visit(child)
            text.append(suffix)
            if tag in {"p", "div", "li"}:
                text.append("\n")

    for item in children:
        visit(item)
    flush()
    return result


def _table(element, budget):
    rows, groups, caption = [], [], None
    for child in element.children:
        if isinstance(child, str):
            if child.strip():
                raise TableConversionError("text directly inside table needs an explicit cell")
            continue
        if child.tag == "caption":
            if caption is not None:
                raise TableConversionError("multiple table captions")
            parts = _content(child.children, budget)
            if any(p["kind"] != "text" for p in parts):
                raise TableConversionError("rich caption requires explicit support")
            caption = "<br>".join(p["text"] for p in parts)
        elif child.tag == "tr":
            rows.append(child)
        elif child.tag in {"thead", "tbody", "tfoot"}:
            start = len(rows)
            for row in child.children:
                if isinstance(row, str) and not row.strip():
                    continue
                if not isinstance(row, Element) or row.tag != "tr":
                    raise TableConversionError("invalid row group")
                rows.append(row)
            groups.append({"kind": child.tag, "start_row": start, "row_count": len(rows) - start})
        elif child.tag == "colgroup":
            if any(isinstance(c, str) and c.strip() or isinstance(c, Element) and c.tag != "col" for c in child.children):
                raise TableConversionError("invalid colgroup")
        elif child.tag != "col":
            raise TableConversionError(f"unsupported table child: {child.tag}")
    if not 1 <= len(rows) <= MAX_TABLE_ROWS:
        raise TableConversionError("invalid table row count")
    cells, occupied, columns = [], set(), 0
    for r, row in enumerate(rows):
        col = 0
        for child in row.children:
            if isinstance(child, str) and not child.strip():
                continue
            if not isinstance(child, Element) or child.tag not in {"td", "th"}:
                raise TableConversionError("invalid row child")
            while (r, col) in occupied:
                col += 1
            rs, cs = _span(child, "rowspan"), _span(child, "colspan")
            if r + rs > len(rows) or col + cs > MAX_TABLE_COLUMNS:
                raise TableConversionError("cell span outside table limits")
            budget[0] += rs * cs
            if budget[0] > MAX_GRID_SLOTS:
                raise TableConversionError("aggregate grid budget exceeded")
            for rr in range(r, r + rs):
                for cc in range(col, col + cs):
                    if (rr, cc) in occupied:
                        raise TableConversionError("overlapping table spans")
                    occupied.add((rr, cc))
            cells.append(
                {
                    "row": r,
                    "column": col,
                    "rowspan": rs,
                    "colspan": cs,
                    "header": child.tag == "th",
                    "content": _content(child.children, budget),
                }
            )
            col += cs
            columns = max(columns, col)
    if columns == 0 or len(rows) * columns > MAX_GRID_SLOTS:
        raise TableConversionError("invalid table grid")
    return {
        "kind": "table",
        "row_count": len(rows),
        "column_count": columns,
        "caption": caption,
        "row_groups": groups,
        "cells": cells,
    }


def convert_rich_table(html: str) -> dict:
    if not isinstance(html, str) or len(html) > 8_000_000:
        raise TableConversionError("HTML input limit exceeded")
    parser = TreeParser()
    parser.feed(html)
    parser.close()
    if len(parser.stack) != 1:
        raise TableConversionError("unclosed HTML tags")
    content = _content(parser.root.children, [0])
    if not any(x["kind"] == "table" for x in content):
        raise TableConversionError("missing table")
    block = {"table_schema_version": 2, "content": content}
    validate_rich_table(block)
    return block


def validate_rich_table(block):
    """Validate stored JSON before traversal/rendering, with aggregate bounds."""
    if block.get("table_schema_version") != 2:
        raise TableConversionError("unsupported table schema version")
    nodes = slots = 0

    def integer(x):
        return type(x) is int

    def visit(content, depth):
        nonlocal nodes, slots
        if depth > MAX_DEPTH or not isinstance(content, list):
            raise TableConversionError("invalid content/depth")
        for node in content:
            nodes += 1
            if nodes > MAX_NODES or not isinstance(node, dict):
                raise TableConversionError("invalid node/budget")
            kind = node.get("kind")
            if kind == "text":
                if not isinstance(node.get("text"), str):
                    raise TableConversionError("invalid text")
            elif kind == "image":
                if node.get("asset_status") not in {"unresolved", "resolved"}:
                    raise TableConversionError("invalid image status")
                for key in ("source_uri", "alt", "image_blake3"):
                    if node.get(key) is not None and not isinstance(node[key], str):
                        raise TableConversionError("invalid image metadata")
                digest = node.get("image_blake3")
                if digest is not None and (len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)):
                    raise TableConversionError("invalid image hash")
                if (node["asset_status"] == "resolved") != bool(digest):
                    raise TableConversionError("inconsistent image resolution")
            elif kind == "table":
                nr, nc = node.get("row_count"), node.get("column_count")
                if not integer(nr) or not integer(nc) or not 1 <= nr <= MAX_TABLE_ROWS or not 1 <= nc <= MAX_TABLE_COLUMNS:
                    raise TableConversionError("invalid table dimensions")
                slots += nr * nc
                if slots > MAX_GRID_SLOTS:
                    raise TableConversionError("aggregate grid budget exceeded")
                occupied = set()
                cells = node.get("cells")
                if not isinstance(cells, list) or not cells:
                    raise TableConversionError("missing cells")
                if node.get("caption") is not None and not isinstance(node["caption"], str):
                    raise TableConversionError("invalid caption")
                for cell in cells:
                    nodes += 1
                    if nodes > MAX_NODES or not isinstance(cell, dict):
                        raise TableConversionError("invalid cell/node budget")
                    vals = [cell.get(k) for k in ("row", "column", "rowspan", "colspan")]
                    if not all(integer(v) for v in vals) or type(cell.get("header")) is not bool:
                        raise TableConversionError("invalid cell coordinates/header")
                    r, c, rs, cs = vals
                    if min(r, c) < 0 or min(rs, cs) < 1 or r + rs > nr or c + cs > nc:
                        raise TableConversionError("invalid stored span")
                    for rr in range(r, r + rs):
                        for cc in range(c, c + cs):
                            if (rr, cc) in occupied:
                                raise TableConversionError("overlapping stored spans")
                            occupied.add((rr, cc))
                    visit(cell.get("content"), depth + 1)
                end = 0
                if not isinstance(node.get("row_groups", []), list):
                    raise TableConversionError("invalid row groups")
                for group in node.get("row_groups", []):
                    if not isinstance(group, dict):
                        raise TableConversionError("invalid row group")
                    start, count = group.get("start_row"), group.get("row_count")
                    if (
                        group.get("kind") not in {"thead", "tbody", "tfoot"}
                        or not integer(start)
                        or not integer(count)
                        or start < end
                        or count < 0
                        or start + count > nr
                    ):
                        raise TableConversionError("invalid row group")
                    end = start + count
            else:
                raise TableConversionError("unknown content node")

    visit(block.get("content"), 0)
    if nodes > MAX_NODES:
        raise TableConversionError("node budget exceeded")


def walk_content(block):
    """Yield all rich nodes in reading order; v1 returns the original block."""
    yield block
    if block.get("table_schema_version") == 2:
        validate_rich_table(block)

        def walk(items):
            for node in items:
                yield node
                if node["kind"] == "table":
                    for cell in node["cells"]:
                        yield from walk(cell["content"])

        yield from walk(block["content"])


def render_table_block(block):
    """Read either v1 or v2. Nested tables are emitted with cell-path labels."""
    if "table_schema_version" not in block:
        table = block["table"]
        return render_markdown_table(
            TableProjection(
                tuple(TableCell(**x) for x in table["cells"]), table["row_count"], table["column_count"], table.get("caption")
            )
        )
    validate_rich_table(block)

    def image_text(n):
        alt = escape(n.get("alt") or "no OCR alt text", quote=False).replace("\n", "<br>")
        return (
            f"[Image {n['asset_status']}; unverified OCR alt: {alt}"
            + (f"; asset {n['image_blake3']}" if n.get("image_blake3") else "")
            + "]"
        )

    def table_text(n, label):
        grid = [[""] * n["column_count"] for _ in range(n["row_count"])]
        header = [False] * n["column_count"]
        nested = []
        for cell in n["cells"]:
            text = []
            k = 0
            for child in cell["content"]:
                if child["kind"] == "text":
                    text.append(child["text"])
                elif child["kind"] == "image":
                    text.append(image_text(child))
                else:
                    k += 1
                    name = f"{label}.r{cell['row']+1}.c{cell['column']+1}.t{k}"
                    text.append(f"[Table {name}]")
                    nested.append(table_text(child, name))
            grid[cell["row"]][cell["column"]] = "<br>".join(text).replace("\n", "<br>")
            if cell["row"] == 0:
                for c in range(cell["column"], cell["column"] + cell["colspan"]):
                    header[c] = cell["header"]
        natural = all(header)
        rows = [grid[0] if natural else [""] * n["column_count"], ["---"] * n["column_count"]] + (grid[1:] if natural else grid)
        result = (
            f"Table {label}\n\n" + ((n["caption"] + "\n\n") if n.get("caption") else "") + "\n".join(_render_row(r) for r in rows)
        )
        return "\n\n".join([result] + nested)

    pieces = []
    k = 0
    for node in block["content"]:
        if node["kind"] == "text":
            pieces.append(node["text"])
        elif node["kind"] == "image":
            pieces.append(image_text(node))
        else:
            k += 1
            pieces.append(table_text(node, f"T{k}"))
    return "\n\n".join(pieces)
