"""Rebuild derived tables from immutable OCR chunks; export reading views."""

from __future__ import annotations

import fcntl
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from itertools import zip_longest
from pathlib import Path

import click
from cpushowspeed.docir_rich_table import (
    convert_rich_table,
    render_table_block,
    validate_rich_table,
)
from cpushowspeed.documents import DEFAULT_DATABASE
from cpushowspeed.ocr import _select_inventory


def migrate_document(path, raw_path, expected_pages, expected_hash, relative_pdf, dry_run=False):
    """Validate complete documents, then atomically replace only changed tables."""
    temporary = None
    changed = pages = 0
    try:
        with (
            path.open() as source,
            raw_path.open() as raw,
            tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
            ) as target,
        ):
            temporary = Path(target.name)
            os.fchmod(target.fileno(), stat.S_IMODE(path.stat().st_mode))
            header = json.loads(next(raw))
            if (
                header.get("source_blake3") != expected_hash
                or header.get("pages") != expected_pages
                or header.get("source_pdf") != relative_pdf
            ):
                raise ValueError("raw source identity mismatch")
            for pages, pair in enumerate(zip_longest(source, raw), 1):
                line, raw_line = pair
                if line is None or raw_line is None:
                    raise ValueError("raw/DocIR page count mismatch")
                page, original = json.loads(line), json.loads(raw_line)
                if (
                    page.get("page") != pages
                    or original.get("page") != pages
                    or page.get("status") not in {"ok", "blank"}
                    or page["status"] != original.get("status")
                ):
                    raise ValueError(f"invalid page identity/status at {pages}")
                if len(page["blocks"]) != len(original["chunks"]):
                    raise ValueError(f"block/chunk count mismatch at {pages}")
                edits = 0
                for index, (block, chunk) in enumerate(zip(page["blocks"], original["chunks"])):
                    if block.get("source_label") != chunk.get("label"):
                        raise ValueError(f"block/chunk label mismatch at {pages}/{index}")
                    if chunk["label"] != "Table":
                        continue
                    if block.get("table_schema_version") == 2:
                        validate_rich_table(block)
                        continue
                    converted = convert_rich_table(chunk["content"])
                    replacement = {
                        k: v
                        for k, v in block.items()
                        if k not in {"table", "content", "table_schema_version", "conversion_status", "error"}
                    }
                    replacement.update(converted)
                    if replacement != block:
                        page["blocks"][index] = replacement
                        edits += 1
                changed += edits
                target.write(json.dumps(page, ensure_ascii=False, separators=(",", ":")) + "\n" if edits else line)
            if pages != expected_pages:
                raise ValueError("unexpected page count")
            if changed and not dry_run:
                target.flush()
                os.fsync(target.fileno())
        if changed and not dry_run:
            os.replace(temporary, path)
            descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return changed
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@click.command("migrate-tables")
@click.option(
    "--database", type=click.Path(path_type=Path, exists=True, dir_okay=False), default=DEFAULT_DATABASE, show_default=True
)
@click.option("--output-root", type=click.Path(path_type=Path, exists=True, file_okay=False), required=True)
@click.option("--file-list", type=click.Path(path_type=Path, exists=True, dir_okay=False), required=True)
@click.option("--dry-run", is_flag=True)
def migrate_tables_command(database, output_root, file_list, dry_run):
    """Reconvert selected published DocIR tables from saved raw HTML to v2."""
    output = output_root.resolve()
    edits = updated = 0
    try:
        with (
            (output / ".ocr.lock").open("a") as lock,
            closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as c,
        ):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            c.row_factory = sqlite3.Row
            root = c.execute("SELECT value FROM metadata WHERE key='root'").fetchone()
            run = c.execute("SELECT run_id FROM ocr_runs WHERE output_root=?", (str(output),)).fetchone()
            if root is None or run is None:
                raise ValueError("inventory has no matching OCR run")
            selected = _select_inventory(c, Path(root["value"]), file_list, "", None)
            for row in selected:
                stem = (output / row["relative_path"]).with_suffix("")
                path = stem.with_name(stem.name + ".docir.jsonl")
                raw = stem.with_name(stem.name + ".raw.jsonl")
                n = migrate_document(path, raw, row["pages"], row["blake3"], row["relative_path"], dry_run)
                click.echo(f"{row['relative_path']}: {n} changed table blocks", err=True)
                edits += n
                updated += bool(n)
    except (OSError, ValueError, KeyError, TypeError, StopIteration, sqlite3.DatabaseError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps({"dry_run": dry_run, "updated_documents": updated, "changed_table_blocks": edits}))


@click.command("render-tables")
@click.argument("docir", type=click.Path(path_type=Path, exists=True, dir_okay=False))
@click.option("--page", type=click.IntRange(1), help="One physical PDF page; default is all pages.")
def render_tables_command(docir, page):
    """Render stored v1/v2 table blocks as Markdown to stdout."""
    try:
        with docir.open() as f:
            for line in f:
                record = json.loads(line)
                if page is not None and page != record["page"]:
                    continue
                for i, block in enumerate(record["blocks"]):
                    if block.get("kind") == "table":
                        click.echo(f"## PDF page {record['page']}, block {i}\n")
                        if block.get("conversion_status") == "failed":
                            click.echo("[Unconverted table; inspect original PDF and raw OCR.]\n")
                        else:
                            click.echo(render_table_block(block) + "\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise click.ClickException(str(exc)) from exc
