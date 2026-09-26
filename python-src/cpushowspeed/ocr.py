"""Bounded, resumable Chandra OCR of an inventoried PDF tree."""

from __future__ import annotations

import asyncio
import base64
import fcntl
import io
import json
import multiprocessing
import os
import re
import signal
import sqlite3
import sys
import uuid
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
from importlib.metadata import version
from pathlib import Path

import blake3
import click
import humanize
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from bs4 import BeautifulSoup
from chandra.model.util import detect_repeat_token, scale_to_fit
from chandra.output import parse_chunks, parse_markdown
from chandra.prompts import PROMPT_MAPPING
from chandra.settings import settings
from cpushowspeed.docir_rich_table import convert_rich_table
from cpushowspeed.docir_table import TableConversionError
from cpushowspeed.documents import DEFAULT_DATABASE, _connect
from openai import AsyncOpenAI
from PIL import Image
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
from rich.text import Text

VISUAL_LABELS = {"Image", "Figure", "Diagram", "Chart"}
RENDER_RESERVATION = 16 * 1024 * 1024
PROMPT = PROMPT_MAPPING["ocr_layout"]
CONSOLE = Console(file=sys.stderr)


class PageETAColumn(TimeRemainingColumn):
    def render(self, task):
        if task.total is not None and task.completed >= task.total:
            return Text("0:00:00")
        return super().render(task)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _render_worker_init() -> None:
    # Terminal Ctrl+C is handled by the coordinator; workers finish their current page.
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _render_page(path: str, page_number: int) -> tuple[bytes, str, int, int]:
    """One page per PDFium process task; never retain a whole PDF's raster pages."""
    with pdfium.PdfDocument(path) as pdf:
        pdf.init_forms()
        page = pdf[page_number - 1]
        try:
            minimum = min(page.get_width(), page.get_height())
            dpi = max(settings.IMAGE_DPI, settings.MIN_PDF_IMAGE_DIM / minimum * 72)
            pdfium_c.FPDFPage_Flatten(page, pdfium_c.FLAT_NORMALDISPLAY)
            image = page.render(scale=dpi / 72).to_pil().convert("RGB")
        finally:
            page.close()
    width, height = image.size
    full = io.BytesIO()
    image.save(full, format="PNG")
    scaled = scale_to_fit(image)
    request = io.BytesIO()
    scaled.save(request, format="PNG")
    return full.getvalue(), base64.b64encode(request.getvalue()).decode("ascii"), width, height


def _bbox(soup_div, width: int, height: int) -> list[int] | None:
    value = soup_div.get("data-bbox")
    try:
        box = [int(part) for part in value.split()]
        if len(box) != 4 or not (0 <= box[0] < box[2] <= settings.BBOX_SCALE):
            return None
        if not (0 <= box[1] < box[3] <= settings.BBOX_SCALE):
            return None
        result = [
            max(0, int(box[0] * width / settings.BBOX_SCALE)),
            max(0, int(box[1] * height / settings.BBOX_SCALE)),
            min(width, int(box[2] * width / settings.BBOX_SCALE)),
            min(height, int(box[3] * height / settings.BBOX_SCALE)),
        ]
        return result if result[0] < result[2] and result[1] < result[3] else None
    except (AttributeError, TypeError, ValueError):
        return None


def _store_image(pool: Path, image: Image.Image, bbox: list[int]) -> dict:
    crop = image.crop(tuple(bbox))
    output = io.BytesIO()
    crop.save(output, format="PNG")
    data = output.getvalue()
    digest = blake3.blake3(data).hexdigest()
    relative = Path("images") / digest[:2] / digest[2:4] / f"{digest}.png"
    target = pool / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        temporary = target.with_name(f".{digest}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_bytes(data)
            try:
                os.link(temporary, target)
            except FileExistsError:
                pass
        finally:
            temporary.unlink(missing_ok=True)
    if blake3.blake3(target.read_bytes()).hexdigest() != digest:
        raise ValueError(f"Image Pool hash mismatch: {target}")
    return {"blake3": digest, "path": relative.as_posix(), "width": crop.width, "height": crop.height}


def _convert_page(raw: str, full_png: bytes, page: int, pool: Path) -> tuple[dict, list[dict], list[dict]]:
    with Image.open(io.BytesIO(full_png)) as source:
        image = source.convert("RGB")
    width, height = image.size
    soup = BeautifulSoup(raw, "html.parser")
    divs = soup.find_all("div", recursive=False)
    if not divs:
        raise ValueError("model response has no top-level layout blocks")
    chunks = parse_chunks(raw, image, bbox_scale=settings.BBOX_SCALE)
    content_divs = [div for div in divs if div.get("data-label") != "Blank-Page"]
    if len(chunks) != len(content_divs):
        raise ValueError("Chandra chunk count does not match layout blocks")
    blocks = []
    assets = []
    for chunk, div in zip(chunks, content_divs):
        label = chunk["label"]
        bbox = _bbox(div, width, height)
        block = {"kind": "text", "source_label": label, "bbox_px": bbox}
        content = chunk["content"]
        if label == "Table":
            block["kind"] = "table"
            try:
                block.update(convert_rich_table(content))
            except TableConversionError as exc:
                block.update(table=None, conversion_status="failed", error=str(exc))
        else:
            plain = BeautifulSoup(content, "html.parser").get_text("\n").strip()
            match = re.search(r"(?:^|\n)\s*(?:graph|flowchart)\s+(?:TB|TD|BT|LR|RL)\b", plain, re.I)
            if match:
                block.update(kind="diagram", diagram={"format": "mermaid", "code": plain[match.start() :].strip()})
            elif label in VISUAL_LABELS:
                block.update(kind="visual", caption=None)
            else:
                wrapper = f'<div data-label="{escape(label, quote=True)}">{content}</div>'
                block["markdown"] = parse_markdown(wrapper, include_headers_footers=True)
            if label in VISUAL_LABELS:
                if bbox is None:
                    block["crop_error"] = "missing or invalid bounding box"
                else:
                    asset = _store_image(pool, image, bbox)
                    block["image_blake3"] = asset["blake3"]
                    assets.append(asset)
        blocks.append(block)
    status = "blank" if not blocks and all(div.get("data-label") == "Blank-Page" for div in divs) else "ok"
    return {"page": page, "page_size_px": [width, height], "status": status, "blocks": blocks}, chunks, assets


def _stage_path(output_root: Path, relative_path: str, page: int | None = None) -> Path:
    digest = blake3.blake3(relative_path.encode()).hexdigest()
    directory = output_root / ".ocr-staging" / digest[:2] / digest
    return directory / ("identity.json" if page is None else f"{page:06d}.json")


def _read_stage(output_root: Path, relative: str, run_id: str, source_hash: str, pages: int) -> set[int]:
    identity = _stage_path(output_root, relative)
    if not identity.exists():
        return set()
    expected = {"run_id": run_id, "relative_path": relative, "source_blake3": source_hash, "pages": pages}
    if json.loads(identity.read_text()) != expected:
        raise ValueError(f"staging identity differs from current source/run: {relative}")
    completed = set()
    for path in identity.parent.glob("[0-9]*.json"):
        record = json.loads(path.read_text())
        page = record["raw"]["page"]
        if page < 1 or page > pages or path.name != f"{page:06d}.json":
            raise ValueError(f"invalid staged page: {path}")
        if record["docir"]["status"] in {"ok", "blank"}:
            completed.add(page)
    return completed


def _record_page(output_root: Path, relative: str, raw_record: dict, docir: dict) -> None:
    target = _stage_path(output_root, relative, raw_record["page"])
    _write_atomic(target, (_json({"raw": raw_record, "docir": docir}) + "\n").encode())


def _write_jsonl_atomic(path: Path, records) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            for record in records:
                stream.write(_json(record) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _finalize(output_root: Path, relative: str, header: dict, pages: int) -> None:
    stem = Path(relative).with_suffix("")
    raw_target = output_root / stem.parent / f"{stem.name}.raw.jsonl"
    docir_target = output_root / stem.parent / f"{stem.name}.docir.jsonl"

    def staged_records():
        for page in range(1, pages + 1):
            record = json.loads(_stage_path(output_root, relative, page).read_text())
            if record["raw"]["page"] != page or record["docir"]["page"] != page or record["docir"]["status"] not in {"ok", "blank"}:
                raise ValueError(f"page {page} is not completed")
            yield record

    def raw_records():
        yield header
        for row in staged_records():
            yield row["raw"]

    _write_jsonl_atomic(raw_target, raw_records())
    _write_jsonl_atomic(docir_target, (row["docir"] for row in staged_records()))
    for page in range(1, pages + 1):
        _stage_path(output_root, relative, page).unlink()
    identity = _stage_path(output_root, relative)
    identity.unlink()
    identity.parent.rmdir()


def _verify_final(raw_path: Path, docir_path: Path, relative: str, source_hash: str, pages: int, run_id: str) -> None:
    with raw_path.open(encoding="utf-8") as raw_stream, docir_path.open(encoding="utf-8") as docir_stream:
        header = json.loads(raw_stream.readline())
        if (
            header.get("run_id") != run_id
            or header.get("source_pdf") != relative
            or header.get("source_blake3") != source_hash
            or header.get("pages") != pages
        ):
            raise ValueError(f"published output identity mismatch: {relative}")
        for page in range(1, pages + 1):
            raw = json.loads(raw_stream.readline())
            docir = json.loads(docir_stream.readline())
            if raw.get("page") != page or docir.get("page") != page or docir.get("status") not in {"ok", "blank"}:
                raise ValueError(f"published page {page} is incomplete: {relative}")
        if raw_stream.readline() or docir_stream.readline():
            raise ValueError(f"published output has extra pages: {relative}")


@dataclass
class Document:
    relative: str
    pages: int
    size: int
    source_hash: str
    started_at: str | None = None
    completed: set[int] = field(default_factory=set)
    next_page: int = 1
    ready: deque = field(default_factory=deque)
    busy: int = 0
    errors: int = 0


@dataclass
class PagePayload:
    document: Document
    page: int
    full_png: bytes
    request_b64: str
    width: int
    height: int
    attempts: int = 0
    reasons: list[str] = field(default_factory=list)
    ready_at: float = 0.0
    last_raw: str = ""
    last_tokens: int = 0
    last_finish_reason: str | None = None

    @property
    def memory(self) -> int:
        return len(self.full_png) + len(self.request_b64) + self.width * self.height * 3


def _init_state(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS ocr_runs (
        run_id TEXT PRIMARY KEY, output_root TEXT NOT NULL UNIQUE,
        config_json TEXT NOT NULL, created_at TEXT NOT NULL)"""
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS ocr_documents (
        run_id TEXT NOT NULL, relative_path TEXT NOT NULL, source_blake3 TEXT NOT NULL,
        source_pages INTEGER NOT NULL, started_at TEXT, status TEXT NOT NULL,
        completed_pages INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL, last_error TEXT,
        PRIMARY KEY (run_id, relative_path))"""
    )
    connection.execute("CREATE INDEX IF NOT EXISTS ocr_documents_priority ON ocr_documents(run_id, status, started_at)")
    connection.commit()


def _init_image_catalog(pool: Path) -> sqlite3.Connection:
    pool.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(pool / "catalog.sqlite")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS images (
        blake3 TEXT PRIMARY KEY, path TEXT NOT NULL, media_type TEXT NOT NULL,
        width INTEGER NOT NULL, height INTEGER NOT NULL)"""
    )
    connection.commit()
    return connection


async def _request(
    client: AsyncOpenAI, model: str, payload: PagePayload, timeout: float
) -> tuple[str, int, str | None, str | None]:
    temperature = 0.0 if payload.attempts == 0 else min(0.2 * payload.attempts, 0.8)
    top_p = 0.1 if payload.attempts == 0 else 0.95
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{payload.request_b64}"}},
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ],
            max_tokens=settings.MAX_OUTPUT_TOKENS,
            temperature=temperature,
            top_p=top_p,
            timeout=timeout,
        )
        choice = response.choices[0]
        return choice.message.content or "", response.usage.completion_tokens if response.usage else 0, choice.finish_reason, None
    except Exception as exc:
        return "", 0, None, f"{type(exc).__name__}: {exc}"[:500]


def _has_bad_repeat(raw: str) -> bool:
    if detect_repeat_token(raw):
        return True
    if len(raw) <= 50 or not detect_repeat_token(raw, cut_from_end=50):
        return False
    # Chandra's second check can end inside a legitimate binary table cell
    # after trimming closing HTML. Do not treat a short complete bit row as
    # model degeneration; long repeated bit runs remain retryable.
    trimmed = raw[:-50]
    cell = re.search(r"<td(?:\s[^>]*)?>([01\s]+)$", trimmed)
    if cell and raw.rstrip().endswith("</div>") and len(re.findall(r"[01]", cell.group(1))) <= 256:
        return False
    return True


def _failure_record(page: int, reason: str, payload: PagePayload | None = None) -> tuple[dict, dict]:
    size = [payload.width, payload.height] if payload else None
    raw_record = {
        "page": page,
        "status": "error",
        "raw": payload.last_raw if payload else "",
        "chunks": [],
        "page_size_px": size,
        "token_count": payload.last_tokens if payload else 0,
        "finish_reason": payload.last_finish_reason if payload else None,
        "attempts": payload.attempts + 1 if payload else 0,
        "retry_reasons": payload.reasons if payload else [],
        "error": reason,
    }
    return raw_record, {"page": page, "page_size_px": size, "status": "error", "blocks": [], "error": reason}


def _prepare_page(
    payload: PagePayload, raw: str, tokens: int, finish_reason: str | None, pool: Path
) -> tuple[dict, dict, list[dict]]:
    docir, chunks, assets = _convert_page(raw, payload.full_png, payload.page, pool)
    record = {
        "page": payload.page,
        "status": docir["status"],
        "raw": raw,
        "chunks": chunks,
        "page_size_px": [payload.width, payload.height],
        "token_count": tokens,
        "finish_reason": finish_reason,
        "attempts": payload.attempts + 1,
        "retry_reasons": payload.reasons,
        "temperature": 0.0 if payload.attempts == 0 else min(0.2 * payload.attempts, 0.8),
        "top_p": 0.1 if payload.attempts == 0 else 0.95,
    }
    return record, docir, assets


def _read_file_list(file_list: Path, input_root: Path) -> list[str]:
    paths = []
    seen = set()
    duplicates = 0
    try:
        lines = file_list.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        raise click.ClickException(f"cannot read file list {file_list}: {exc}") from exc
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        source = Path(line).expanduser()
        if source.is_absolute():
            try:
                relative = source.resolve().relative_to(input_root)
            except ValueError as exc:
                raise click.ClickException(f"{file_list}:{line_number}: path is outside PDF root: {line}") from exc
        else:
            if ".." in source.parts:
                raise click.ClickException(f"{file_list}:{line_number}: parent traversal is not allowed: {line}")
            relative = source
        if relative.suffix.lower() != ".pdf":
            raise click.ClickException(f"{file_list}:{line_number}: expected a PDF path: {line}")
        key = relative.as_posix()
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        paths.append(key)
    if not paths:
        raise click.ClickException(f"file list has no PDF paths: {file_list}")
    if duplicates:
        CONSOLE.print(f"[yellow]Ignored {duplicates:,} duplicate file-list entries.[/yellow]")
    return paths


def _select_inventory(
    connection: sqlite3.Connection, input_root: Path, file_list: Path | None, prefix: str, limit_documents: int | None
) -> list[sqlite3.Row]:
    columns = "relative_path, pages, size_bytes, blake3, mtime_ns, ctime_ns, status"
    if file_list is not None:
        selected_paths = _read_file_list(file_list, input_root)
        available = {row["relative_path"]: row for row in connection.execute(f"SELECT {columns} FROM files")}
        selected = []
        for relative in selected_paths:
            row = available.get(relative)
            if row is None:
                raise click.ClickException(f"file list names a PDF absent from inventory: {relative}")
            if row["status"] != "ok":
                raise click.ClickException(f"file list names a PDF with inventory status {row['status']}: {relative}")
            selected.append(row)
        return selected
    sql = f"SELECT {columns} FROM files WHERE status = 'ok'"
    args: tuple = ()
    if prefix:
        sql += " AND relative_path LIKE ? ESCAPE '\\'"
        args = (prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",)
    sql += " ORDER BY relative_path"
    selected = connection.execute(sql, args).fetchall()
    return selected[:limit_documents] if limit_documents is not None else selected


async def _run_ocr(
    database: Path,
    input_root: Path,
    output_root: Path,
    api_base: str,
    model: str,
    jobs: int,
    inflight_pages: int,
    buffer_mib: int,
    file_list: Path | None,
    prefix: str,
    limit_documents: int | None,
    request_timeout: float,
    max_retries: int,
    shutdown_grace: float,
) -> bool:
    connection = _connect(database, input_root)
    image_catalog = _init_image_catalog(output_root / "ImagePool")
    try:
        _init_state(connection)
        inventory = _select_inventory(connection, input_root, file_list, prefix, limit_documents)
        if not inventory:
            raise click.ClickException("no inventoried PDFs match the selection")
        destinations = {}
        for row in inventory:
            key = Path(row["relative_path"]).with_suffix("").as_posix().casefold()
            previous = destinations.setdefault(key, row["relative_path"])
            if previous != row["relative_path"]:
                raise click.ClickException(f"output-name collision: {previous} and {row['relative_path']}")
        config = {
            "input_root": str(input_root),
            "output_root": str(output_root),
            "api_base": api_base,
            "model": model,
            "prompt_blake3": blake3.blake3(PROMPT.encode()).hexdigest(),
            "chandra_version": version("chandra-ocr"),
            "pdfium_version": version("pypdfium2"),
            "image_dpi": settings.IMAGE_DPI,
            "min_pdf_image_dim": settings.MIN_PDF_IMAGE_DIM,
            "bbox_scale": settings.BBOX_SCALE,
            "max_output_tokens": settings.MAX_OUTPUT_TOKENS,
        }
        existing_run = connection.execute("SELECT * FROM ocr_runs WHERE output_root = ?", (str(output_root),)).fetchone()
        if existing_run:
            if json.loads(existing_run["config_json"]) != config:
                raise click.ClickException("output root belongs to a run with different OCR settings; choose a new output root")
            run_id = existing_run["run_id"]
        else:
            run_id = uuid.uuid4().hex
            connection.execute("INSERT INTO ocr_runs VALUES (?, ?, ?, ?)", (run_id, str(output_root), _json(config), _now()))
            connection.commit()
        inventory_by_path = {row["relative_path"]: row for row in inventory}
        records = {
            row["relative_path"]: row for row in connection.execute("SELECT * FROM ocr_documents WHERE run_id = ?", (run_id,))
        }
        documents = []
        completed_total = 0
        for row in inventory:
            relative = row["relative_path"]
            state = records.get(relative)
            if state and (state["source_blake3"] != row["blake3"] or state["source_pages"] != row["pages"]):
                raise click.ClickException(f"source changed since OCR began: {relative}; use a new output root")
            doc = Document(relative, row["pages"], row["size_bytes"], row["blake3"], state["started_at"] if state else None)
            final = output_root / Path(relative).with_suffix("")
            raw_final = final.with_name(final.name + ".raw.jsonl")
            final = final.with_name(final.name + ".docir.jsonl")
            if final.exists():
                if not state:
                    raise click.ClickException(f"output exists without run state: {final}")
                if not raw_final.exists():
                    raise click.ClickException(f"published raw output is missing: {raw_final}")
                if state["status"] != "published":
                    try:
                        _verify_final(raw_final, final, relative, doc.source_hash, doc.pages, run_id)
                    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                        raise click.ClickException(f"cannot recover published output {relative}: {exc}") from exc
                completed_total += doc.pages
                if state["status"] != "published":
                    connection.execute(
                        "UPDATE ocr_documents SET status = 'published', completed_pages = ?, updated_at = ? WHERE run_id = ? AND relative_path = ?",
                        (doc.pages, _now(), run_id, relative),
                    )
                continue
            if state and state["status"] == "published":
                raise click.ClickException(f"published output is missing: {final}")
            if doc.started_at:
                doc.completed = _read_stage(output_root, relative, run_id, doc.source_hash, doc.pages)
                completed_total += len(doc.completed)
            documents.append(doc)
        connection.commit()
        # Stable sorting preserves file-list order among documents that have not started.
        documents.sort(key=lambda doc: (doc.started_at is None, doc.started_at or ""))
        total_pages = sum(row["pages"] for row in inventory)
        buffer_bytes = buffer_mib * 1024 * 1024
        active: list[Document] = []
        next_doc = 0
        render_tasks: dict[asyncio.Future, tuple[Document, int]] = {}
        request_tasks: dict[asyncio.Task, PagePayload] = {}
        process_tasks: dict[asyncio.Task, tuple[PagePayload, bool]] = {}
        queued_memory = 0
        max_active = max(2, min(32, jobs + inflight_pages))
        loop = asyncio.get_running_loop()
        stop_requested = False
        stop_deadline = 0.0

        def request_stop() -> None:
            nonlocal stop_requested, stop_deadline
            if not stop_requested:
                stop_requested = True
                stop_deadline = loop.time() + shutdown_grace
                CONSOLE.print("[yellow]Interrupt requested:[/yellow] stopping new work and saving completed pages.")
            else:
                stop_deadline = loop.time()
                CONSOLE.print("[yellow]Second interrupt:[/yellow] cancelling outstanding OCR requests now.")

        loop.add_signal_handler(signal.SIGINT, request_stop)
        loop.add_signal_handler(signal.SIGTERM, request_stop)
        async with AsyncOpenAI(api_key=settings.VLLM_API_KEY, base_url=api_base, max_retries=0) as client:
            with (
                ProcessPoolExecutor(
                    max_workers=jobs, mp_context=multiprocessing.get_context("spawn"), initializer=_render_worker_init
                ) as render_pool,
                Progress(
                    SpinnerColumn(),
                    TextColumn("Completed pages"),
                    BarColumn(),
                    MofNCompleteColumn(),
                    TimeElapsedColumn(),
                    TextColumn("ETA"),
                    PageETAColumn(),
                    console=CONSOLE,
                    transient=False,
                ) as progress,
            ):
                progress_task = progress.add_task("OCR", total=total_pages, completed=completed_total)
                while (
                    (not stop_requested and (active or next_doc < len(documents))) or render_tasks or request_tasks or process_tasks
                ):
                    if stop_requested and request_tasks and loop.time() >= stop_deadline:
                        for request in request_tasks:
                            request.cancel()
                    while (
                        not stop_requested
                        and next_doc < len(documents)
                        and len(active) < max_active
                        and len(render_tasks) < jobs
                        and queued_memory + len(render_tasks) * RENDER_RESERVATION < buffer_bytes
                        and not any(doc.next_page <= doc.pages for doc in active)
                    ):
                        doc = documents[next_doc]
                        next_doc += 1
                        path = input_root / doc.relative
                        stat = path.stat()
                        inv = inventory_by_path[doc.relative]
                        if (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) != (
                            inv["size_bytes"],
                            inv["mtime_ns"],
                            inv["ctime_ns"],
                        ):
                            raise click.ClickException(f"PDF changed after inventory: {doc.relative}")
                        if doc.started_at is None:
                            doc.started_at = _now()
                        identity = _stage_path(output_root, doc.relative)
                        if not identity.exists():
                            _write_atomic(
                                identity,
                                (
                                    _json(
                                        {
                                            "run_id": run_id,
                                            "relative_path": doc.relative,
                                            "source_blake3": doc.source_hash,
                                            "pages": doc.pages,
                                        }
                                    )
                                    + "\n"
                                ).encode(),
                            )
                        connection.execute(
                            """INSERT INTO ocr_documents
                            (run_id, relative_path, source_blake3, source_pages, started_at, status, completed_pages, updated_at)
                            VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                            ON CONFLICT(run_id, relative_path) DO UPDATE SET status = 'active', updated_at = excluded.updated_at""",
                            (run_id, doc.relative, doc.source_hash, doc.pages, doc.started_at, len(doc.completed), _now()),
                        )
                        connection.commit()
                        CONSOLE.print(
                            f"[cyan]Dispatch[/cyan] {doc.relative}  [bold]{doc.pages:,} {'page' if doc.pages == 1 else 'pages'}[/bold]  "
                            f"{humanize.naturalsize(doc.size, binary=True)}"
                        )
                        active.append(doc)
                    active.sort(key=lambda doc: (doc.started_at, doc.relative))
                    while (
                        not stop_requested
                        and len(render_tasks) < jobs
                        and queued_memory + len(render_tasks) * RENDER_RESERVATION < buffer_bytes
                    ):
                        candidate = next((doc for doc in active if doc.next_page <= doc.pages), None)
                        if candidate is None:
                            break
                        while candidate.next_page in candidate.completed:
                            candidate.next_page += 1
                        if candidate.next_page > candidate.pages:
                            continue
                        page = candidate.next_page
                        candidate.next_page += 1
                        candidate.busy += 1
                        future = loop.run_in_executor(render_pool, _render_page, str(input_root / candidate.relative), page)
                        render_tasks[future] = (candidate, page)
                    while not stop_requested and len(request_tasks) < inflight_pages:
                        ready = next((doc for doc in active if any(item.ready_at <= loop.time() for item in doc.ready)), None)
                        if ready is None:
                            break
                        payload = next(item for item in ready.ready if item.ready_at <= loop.time())
                        ready.ready.remove(payload)
                        request_tasks[asyncio.create_task(_request(client, model, payload, request_timeout))] = payload
                    waiting = list(render_tasks) + list(request_tasks) + list(process_tasks)
                    if waiting:
                        done, _ = await asyncio.wait(waiting, timeout=0.5, return_when=asyncio.FIRST_COMPLETED)
                    else:
                        done = set()
                        await asyncio.sleep(0.2)
                    for future in done:
                        if future in render_tasks:
                            doc, page = render_tasks.pop(future)
                            if stop_requested:
                                try:
                                    future.result()
                                except Exception:
                                    pass
                                doc.busy -= 1
                                continue
                            try:
                                full, request_b64, width, height = future.result()
                                payload = PagePayload(doc, page, full, request_b64, width, height)
                                queued_memory += payload.memory
                                doc.ready.append(payload)
                            except Exception as exc:
                                reason = f"{type(exc).__name__}: {exc}"[:500]
                                failed_raw, failed_docir = _failure_record(page, reason)
                                await asyncio.to_thread(_record_page, output_root, doc.relative, failed_raw, failed_docir)
                                doc.errors += 1
                                doc.busy -= 1
                                CONSOLE.print(f"[red]Render failed[/red] {doc.relative} page {page}: {reason}")
                            continue
                        if future in request_tasks:
                            payload = request_tasks.pop(future)
                            if future.cancelled():
                                payload.document.busy -= 1
                                queued_memory -= payload.memory
                                continue
                            raw, tokens, finish_reason, error = future.result()
                            payload.last_raw = raw
                            payload.last_tokens = tokens
                            payload.last_finish_reason = finish_reason
                            reason = error
                            if not reason and finish_reason == "length":
                                reason = "output truncated at max tokens"
                            if not reason and not raw.strip():
                                reason = "empty response"
                            if not reason and _has_bad_repeat(raw):
                                reason = "repeated output"
                            if reason:
                                payload.reasons.append(reason)
                                if not stop_requested and payload.attempts < max_retries:
                                    payload.attempts += 1
                                    payload.ready_at = loop.time() + (2 * payload.attempts if error else 0)
                                    payload.document.ready.appendleft(payload)
                                elif not stop_requested:
                                    failed_raw, failed_docir = _failure_record(payload.page, reason, payload)
                                    await asyncio.to_thread(
                                        _record_page, output_root, payload.document.relative, failed_raw, failed_docir
                                    )
                                    payload.document.errors += 1
                                    payload.document.busy -= 1
                                    queued_memory -= payload.memory
                                    CONSOLE.print(
                                        f"[red]OCR failed[/red] {payload.document.relative} page {payload.page}: {reason}"
                                    )
                                else:
                                    payload.document.busy -= 1
                                    queued_memory -= payload.memory
                            else:
                                task = asyncio.create_task(
                                    asyncio.to_thread(_prepare_page, payload, raw, tokens, finish_reason, output_root / "ImagePool")
                                )
                                process_tasks[task] = (payload, False)
                            continue
                        payload, _ = process_tasks.pop(future)
                        doc = payload.document
                        try:
                            raw_record, docir, assets = future.result()
                            for asset in assets:
                                image_catalog.execute(
                                    "INSERT OR IGNORE INTO images VALUES (?, ?, 'image/png', ?, ?)",
                                    (asset["blake3"], asset["path"], asset["width"], asset["height"]),
                                )
                            image_catalog.commit()
                            await asyncio.to_thread(_record_page, output_root, doc.relative, raw_record, docir)
                            doc.completed.add(payload.page)
                            progress.advance(progress_task)
                            connection.execute(
                                "UPDATE ocr_documents SET completed_pages = ?, updated_at = ? WHERE run_id = ? AND relative_path = ?",
                                (len(doc.completed), _now(), run_id, doc.relative),
                            )
                        except Exception as exc:
                            reason = f"{type(exc).__name__}: {exc}"[:500]
                            failed_raw, failed_docir = _failure_record(payload.page, reason, payload)
                            await asyncio.to_thread(_record_page, output_root, doc.relative, failed_raw, failed_docir)
                            doc.errors += 1
                            CONSOLE.print(f"[red]Page conversion failed[/red] {doc.relative} page {payload.page}: {reason}")
                        finally:
                            doc.busy -= 1
                            queued_memory -= payload.memory
                    for doc in list(active):
                        if stop_requested:
                            continue
                        if doc.next_page <= doc.pages or doc.busy or doc.ready:
                            continue
                        if len(doc.completed) == doc.pages:
                            stat = (input_root / doc.relative).stat()
                            inv = inventory_by_path[doc.relative]
                            if (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) != (
                                inv["size_bytes"],
                                inv["mtime_ns"],
                                inv["ctime_ns"],
                            ):
                                raise click.ClickException(f"PDF changed during OCR: {doc.relative}")
                            header = {
                                "type": "document",
                                "schema_version": 2,
                                "run_id": run_id,
                                "source_pdf": doc.relative,
                                "source_blake3": doc.source_hash,
                                "pages": doc.pages,
                                "settings": config,
                                "processed_at": _now(),
                            }
                            await asyncio.to_thread(_finalize, output_root, doc.relative, header, doc.pages)
                            connection.execute(
                                "UPDATE ocr_documents SET status = 'published', completed_pages = ?, updated_at = ? WHERE run_id = ? AND relative_path = ?",
                                (doc.pages, _now(), run_id, doc.relative),
                            )
                        else:
                            connection.execute(
                                "UPDATE ocr_documents SET status = 'error', last_error = ?, updated_at = ? WHERE run_id = ? AND relative_path = ?",
                                (f"{doc.pages - len(doc.completed)} pages unfinished", _now(), run_id, doc.relative),
                            )
                        active.remove(doc)
                    connection.commit()
        loop.remove_signal_handler(signal.SIGINT)
        loop.remove_signal_handler(signal.SIGTERM)
        if stop_requested:
            for doc in active:
                connection.execute(
                    "UPDATE ocr_documents SET status = 'interrupted', completed_pages = ?, updated_at = ? "
                    "WHERE run_id = ? AND relative_path = ?",
                    (len(doc.completed), _now(), run_id, doc.relative),
                )
            connection.commit()
            CONSOLE.print(
                f"[yellow]Stopped.[/yellow] {int(progress.tasks[0].completed):,}/{total_pages:,} pages saved; rerun to resume."
            )
            return True
        remaining = sum(len(doc.completed) < doc.pages for doc in documents)
        if remaining:
            raise click.ClickException(f"{remaining} documents have unfinished pages; rerun to retry them")
        return False
    finally:
        connection.commit()
        connection.close()
        image_catalog.close()


@click.command("ocr")
@click.option(
    "--database", type=click.Path(path_type=Path, exists=True, dir_okay=False), default=DEFAULT_DATABASE, show_default=True
)
@click.option("--input-root", type=click.Path(path_type=Path, exists=True, file_okay=False), default=None)
@click.option("--output-root", type=click.Path(path_type=Path, file_okay=False), required=True)
@click.option("--api-base", default=settings.VLLM_API_BASE, show_default=True)
@click.option("--model", default=settings.VLLM_MODEL_NAME, show_default=True)
@click.option("-j", "--jobs", type=click.IntRange(1), default=4, show_default=True, help="PDF rendering process pool size.")
@click.option("--inflight-pages", type=click.IntRange(1), default=8, show_default=True)
@click.option("--buffer-mib", type=click.IntRange(32), default=512, show_default=True)
@click.option(
    "--file-list",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="UTF-8 text file with one inventoried PDF path per line, relative to the PDF root or absolute.",
)
@click.option("--prefix", default="", help="Source-relative path prefix to process.")
@click.option("--all", "all_documents", is_flag=True, help="Explicitly process every inventoried PDF.")
@click.option("--limit-documents", type=click.IntRange(1), default=None, help="Limit a pilot to this many PDFs.")
@click.option("--request-timeout", type=click.FloatRange(min=1), default=600.0, show_default=True)
@click.option("--max-retries", type=click.IntRange(0), default=settings.MAX_VLLM_RETRIES, show_default=True)
@click.option(
    "--shutdown-grace",
    type=click.FloatRange(min=0),
    default=10.0,
    show_default=True,
    help="Seconds to let in-flight OCR requests finish after Ctrl+C before cancelling them.",
)
def ocr_command(
    database: Path,
    input_root: Path | None,
    output_root: Path,
    api_base: str,
    model: str,
    jobs: int,
    inflight_pages: int,
    buffer_mib: int,
    file_list: Path | None,
    prefix: str,
    all_documents: bool,
    limit_documents: int | None,
    request_timeout: float,
    max_retries: int,
    shutdown_grace: float,
) -> None:
    """OCR inventoried PDFs into raw Chandra JSONL, DocIR, and ImagePool assets."""
    database = database.resolve(strict=True)
    with sqlite3.connect(database) as connection:
        stored = connection.execute("SELECT value FROM metadata WHERE key = 'root'").fetchone()
    if not stored:
        raise click.ClickException("inventory database has no source root")
    root = (input_root or Path(stored[0])).resolve(strict=True)
    if str(root) != stored[0]:
        raise click.ClickException(f"inventory belongs to {stored[0]}")
    if file_list is not None and (prefix or limit_documents is not None or all_documents):
        raise click.ClickException("--file-list cannot be combined with --prefix, --limit-documents, or --all")
    if all_documents and (prefix or limit_documents is not None):
        raise click.ClickException("--all cannot be combined with --prefix or --limit-documents")
    if file_list is None and not prefix and limit_documents is None and not all_documents:
        raise click.ClickException("select PDFs with --file-list, --prefix, or --limit-documents; use --all for the full inventory")
    output = output_root.resolve()
    if output == root or root in output.parents:
        raise click.ClickException("output root must be outside the source PDF tree")
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".ocr.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise click.ClickException(f"another OCR process is using {output}") from exc
        try:
            interrupted = asyncio.run(
                _run_ocr(
                    database,
                    root,
                    output,
                    api_base.rstrip("/"),
                    model,
                    jobs,
                    inflight_pages,
                    buffer_mib,
                    file_list,
                    prefix,
                    limit_documents,
                    request_timeout,
                    max_retries,
                    shutdown_grace,
                )
            )
            if interrupted:
                raise SystemExit(130)
        except KeyboardInterrupt:
            raise click.Abort() from None
