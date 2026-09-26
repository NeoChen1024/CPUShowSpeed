"""Bounded, source-listed collection of classic benchmark documents."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import tempfile
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urldefrag, urljoin, urlsplit
from urllib.request import Request, urlopen

import blake3
import click
from bs4 import BeautifulSoup, UnicodeDammit
from cpushowspeed.docir_rich_table import convert_rich_table
from cpushowspeed.docir_table import TableConversionError

DEFAULT_SOURCES = Path("docs/data/classic-benchmark-sources.csv")


def normalize_url(url):
    url = urldefrag(url)[0]
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.netloc or p.username or p.password:
        raise ValueError(f"unsupported source URL: {url}")
    return quote(url, safe=":/?=&%+;,@!$'()*[]~")


def load_sources(path):
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    seen = set()
    for row in rows:
        if not all(row.get(k) for k in ("source_id", "url", "provider", "lineage", "family", "role")):
            raise ValueError("incomplete source record")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", row["source_id"]):
            raise ValueError("invalid source ID")
        if row["source_id"] in seen:
            raise ValueError("duplicate source ID")
        seen.add(row["source_id"])
        row["url"] = normalize_url(row["url"])
    return rows


def immutable_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
            temporary = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != data:
                raise ValueError(f"content conflict: {path}")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def fetch_source(source, root, timeout, max_bytes):
    record = dict(source, retrieved_date=datetime.now(timezone.utc).date().isoformat())
    try:
        request = Request(source["url"], headers={"User-Agent": "CPUShowSpeed historical benchmark research/0.1"})
        with urlopen(request, timeout=timeout) as response:
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise ValueError(f"response exceeds {max_bytes} bytes")
            digest = blake3.blake3(data).hexdigest()
            target = root / "blobs" / digest[:2] / digest
            immutable_write(target, data)
            record.update(
                status="downloaded",
                final_url=response.url,
                http_status=response.status,
                content_type=response.headers.get("Content-Type"),
                blake3=digest,
                bytes=len(data),
                blob_path=str(target),
                last_modified=response.headers.get("Last-Modified"),
            )
    except Exception as exc:
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    return record


def extract_html(data, source_url):
    """Keep raw table HTML and preformatted layouts; do not infer score columns."""
    decoded = UnicodeDammit(data, is_html=True)
    if decoded.unicode_markup is None:
        raise ValueError("cannot decode HTML")
    soup = BeautifulSoup(decoded.unicode_markup, "html.parser")
    blocks = []
    for index, table in enumerate(soup.find_all("table")):
        if table.find_parent("table") is not None:
            continue
        html = str(table)
        item = {"kind": "table", "table_index": index, "html": html, "verification": "unreviewed_web_extraction"}
        try:
            item.update(convert_rich_table(html))
        except TableConversionError as exc:
            item.update(conversion_status="failed", error=str(exc))
        blocks.append(item)
    for index, pre in enumerate(soup.find_all("pre")):
        blocks.append(
            {"kind": "preformatted", "pre_index": index, "text": pre.get_text(), "verification": "unreviewed_web_extraction"}
        )
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(source_url, a["href"])
        if urlsplit(href).scheme in {"http", "https"}:
            links.append({"url": normalize_url(href), "fragment": urldefrag(href)[1], "label": a.get_text(" ", strip=True)})
    return {
        "encoding": decoded.original_encoding,
        "title": soup.title.get_text(" ", strip=True) if soup.title else None,
        "parser": "beautifulsoup4/html.parser",
        "blocks": blocks,
        "links": links,
        "text": soup.get_text("\n", strip=True),
    }


@click.group()
def classic():
    """Archive classic benchmark sources and extract unreviewed reading data."""


@classic.command("collect")
@click.option("--sources", type=click.Path(path_type=Path, exists=True, dir_okay=False), default=DEFAULT_SOURCES, show_default=True)
@click.option("--raw-root", type=click.Path(path_type=Path), default=Path("data/raw/classic"), show_default=True)
@click.option("--workers", type=click.IntRange(1, 8), default=2, show_default=True)
@click.option("--timeout", type=click.FloatRange(min=1), default=60, show_default=True)
@click.option("--max-mib", type=click.IntRange(1), default=50, show_default=True)
def collect(sources, raw_root, workers, timeout, max_mib):
    """Fetch only listed URLs; archive bytes and a unique immutable run manifest."""
    try:
        rows = load_sources(sources)
        records = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for record in pool.map(lambda s: fetch_source(s, raw_root, timeout, max_mib * 1024 * 1024), rows):
                records.append(record)
                click.echo(f"{record['source_id']}: {record['status']}", err=True)
        manifest = raw_root / "manifests" / f"{uuid.uuid4().hex}.jsonl"
        immutable_write(manifest, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records).encode())
        failed = sum(r["status"] == "failed" for r in records)
        click.echo(json.dumps({"manifest": str(manifest), "downloaded": len(records) - failed, "failed": failed}))
        if failed:
            raise click.ClickException("some sources failed; see immutable manifest")
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@classic.command("extract")
@click.argument("manifest", type=click.Path(path_type=Path, exists=True, dir_okay=False))
@click.option("--output-root", type=click.Path(path_type=Path), default=Path("data/derived/classic"), show_default=True)
def extract(manifest, output_root):
    """Extract HTML tables, PRE layouts, text and links; leave other files raw."""
    output_root.mkdir(parents=True, exist_ok=True)
    summary = []
    try:
        for line in manifest.read_text().splitlines():
            record = json.loads(line)
            if record["status"] != "downloaded":
                continue
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", record["source_id"]):
                raise ValueError("invalid source ID")
            path = Path(record["blob_path"])
            data = path.read_bytes()
            if blake3.blake3(data).hexdigest() != record["blake3"]:
                raise ValueError(f"hash mismatch: {path}")
            mime = (record.get("content_type") or "").lower()
            item = {
                "source_id": record["source_id"],
                "url": record["url"],
                "blake3": record["blake3"],
                "lineage": record["lineage"],
                "bytes": len(data),
            }
            if "html" in mime or data.lstrip().lower().startswith((b"<html", b"<!doctype html")):
                parsed = extract_html(data, record["final_url"])
                parsed.update(source=record, manifest=str(manifest))
                target = output_root / (record["source_id"] + "-" + record["blake3"][:12] + ".json")
                target.write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n")
                item.update(
                    extraction_path=str(target),
                    tables=sum(b["kind"] == "table" for b in parsed["blocks"]),
                    preformatted=sum(b["kind"] == "preformatted" for b in parsed["blocks"]),
                    conversion_failures=sum(b.get("conversion_status") == "failed" for b in parsed["blocks"]),
                )
            elif zipfile.is_zipfile(io.BytesIO(data)):
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    members = [
                        {"name": x.filename, "bytes": x.file_size, "compressed_bytes": x.compress_size, "crc32": x.CRC}
                        for x in archive.infolist()
                    ]
                target = output_root / (record["source_id"] + "-" + record["blake3"][:12] + ".json")
                target.write_text(json.dumps({"source": record, "manifest": str(manifest), "members": members}, indent=2) + "\n")
                item.update(extraction_path=str(target), archive_members=len(members), extraction_status="archive_inventory_only")
            else:
                item["extraction_status"] = "non_html_preserved_raw"
            summary.append(item)
        dest = output_root / (manifest.stem + "-summary.json")
        dest.write_text(json.dumps(summary, indent=2) + "\n")
        click.echo(json.dumps({"summary": str(dest), "sources": len(summary)}))
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
