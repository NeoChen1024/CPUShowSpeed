"""Resumable image-only captions for published DocIR documents."""

from __future__ import annotations

import asyncio
import base64
import fcntl
import json
import signal
import sqlite3
import sys
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import blake3
import click
import humanize
from cpushowspeed.docir_rich_table import walk_content
from cpushowspeed.document_report import collect_ocr_stats
from cpushowspeed.documents import DEFAULT_DATABASE, _connect
from cpushowspeed.ocr import _select_inventory
from openai import AsyncOpenAI
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

CONSOLE = Console(file=sys.stderr)
PROMPT = (
    "Describe only what is visible in this image for document search. Identify the visual type and important parts, "
    "labels, arrows, axes, units, and relationships where legible. Quote short readable labels exactly. "
    "If details are unclear, say so. Do not infer the source document, device identity, or purpose beyond visible evidence. "
    "Write one concise plain-text paragraph."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


@dataclass
class CaptionDocument:
    relative: str
    images: deque[str]
    started_at: str | None = None


def _eligible_images(path: Path, expected_pages: int) -> deque[str]:
    images: deque[str] = deque()
    seen: set[str] = set()
    page_number = 0
    with path.open(encoding="utf-8") as stream:
        for page_number, line in enumerate(stream, 1):
            page = json.loads(line)
            if page.get("page") != page_number or page.get("status") not in {"ok", "blank"}:
                raise ValueError(f"invalid page {page_number} in {path}")
            for block in (node for parent in page["blocks"] for node in walk_content(parent)):
                digest = block.get("image_blake3")
                if not digest or digest in seen:
                    continue
                structured = block.get("source_label") in {"Diagram", "Chart"} and (
                    bool((block.get("diagram") or {}).get("code")) or bool(block.get("table"))
                )
                if not structured:
                    images.append(digest)
                    seen.add(digest)
        if page_number != expected_pages:
            raise ValueError(f"expected {expected_pages} pages, found {page_number} in {path}")
    return images


def _init_catalog(connection: sqlite3.Connection) -> None:
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='images'").fetchone() is None:
        raise click.ClickException("ImagePool catalog has no images table")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS captions (
        image_blake3 TEXT PRIMARY KEY, caption TEXT, model TEXT, completed_at TEXT, last_error TEXT)"""
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS caption_documents (
        relative_path TEXT PRIMARY KEY, started_at TEXT NOT NULL)"""
    )
    connection.commit()


def _image_bytes(pool: Path, row: sqlite3.Row, digest: str) -> tuple[bytes, str]:
    relative = Path(row["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe ImagePool path for {digest}")
    data = (pool / relative).read_bytes()
    if blake3.blake3(data).hexdigest() != digest:
        raise ValueError(f"ImagePool BLAKE3 mismatch for {digest}")
    if row["media_type"] not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError(f"unsupported media type for {digest}: {row['media_type']}")
    return data, row["media_type"]


async def _request(client: AsyncOpenAI, model: str, pool: Path, row: sqlite3.Row, digest: str, retries: int) -> str:
    data, media_type = await asyncio.to_thread(_image_bytes, pool, row, digest)
    encoded = base64.b64encode(data).decode("ascii")
    message = {
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{encoded}"}},
            {"type": "text", "text": PROMPT},
        ],
    }
    for attempt in range(retries + 1):
        try:
            response = await client.chat.completions.create(model=model, messages=[message], temperature=0, max_tokens=512)
            choice = response.choices[0]
            caption = choice.message.content
            if choice.finish_reason != "stop" or not isinstance(caption, str) or not caption.strip():
                raise ValueError(f"incomplete caption (finish_reason={choice.finish_reason})")
            return caption.strip()
        except Exception as exc:
            if attempt == retries:
                raise RuntimeError(f"{type(exc).__name__}: {exc}") from exc
            await asyncio.sleep(min(2**attempt, 16))
    raise AssertionError("unreachable")


async def _run(
    database: Path,
    output_root: Path,
    file_list: Path | None,
    api_base: str,
    model: str,
    inflight_images: int,
    request_timeout: float,
    max_retries: int,
    shutdown_grace: float,
    force: bool,
) -> bool:
    inventory = _connect(database)
    pool = output_root / "ImagePool"
    catalog = sqlite3.connect(pool / "catalog.sqlite")
    catalog.row_factory = sqlite3.Row
    try:
        source_root = inventory.execute("SELECT value FROM metadata WHERE key='root'").fetchone()
        run = inventory.execute("SELECT run_id FROM ocr_runs WHERE output_root=?", (str(output_root),)).fetchone()
        if source_root is None or run is None:
            raise click.ClickException("inventory has no OCR run for this output root")
        selected = _select_inventory(inventory, Path(source_root["value"]), file_list, "", None)
        stats = collect_ocr_stats(inventory, run["run_id"], output_root, selected)
        _init_catalog(catalog)
        published = {path: pages for path, pages in stats.published}
        documents: list[CaptionDocument] = []
        for row in selected:
            relative = row["relative_path"]
            stem = (output_root / relative).with_suffix("")
            path = stem.with_name(stem.name + ".docir.jsonl")
            if path not in published:
                continue
            try:
                images = _eligible_images(path, row["pages"])
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise click.ClickException(f"cannot read published DocIR {path}: {exc}") from exc
            if images:
                started = catalog.execute("SELECT started_at FROM caption_documents WHERE relative_path=?", (relative,)).fetchone()
                documents.append(CaptionDocument(relative, images, started["started_at"] if started else None))
        order = {row["relative_path"]: index for index, row in enumerate(selected)}
        documents.sort(key=lambda doc: (doc.started_at is None, doc.started_at or "", order[doc.relative]))
        all_hashes = {digest for doc in documents for digest in doc.images}
        rows = {}
        hashes = sorted(all_hashes)
        for start in range(0, len(hashes), 500):
            batch = hashes[start : start + 500]
            placeholders = ",".join("?" for _ in batch)
            rows.update(
                {row["blake3"]: row for row in catalog.execute(f"SELECT * FROM images WHERE blake3 IN ({placeholders})", batch)}
            )
        missing = all_hashes - rows.keys()
        if missing:
            raise click.ClickException(f"{len(missing)} DocIR images are absent from ImagePool catalog; first: {min(missing)}")
        successes = {
            digest
            for digest, caption in catalog.execute("SELECT image_blake3, caption FROM captions")
            if caption and caption.strip()
        }
        pending = all_hashes if force else all_hashes - successes
        for doc in documents:
            doc.images = deque(digest for digest in doc.images if digest in pending)
        documents = [doc for doc in documents if doc.images]
        if not pending:
            CONSOLE.print(f"[green]All {len(all_hashes):,} eligible unique images already have captions.[/green]")
            return False
        CONSOLE.print(
            f"Captioning {len(pending):,} unique images from {len(documents):,} published documents "
            f"({len(selected) - stats.published_documents:,} selected PDFs without published DocIR)."
        )
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:
                pass
        dispatched: set[str] = set()
        completed: set[str] = set()
        active: dict[asyncio.Task, str] = {}
        failures = 0
        stop_deadline: float | None = None
        async with AsyncOpenAI(base_url=api_base, api_key="not-needed", max_retries=0, timeout=request_timeout) as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("Unique images attempted"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=CONSOLE,
            ) as progress:
                task_id = progress.add_task("Captions", total=len(pending))
                while active or (not stop.is_set() and len(dispatched) < len(pending)):
                    while not stop.is_set() and len(active) < inflight_images:
                        doc = next((doc for doc in documents if doc.images), None)
                        if doc is None:
                            break
                        digest = doc.images.popleft()
                        if digest in dispatched:
                            continue
                        if doc.started_at is None:
                            doc.started_at = _now()
                            catalog.execute(
                                "INSERT OR IGNORE INTO caption_documents(relative_path, started_at) VALUES (?, ?)",
                                (doc.relative, doc.started_at),
                            )
                            catalog.commit()
                            count = len(doc.images) + 1
                            size = sum((pool / rows[item]["path"]).stat().st_size for item in (digest, *doc.images))
                            CONSOLE.print(
                                f"Dispatch {doc.relative}: {count:,} pending images, {humanize.naturalsize(size, binary=True)}"
                            )
                        dispatched.add(digest)
                        active[asyncio.create_task(_request(client, model, pool, rows[digest], digest, max_retries))] = digest
                    if not active:
                        break
                    done, _ = await asyncio.wait(active, timeout=0.5, return_when=asyncio.FIRST_COMPLETED)
                    if stop.is_set():
                        if stop_deadline is None:
                            stop_deadline = time.monotonic() + shutdown_grace
                        if time.monotonic() >= stop_deadline:
                            for request in active:
                                if request not in done:
                                    request.cancel()
                    for finished in done:
                        digest = active.pop(finished)
                        if finished.cancelled():
                            continue
                        try:
                            caption = finished.result()
                            catalog.execute(
                                "INSERT INTO captions VALUES (?, ?, ?, ?, NULL) ON CONFLICT(image_blake3) DO UPDATE SET "
                                "caption=excluded.caption, model=excluded.model, completed_at=excluded.completed_at, last_error=NULL",
                                (digest, caption, model, _now()),
                            )
                        except Exception as exc:
                            failures += 1
                            error = str(exc)[:1000]
                            catalog.execute(
                                "INSERT INTO captions VALUES (?, NULL, NULL, NULL, ?) ON CONFLICT(image_blake3) DO UPDATE SET "
                                "last_error=excluded.last_error",
                                (digest, error),
                            )
                            CONSOLE.print(f"[red]Caption failed {digest[:12]}: {error}[/red]")
                        catalog.commit()
                        completed.add(digest)
                        progress.advance(task_id)
        CONSOLE.print(
            f"Saved {len(completed) - failures:,} captions; {failures:,} failed; {len(pending) - len(completed):,} pending."
        )
        return stop.is_set()
    finally:
        inventory.close()
        catalog.close()


@click.command("caption")
@click.option(
    "--database", type=click.Path(path_type=Path, exists=True, dir_okay=False), default=DEFAULT_DATABASE, show_default=True
)
@click.option("--output-root", type=click.Path(path_type=Path, exists=True, file_okay=False), required=True)
@click.option("--file-list", type=click.Path(path_type=Path, exists=True, dir_okay=False))
@click.option("--all", "all_documents", is_flag=True, help="Select all inventoried PDFs with published DocIR.")
@click.option("--api-base", default="http://sparksrv.lan:5000/v1", show_default=True)
@click.option("--model", default="gemma-4-26B-A4B-it", show_default=True)
@click.option("--inflight-images", type=click.IntRange(1), default=4, show_default=True)
@click.option("--request-timeout", type=click.FloatRange(min=1), default=180.0, show_default=True)
@click.option("--max-retries", type=click.IntRange(0), default=2, show_default=True)
@click.option("--shutdown-grace", type=click.FloatRange(min=0), default=10.0, show_default=True)
@click.option("--force", is_flag=True, help="Regenerate captions that already succeeded.")
def caption_command(
    database: Path,
    output_root: Path,
    file_list: Path | None,
    all_documents: bool,
    api_base: str,
    model: str,
    inflight_images: int,
    request_timeout: float,
    max_retries: int,
    shutdown_grace: float,
    force: bool,
) -> None:
    """Caption published DocIR images with a vision LLM."""
    if (file_list is None) == (not all_documents):
        raise click.ClickException("select either --file-list or --all")
    output = output_root.resolve(strict=True)
    pool = output / "ImagePool"
    if not (pool / "catalog.sqlite").is_file():
        raise click.ClickException(f"ImagePool catalog does not exist: {pool / "catalog.sqlite"}")
    lock_path = pool / ".caption.lock"
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise click.ClickException(f"another caption process is using {output}") from exc
        interrupted = asyncio.run(
            _run(
                database.resolve(strict=True),
                output,
                file_list,
                api_base.rstrip("/"),
                model,
                inflight_images,
                request_timeout,
                max_retries,
                shutdown_grace,
                force,
            )
        )
        if interrupted:
            raise SystemExit(130)
