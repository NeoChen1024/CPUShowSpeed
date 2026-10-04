"""Inventory-scoped OCR and optional Image Pool caption progress."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

import click
from cpushowspeed.documents.ocr import select_inventory
from cpushowspeed.documents.rich_table import walk_content
from rich.console import Console
from rich.table import Table


@dataclass
class OCRStats:
    target_documents: int
    target_pages: int
    published_documents: int = 0
    published_pages: int = 0
    staged_pages: int = 0
    not_started: int = 0
    stale_sources: int = 0
    missing_outputs: int = 0
    statuses: Counter = field(default_factory=Counter)
    published: list[tuple[Path, int]] = field(default_factory=list)

    @property
    def completed_pages(self) -> int:
        return self.published_pages + self.staged_pages


@dataclass
class CaptionStats:
    images: int
    initialized: bool
    captioned: int = 0
    skipped: int = 0
    failed: int = 0
    pending: int = 0
    unresolved: int = 0

    @property
    def processed(self) -> int:
        return self.captioned + self.skipped


def _has_table(connection: sqlite3.Connection, name: str) -> bool:
    return connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone() is not None


def _output_paths(output_root: Path, relative: str) -> tuple[Path, Path]:
    stem = output_root / Path(relative).with_suffix("")
    return stem.with_name(stem.name + ".raw.jsonl"), stem.with_name(stem.name + ".docir.jsonl")


def _percent(numerator: int, denominator: int) -> str:
    if not denominator:
        return "n/a"
    if numerator == 0:
        return "0.0%"
    places = 4 if numerator * 1000 < denominator else 2 if numerator * 100 < denominator else 1
    scale = 10**places
    floored = numerator * 100 * scale // denominator
    whole, fractional = divmod(floored, scale)
    return f"{whole}.{fractional:0{places}d}%"


def collect_ocr_stats(connection: sqlite3.Connection, run_id: str, output_root: Path, selected: list[sqlite3.Row]) -> OCRStats:
    stats = OCRStats(len(selected), sum(row["pages"] for row in selected))
    states = {row["relative_path"]: row for row in connection.execute("SELECT * FROM ocr_documents WHERE run_id = ?", (run_id,))}
    for source in selected:
        relative = source["relative_path"]
        state = states.get(relative)
        if state is None:
            stats.not_started += 1
            continue
        if state["source_blake3"] != source["blake3"] or state["source_pages"] != source["pages"]:
            stats.stale_sources += 1
            continue
        if state["status"] == "published":
            raw_path, docir_path = _output_paths(output_root, relative)
            if not raw_path.is_file() or not docir_path.is_file():
                stats.missing_outputs += 1
                continue
            stats.published_documents += 1
            stats.published_pages += source["pages"]
            stats.published.append((docir_path, source["pages"]))
        else:
            stats.statuses[state["status"]] += 1
            stats.staged_pages += max(0, min(state["completed_pages"], source["pages"]))
    return stats


def _image_occurrences(published: list[tuple[Path, int]]) -> tuple[int, dict[str, list[int]], int]:
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    total = unresolved = 0
    for docir_path, expected_pages in published:
        try:
            with docir_path.open(encoding="utf-8") as stream:
                pages = 0
                for line in stream:
                    page = json.loads(line)
                    pages += 1
                    for block in (node for parent in page["blocks"] for node in walk_content(parent)):
                        if block.get("kind") == "image" and block.get("asset_status") == "unresolved":
                            unresolved += 1
                        digest = block.get("image_blake3")
                        if not isinstance(digest, str) or not digest:
                            continue
                        total += 1
                        structured = block.get("source_label") in {"Diagram", "Chart"} and (
                            bool((block.get("diagram") or {}).get("code")) or bool(block.get("table"))
                        )
                        counts[digest][1 if structured else 0] += 1
                if pages != expected_pages:
                    raise ValueError(f"expected {expected_pages} pages, found {pages}")
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise click.ClickException(f"cannot count images in {docir_path}: {exc}") from exc
    return total, counts, unresolved


def collect_caption_stats(database: Path, published: list[tuple[Path, int]]) -> CaptionStats:
    if not database.is_file():
        raise click.ClickException(f"caption database does not exist: {database}")
    total, counts, unresolved = _image_occurrences(published)
    try:
        with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as connection:
            if not _has_table(connection, "images"):
                raise click.ClickException(f"caption database has no images table: {database}")
            if not _has_table(connection, "captions"):
                return CaptionStats(total, initialized=False, unresolved=unresolved)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(captions)")}
            if not {"image_blake3", "caption", "last_error"} <= columns:
                raise click.ClickException("captions table needs image_blake3, caption, and last_error columns")
            captions = {}
            digests = list(counts)
            for start in range(0, len(digests), 500):
                batch = digests[start : start + 500]
                placeholders = ",".join("?" for _ in batch)
                for digest, caption, error in connection.execute(
                    f"SELECT image_blake3, caption, last_error FROM captions WHERE image_blake3 IN ({placeholders})", batch
                ):
                    captions[digest] = (caption, error)
    except sqlite3.DatabaseError as exc:
        raise click.ClickException(f"cannot read caption database {database}: {exc}") from exc

    stats = CaptionStats(total, initialized=True, unresolved=unresolved)
    for digest, (eligible, structured) in counts.items():
        caption, error = captions.get(digest, (None, None))
        if isinstance(caption, str) and caption.strip():
            stats.captioned += eligible + structured
        else:
            stats.skipped += structured
            if error:
                stats.failed += eligible
            else:
                stats.pending += eligible
    return stats


def _ocr_table(stats: OCRStats, output_root: Path, scope: str) -> Table:
    table = Table(title="OCR progress", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Output root", str(output_root))
    table.add_row("Scope", scope)
    table.add_row("Target", f"{stats.target_documents:,} documents / {stats.target_pages:,} pages")
    table.add_row(
        "DocIR published documents",
        f"{stats.published_documents:,}/{stats.target_documents:,} ({_percent(stats.published_documents, stats.target_documents)})",
    )
    table.add_row(
        "DocIR published pages",
        f"{stats.published_pages:,}/{stats.target_pages:,} ({_percent(stats.published_pages, stats.target_pages)})",
    )
    table.add_row(
        "OCR completed pages",
        f"{stats.completed_pages:,}/{stats.target_pages:,} ({_percent(stats.completed_pages, stats.target_pages)})",
    )
    table.add_row("Completed in staging", f"{stats.staged_pages:,}")
    table.add_row("Active documents", f"{stats.statuses['active']:,}")
    table.add_row("Interrupted documents", f"{stats.statuses['interrupted']:,}")
    table.add_row("Documents needing retry", f"{stats.statuses['error']:,}")
    table.add_row("Not started", f"{stats.not_started:,}")
    if stats.stale_sources or stats.missing_outputs:
        table.add_row("Stale source / missing published output", f"{stats.stale_sources:,} / {stats.missing_outputs:,}")
    return table


def _caption_table(stats: CaptionStats, database: Path) -> Table:
    table = Table(title="Image captioning", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Database", str(database))
    table.add_row("Resolved images in published DocIR", f"{stats.images:,}")
    table.add_row("Unresolved inline images (not captionable)", f"{stats.unresolved:,}")
    if not stats.initialized:
        table.add_row("Captioning", "not started (no captions table)")
        return table
    table.add_row(
        "Captioned / structured skip / failed / pending",
        f"{stats.captioned:,} / {stats.skipped:,} / {stats.failed:,} / {stats.pending:,}",
    )
    table.add_row("Caption coverage", f"{stats.captioned:,}/{stats.images:,} ({_percent(stats.captioned, stats.images)})")
    table.add_row("Processing progress", f"{stats.processed:,}/{stats.images:,} ({_percent(stats.processed, stats.images)})")
    return table


def print_document_report(
    connection: sqlite3.Connection,
    database: Path,
    output_root: Path | None,
    file_list: Path | None,
    all_documents: bool,
    caption_database: Path | None,
) -> None:
    from cpushowspeed.documents.inventory import print_summary

    if file_list is not None and all_documents:
        raise click.ClickException("--file-list and --all cannot be combined")
    if caption_database is not None and not caption_database.is_file():
        raise click.ClickException(f"caption database does not exist: {caption_database}")
    root = connection.execute("SELECT value FROM metadata WHERE key = 'root'").fetchone()
    if not root:
        raise click.ClickException("inventory database has no source root")
    selected = select_inventory(connection, Path(root["value"]), file_list, "", None)
    if not _has_table(connection, "ocr_runs"):
        if output_root is not None or caption_database is not None:
            raise click.ClickException("inventory database has no OCR runs")
        print_summary(connection, database)
        Console().print("OCR: not started")
        return
    runs = connection.execute("SELECT run_id, output_root FROM ocr_runs ORDER BY created_at").fetchall()
    if output_root is not None:
        chosen_root = output_root.resolve()
        run = next((row for row in runs if row["output_root"] == str(chosen_root)), None)
        if run is None:
            raise click.ClickException(f"no OCR run for output root: {chosen_root}")
    elif len(runs) == 1:
        run = runs[0]
        chosen_root = Path(run["output_root"])
    elif not runs:
        if caption_database is not None:
            raise click.ClickException("inventory database has no OCR runs")
        print_summary(connection, database)
        Console().print("OCR: not started")
        return
    else:
        if file_list is not None or caption_database is not None:
            raise click.ClickException("multiple OCR runs; select one with --output-root")
        print_summary(connection, database)
        table = Table(title="OCR runs")
        table.add_column("Output root")
        for row in runs:
            table.add_row(row["output_root"])
        Console().print(table)
        return
    if not _has_table(connection, "ocr_documents"):
        raise click.ClickException("OCR run exists but ocr_documents table is missing")
    stats = collect_ocr_stats(connection, run["run_id"], chosen_root, selected)
    caption_stats = collect_caption_stats(caption_database, stats.published) if caption_database is not None else None
    print_summary(connection, database)
    console = Console()
    console.print(_ocr_table(stats, chosen_root, str(file_list) if file_list else "all eligible PDFs"))
    if caption_stats is not None:
        console.print(_caption_table(caption_stats, caption_database))
