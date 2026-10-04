"""Materialize SQLite image captions into published DocIR, one document at a time."""

from __future__ import annotations

import fcntl
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import ExitStack, closing
from pathlib import Path

import click
from cpushowspeed.docir_rich_table import walk_content
from cpushowspeed.document_report import collect_ocr_stats
from cpushowspeed.documents import DEFAULT_DATABASE
from cpushowspeed.ocr import CONSOLE, select_inventory
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)


def backfill_document(path: Path, expected_pages: int, catalog: sqlite3.Connection, dry_run: bool = False) -> tuple[int, int]:
    """Return (image occurrences with saved captions, changed captions).

    Validate the whole document before replacing it. Keep unchanged lines verbatim;
    only one page and its caption lookups need to be held in memory.
    """
    matched = changed = pages = 0
    temporary = None
    try:
        with (
            path.open(encoding="utf-8") as source,
            tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
            ) as target,
        ):
            temporary = Path(target.name)
            os.fchmod(target.fileno(), stat.S_IMODE(path.stat().st_mode))
            for pages, line in enumerate(source, 1):
                page = json.loads(line)
                if page.get("page") != pages or page.get("status") not in {"ok", "blank"}:
                    raise ValueError(f"invalid page {pages}")
                blocks = page["blocks"]
                if not isinstance(blocks, list) or any(not isinstance(block, dict) for block in blocks):
                    raise ValueError(f"invalid blocks on page {pages}")
                blocks = [node for block in blocks for node in walk_content(block)]
                digests = list({block["image_blake3"] for block in blocks if block.get("image_blake3")})
                captions = {}
                for start in range(0, len(digests), 500):
                    batch = digests[start : start + 500]
                    placeholders = ",".join("?" for _ in batch)
                    for digest, caption in catalog.execute(
                        f"SELECT image_blake3, caption FROM captions WHERE image_blake3 IN ({placeholders})", batch
                    ):
                        if isinstance(caption, str) and caption.strip():
                            captions[digest] = caption
                page_changed = False
                for block in blocks:
                    caption = captions.get(block.get("image_blake3"))
                    if caption is not None:
                        matched += 1
                        if block.get("caption") != caption:
                            block["caption"] = caption
                            changed += 1
                            page_changed = True
                target.write(json.dumps(page, ensure_ascii=False, separators=(",", ":")) + "\n" if page_changed else line)
            if pages != expected_pages:
                raise ValueError(f"expected {expected_pages} pages, found {pages}")
            if changed and not dry_run:
                target.flush()
                os.fsync(target.fileno())
        if changed and not dry_run:
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        return matched, changed
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@click.command("backfill-captions")
@click.option(
    "--database", type=click.Path(path_type=Path, exists=True, dir_okay=False), default=DEFAULT_DATABASE, show_default=True
)
@click.option("--output-root", type=click.Path(path_type=Path, exists=True, file_okay=False), required=True)
@click.option(
    "--caption-database",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="Defaults to OUTPUT_ROOT/ImagePool/catalog.sqlite.",
)
@click.option("--file-list", type=click.Path(path_type=Path, exists=True, dir_okay=False))
@click.option("--all", "all_documents", is_flag=True, help="Select all inventoried PDFs with published DocIR.")
@click.option("--dry-run", is_flag=True, help="Validate and count changes without replacing DocIR files.")
def backfill_captions_command(
    database: Path,
    output_root: Path,
    caption_database: Path | None,
    file_list: Path | None,
    all_documents: bool,
    dry_run: bool,
) -> None:
    """Copy saved image captions into published DocIR. Safe to repeat."""
    if (file_list is None) == (not all_documents):
        raise click.ClickException("select either --file-list or --all")
    output = output_root.resolve()
    caption_database = caption_database or output / "ImagePool" / "catalog.sqlite"
    if not caption_database.is_file():
        raise click.ClickException(f"caption database does not exist: {caption_database}")
    try:
        with ExitStack() as stack:
            # OCR uses this same lock; it also serializes competing backfills.
            lock = stack.enter_context((output / ".ocr.lock").open("a"))
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise click.ClickException(f"another OCR or backfill process is using {output}") from exc
            inventory = stack.enter_context(closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)))
            inventory.row_factory = sqlite3.Row
            catalog = stack.enter_context(closing(sqlite3.connect(f"{caption_database.resolve().as_uri()}?mode=ro", uri=True)))
            catalog.execute("BEGIN")  # One consistent caption snapshot for the entire invocation.
            catalog.execute("SELECT image_blake3, caption FROM captions LIMIT 0")
            root = inventory.execute("SELECT value FROM metadata WHERE key='root'").fetchone()
            run = inventory.execute("SELECT run_id FROM ocr_runs WHERE output_root=?", (str(output),)).fetchone()
            if root is None or run is None:
                raise click.ClickException("inventory has no OCR run for this output root")
            selected = select_inventory(inventory, Path(root["value"]), file_list, "", None)
            stats = collect_ocr_stats(inventory, run["run_id"], output, selected)
            CONSOLE.print(
                f"Selected {len(selected):,} PDFs; {stats.published_documents:,} published documents / {stats.published_pages:,} pages."
            )
            matched = changed = updated = 0
            with Progress(
                TextColumn("DocIR pages"), BarColumn(), MofNCompleteColumn(), TimeRemainingColumn(), console=CONSOLE
            ) as progress:
                task = progress.add_task("Backfill", total=stats.published_pages)
                for path, pages in stats.published:
                    try:
                        found, edits = backfill_document(path, pages, catalog, dry_run)
                    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                        raise click.ClickException(f"cannot backfill {path}: {exc}") from exc
                    matched += found
                    changed += edits
                    updated += bool(edits)
                    progress.advance(task, pages)
            action = "Would update" if dry_run else "Updated"
            CONSOLE.print(
                f"{action} {updated:,} documents / {changed:,} captions; {matched:,} image occurrences have saved captions."
            )
    except (OSError, sqlite3.DatabaseError) as exc:
        raise click.ClickException(str(exc)) from exc
