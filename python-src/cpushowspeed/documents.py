"""Resumable, source-preserving inventory of local PDF collections."""

from __future__ import annotations

import json
import multiprocessing
import os
import sqlite3
import sys
import uuid
from collections import Counter, defaultdict
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from contextlib import closing
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import blake3
import click
import pypdfium2 as pdfium
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

DEFAULT_DATABASE = Path("data/derived/documents/inventory.sqlite")
SCHEMA_VERSION = "1"
HASH_CHUNK_SIZE = 4 * 1024 * 1024
PDFIUM_VERSION = version("pypdfium2")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _signature(stat: os.stat_result) -> tuple[int, int, int, int, int]:
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def _inventory_one(root: str, relative_path: str, expected: tuple[int, int, int, int, int]) -> dict:
    path = Path(root) / relative_path
    result = {
        "relative_path": relative_path,
        "size_bytes": expected[2],
        "mtime_ns": expected[3],
        "ctime_ns": expected[4],
        "blake3": None,
        "pages": None,
        "pdf_version": None,
        "status": "io_error",
        "error": None,
        "pdfium_version": PDFIUM_VERSION,
        "scanned_at": _now(),
    }
    try:
        with path.open("rb") as stream:
            if _signature(os.fstat(stream.fileno())) != expected:
                result["status"] = "changed"
                result["error"] = "file changed before reading"
                return result

            digest = blake3.blake3()
            while chunk := stream.read(HASH_CHUNK_SIZE):
                digest.update(chunk)
            result["blake3"] = digest.hexdigest()

            if _signature(os.fstat(stream.fileno())) != expected:
                result["status"] = "changed"
                result["error"] = "file changed while hashing"
                result["blake3"] = None
                return result

            stream.seek(0)
            try:
                with pdfium.PdfDocument(stream) as document:
                    result["pages"] = len(document)
                    result["pdf_version"] = document.get_version()
                result["status"] = "ok"
            except Exception as exc:
                result["status"] = "pdf_error"
                result["error"] = f"{type(exc).__name__}: {exc}"[:500]

        if _signature(path.stat()) != expected:
            result["status"] = "changed"
            result["error"] = "file changed during inventory"
            result["blake3"] = None
            result["pages"] = None
            result["pdf_version"] = None
    except Exception as exc:
        result["status"] = "io_error"
        result["error"] = f"{type(exc).__name__}: {exc}"[:500]
        result["blake3"] = None
        result["pages"] = None
        result["pdf_version"] = None
    return result


def _connect(database: Path, root: Path | None = None) -> sqlite3.Connection:
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS files (
            relative_path TEXT PRIMARY KEY,
            size_bytes INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            ctime_ns INTEGER NOT NULL,
            blake3 TEXT,
            pages INTEGER,
            pdf_version INTEGER,
            status TEXT NOT NULL,
            error TEXT,
            pdfium_version TEXT,
            scanned_at TEXT,
            seen_run TEXT NOT NULL
        )"""
    )
    stored_version = connection.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone()
    if stored_version and stored_version["value"] != SCHEMA_VERSION:
        connection.close()
        raise click.ClickException(f"unsupported inventory schema version: {stored_version['value']}")
    stored_root = connection.execute("SELECT value FROM metadata WHERE key = 'root'").fetchone()
    if root is not None and stored_root and stored_root["value"] != str(root):
        connection.close()
        raise click.ClickException(f"database belongs to {stored_root['value']}; requested root is {root}")
    if root is not None and not stored_root:
        connection.execute("INSERT INTO metadata (key, value) VALUES ('root', ?)", (str(root),))
    if not stored_version:
        connection.execute("INSERT INTO metadata (key, value) VALUES ('schema_version', ?)", (SCHEMA_VERSION,))
    connection.commit()
    return connection


def _discover(root: Path) -> list[tuple[str, tuple[int, int, int, int, int] | None, str | None]]:
    found = []

    def onerror(error: OSError) -> None:
        raise error

    with Progress(
        SpinnerColumn(),
        TextColumn("Discovering PDFs: {task.completed:,} found"),
        console=Console(file=sys.stderr),
        transient=False,
    ) as progress:
        task = progress.add_task("Discovering PDFs", total=None)
        for directory, _, names in os.walk(root, followlinks=False, onerror=onerror):
            for name in names:
                if not name.lower().endswith(".pdf"):
                    continue
                path = Path(directory) / name
                if path.is_symlink():
                    continue
                relative = path.relative_to(root).as_posix()
                try:
                    signature = _signature(path.stat())
                    found.append((relative, signature, None))
                except OSError as exc:
                    found.append((relative, None, f"{type(exc).__name__}: {exc}"[:500]))
                progress.advance(task)
    found.sort(key=lambda item: item[0])
    return found


def _store_result(connection: sqlite3.Connection, result: dict, run_id: str) -> None:
    connection.execute(
        """UPDATE files SET size_bytes = ?, mtime_ns = ?, ctime_ns = ?, blake3 = ?, pages = ?,
            pdf_version = ?, status = ?, error = ?, pdfium_version = ?, scanned_at = ?, seen_run = ?
           WHERE relative_path = ?""",
        (
            result["size_bytes"],
            result["mtime_ns"],
            result["ctime_ns"],
            result["blake3"],
            result["pages"],
            result["pdf_version"],
            result["status"],
            result["error"],
            result["pdfium_version"],
            result["scanned_at"],
            run_id,
            result["relative_path"],
        ),
    )


def _summary(connection: sqlite3.Connection, database: Path) -> None:
    console = Console()
    root = connection.execute("SELECT value FROM metadata WHERE key = 'root'").fetchone()
    rows = connection.execute("SELECT relative_path, size_bytes, pages, status FROM files").fetchall()
    counts = Counter(row["status"] for row in rows)
    valid_pages = sum(row["pages"] or 0 for row in rows if row["status"] == "ok")
    total_bytes = sum(row["size_bytes"] for row in rows if row["status"] != "missing")
    table = Table(title="PDF inventory", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Root", root["value"] if root else "unknown")
    table.add_row("Database", str(database))
    table.add_row("Current PDFs", f"{len(rows) - counts.get('missing', 0):,}")
    table.add_row("Current size", f"{total_bytes / (1024 ** 3):,.2f} GiB")
    table.add_row("Known pages", f"{valid_pages:,}")
    for status, count in sorted(counts.items()):
        table.add_row(status, f"{count:,}")
    console.print(table)

    by_branch = defaultdict(lambda: [0, 0])
    for row in rows:
        if row["status"] != "ok":
            continue
        branch = row["relative_path"].split("/", 1)[0] if "/" in row["relative_path"] else "(root)"
        by_branch[branch][0] += 1
        by_branch[branch][1] += row["pages"] or 0
    if by_branch:
        branch_table = Table(title="Largest directories by pages")
        branch_table.add_column("Directory")
        branch_table.add_column("PDFs", justify="right")
        branch_table.add_column("Pages", justify="right")
        for branch, (files, pages) in sorted(by_branch.items(), key=lambda item: item[1][1], reverse=True)[:15]:
            branch_table.add_row(branch, f"{files:,}", f"{pages:,}")
        console.print(branch_table)


@click.group()
def documents() -> None:
    """Inspect local PDF collections before OCR."""


@documents.command("inventory")
@click.option("--root", type=click.Path(path_type=Path, exists=True, file_okay=False), required=True, help="PDF collection root.")
@click.option("--database", type=click.Path(path_type=Path), default=DEFAULT_DATABASE, show_default=True)
@click.option("--workers", type=click.IntRange(min=1), default=4, show_default=True, help="Independent PDFium worker processes.")
@click.option("--rescan", is_flag=True, help="Rehash and reparse every PDF, including unchanged successful records.")
def inventory_command(root: Path, database: Path, workers: int, rescan: bool) -> None:
    """Hash every new or changed PDF with BLAKE3 and record its page count."""
    root = root.resolve(strict=True)
    database = database.resolve()
    with closing(_connect(database, root)) as connection:
        try:
            discovered = _discover(root)
        except OSError as exc:
            raise click.ClickException(f"cannot enumerate PDF collection: {exc}") from exc

        cached = {
            row["relative_path"]: row
            for row in connection.execute("SELECT relative_path, size_bytes, mtime_ns, ctime_ns, status FROM files")
        }
        if not discovered and cached:
            raise click.ClickException("no PDFs found; existing records were left unchanged (check the source mount)")
        run_id = uuid.uuid4().hex
        todo = []
        skipped = []
        stat_errors = []
        for relative, signature, error in discovered:
            if signature is None:
                stat_errors.append((relative, error))
                continue
            previous = cached.get(relative)
            if (
                not rescan
                and previous
                and previous["status"] == "ok"
                and (previous["size_bytes"], previous["mtime_ns"], previous["ctime_ns"]) == signature[2:]
            ):
                skipped.append(relative)
            else:
                todo.append((relative, signature))
        connection.executemany("UPDATE files SET seen_run = ? WHERE relative_path = ?", ((run_id, path) for path in skipped))
        connection.executemany(
            """INSERT INTO files (relative_path, size_bytes, mtime_ns, ctime_ns, status, seen_run)
               VALUES (?, ?, ?, ?, 'pending', ?)
               ON CONFLICT(relative_path) DO UPDATE SET
                 size_bytes = excluded.size_bytes, mtime_ns = excluded.mtime_ns, ctime_ns = excluded.ctime_ns,
                 blake3 = NULL, pages = NULL, pdf_version = NULL, status = 'pending', error = NULL,
                 pdfium_version = NULL, scanned_at = NULL, seen_run = excluded.seen_run""",
            ((path, sig[2], sig[3], sig[4], run_id) for path, sig in todo),
        )
        for relative, error in stat_errors:
            connection.execute(
                """INSERT INTO files (relative_path, size_bytes, mtime_ns, ctime_ns, status, error, scanned_at, seen_run)
                   VALUES (?, 0, 0, 0, 'io_error', ?, ?, ?)
                   ON CONFLICT(relative_path) DO UPDATE SET
                     size_bytes = 0, mtime_ns = 0, ctime_ns = 0,
                     blake3 = NULL, pages = NULL, pdf_version = NULL, status = 'io_error',
                     error = excluded.error, scanned_at = excluded.scanned_at, seen_run = excluded.seen_run""",
                (relative, error, _now(), run_id),
            )
        connection.commit()

        progress = Progress(
            TextColumn("{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=Console(file=sys.stderr),
            transient=False,
        )
        completed = 0
        with progress:
            task = progress.add_task("PDFs", total=len(todo))
            if todo:
                with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as executor:
                    iterator = iter(todo)
                    pending = {}
                    for _ in range(min(workers * 2, len(todo))):
                        path, signature = next(iterator)
                        pending[executor.submit(_inventory_one, str(root), path, signature)] = path
                    while pending:
                        done, _ = wait(pending, return_when=FIRST_COMPLETED)
                        for future in done:
                            path = pending.pop(future)
                            try:
                                result = future.result()
                            except Exception as exc:
                                raise click.ClickException(f"worker failed for {path}: {exc}") from exc
                            _store_result(connection, result, run_id)
                            completed += 1
                            progress.advance(task)
                            if completed % 32 == 0:
                                connection.commit()
                            try:
                                next_path, signature = next(iterator)
                            except StopIteration:
                                continue
                            pending[executor.submit(_inventory_one, str(root), next_path, signature)] = next_path
                connection.commit()

        connection.execute(
            """UPDATE files SET status = 'missing', error = 'not found in completed inventory run',
               blake3 = NULL, pages = NULL, pdf_version = NULL
               WHERE seen_run != ? AND status != 'missing'""",
            (run_id,),
        )
        connection.commit()
        _summary(connection, database)
        click.echo(f"Scanned {completed:,}; reused {len(skipped):,}; stat errors {len(stat_errors):,}.", err=True)


@documents.command("report")
@click.option(
    "--database", type=click.Path(path_type=Path, exists=True, dir_okay=False), default=DEFAULT_DATABASE, show_default=True
)
def report_command(database: Path) -> None:
    """Show the current inventory summary."""
    with closing(_connect(database)) as connection:
        _summary(connection, database)


@documents.command("export")
@click.option(
    "--database", type=click.Path(path_type=Path, exists=True, dir_okay=False), default=DEFAULT_DATABASE, show_default=True
)
@click.option("--output", type=click.Path(path_type=Path, dir_okay=False), required=True, help="JSONL path, or '-' for stdout.")
def export_command(database: Path, output: Path) -> None:
    """Export per-file records as JSONL."""
    with closing(_connect(database)) as connection:
        root = connection.execute("SELECT value FROM metadata WHERE key = 'root'").fetchone()
        source_root = root["value"] if root else None
        destination = sys.stdout if str(output) == "-" else None
        temporary = None
        if destination is None:
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_name(output.name + ".partial")
            destination = temporary.open("w", encoding="utf-8")
        try:
            for row in connection.execute(
                """SELECT relative_path, size_bytes, mtime_ns, ctime_ns, blake3, pages, pdf_version,
                          status, error, pdfium_version, scanned_at FROM files ORDER BY relative_path"""
            ):
                record = {"source_root": source_root, **dict(row)}
                destination.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        finally:
            if temporary is not None:
                destination.close()
        if temporary is not None:
            temporary.replace(output)
