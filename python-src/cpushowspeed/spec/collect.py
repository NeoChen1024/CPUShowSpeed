"""Resumable collection of published SPEC CPU result files."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import time
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import click

GENERATIONS = ("cpu95", "cpu2000", "cpu2006", "cpu2017", "cpu2026")
BASE = "https://www.spec.org"
USER_AGENT = "CPUShowSpeed/0.0 (historical SPEC result research)"
RESULT_NAME = {
    "cpu95": re.compile(r"(?:p\d+|cpu95-[\w-]+)\.(?:html|txt|ps)$", re.I),
    "cpu2000": re.compile(r"cpu2000-[\w-]+\.(?:html|txt|pdf|ps|cfg)$", re.I),
    "cpu2006": re.compile(r"cpu2006-[\w-]+\.(?:html|csv|txt|pdf|ps|cfg)$", re.I),
    "cpu2017": re.compile(r"cpu2017-[\w-]+\.(?:html|csv|txt|pdf|ps|cfg)$", re.I),
    "cpu2026": re.compile(r"cpu2026-[\w-]+\.(?:html|csv|txt|pdf|ps|cfg)$", re.I),
}


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def links(document: bytes) -> list[str]:
    parser = LinkParser()
    parser.feed(document.decode("utf-8", errors="replace"))
    return parser.links


class SectionLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.section = ""
        self.heading_tag: str | None = None
        self.heading_parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h2", "h3"}:
            self.heading_tag = tag
            self.heading_parts = []
        elif tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append((href, self.section))

    def handle_data(self, data: str) -> None:
        if self.heading_tag:
            self.heading_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self.heading_tag:
            self.section = " ".join(" ".join(self.heading_parts).split())
            self.heading_tag = None


def section_links(document: bytes) -> list[tuple[str, str]]:
    parser = SectionLinkParser()
    parser.feed(document.decode("utf-8", errors="replace"))
    return parser.links


def track(section: str) -> str:
    name = section.upper()
    kind = "floating-point" if "FP" in name or "FLOAT" in name else "integer" if "INT" in name else "unknown"
    mode = "rate" if "RATE" in name or "THRUPUT" in name else "speed"
    return f"{kind}-{mode}"


def fetch(url: str, attempts: int = 3) -> tuple[bytes, str]:
    if urlparse(url).hostname not in {"www.spec.org", "spec.org", "www.netlib.org", "netlib.org"}:
        raise ValueError(f"unexpected host: {url}")
    for attempt in range(attempts):
        try:
            with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=45) as response:
                if urlparse(response.url).hostname not in {"www.spec.org", "spec.org", "www.netlib.org", "netlib.org"}:
                    raise ValueError(f"unexpected redirect: {response.url}")
                return response.read(), response.headers.get("Content-Type", "")
        except (HTTPError, URLError, TimeoutError) as exc:
            if isinstance(exc, HTTPError) and exc.code not in {429, 500, 502, 503, 504}:
                raise
            if attempt == attempts - 1:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def save_raw(path: Path, body: bytes, url: str, content_type: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".partial")
    tmp.write_bytes(body)
    tmp.replace(path)
    metadata = {
        "source_url": url,
        "retrieved_on": datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat(),
        "sha256": hashlib.sha256(body).hexdigest(),
        "content_type": content_type,
    }
    meta_path = path.with_name(path.name + ".meta.json")
    tmp_meta = meta_path.with_name(meta_path.name + ".partial")
    tmp_meta.write_text(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")
    tmp_meta.replace(meta_path)


def get_cached(url: str, path: Path, *, refresh: bool, delay: float) -> bytes:
    if path.exists() and not refresh:
        return path.read_bytes()
    body, content_type = fetch(url)
    save_raw(path, body, url, content_type)
    if delay:
        time.sleep(delay)
    return body


def quarter_pages(generation: str, document: bytes) -> list[tuple[str, str]]:
    root = f"{BASE}/{generation}/results/"
    periods: dict[str, str] = {}
    for href in links(document):
        url = urljoin(root, href)
        parsed = urlparse(url)
        if parsed.hostname not in {"www.spec.org", "spec.org"}:
            continue
        match = re.fullmatch(rf"/{generation}/results/(res[\w-]+)/?", parsed.path)
        if match:
            periods[match.group(1)] = f"{root}{match.group(1)}/"
    return sorted(periods.items())


def result_links(generation: str, period: str, document: bytes) -> dict[str, dict[str, object]]:
    page = f"{BASE}/{generation}/results/{period}/"
    results: dict[str, dict[str, object]] = {}
    for href, section in section_links(document):
        url = urljoin(page, href)
        parsed = urlparse(url)
        if parsed.hostname not in {"www.spec.org", "spec.org"}:
            continue
        if not parsed.path.startswith(f"/{generation}/results/{period}/"):
            continue
        filename = parsed.path.rsplit("/", 1)[-1]
        if not RESULT_NAME[generation].fullmatch(filename):
            continue
        stem, extension = filename.rsplit(".", 1)
        entry = results.setdefault(stem, {"formats": {}, "section": section, "track": track(section)})
        entry["formats"][extension.lower()] = url
    return results


def collect_indexes(generations: tuple[str, ...], raw_dir: Path, manifest: Path, delay: float, refresh: bool) -> None:
    records: list[dict[str, object]] = []
    for generation in generations:
        root_url = f"{BASE}/{generation}/results/"
        root_html = get_cached(root_url, raw_dir / generation / "index.html", refresh=refresh, delay=delay)
        periods = quarter_pages(generation, root_html)
        click.echo(f"{generation}: {len(periods)} publication periods", err=True)
        if not periods:
            raise click.ClickException(f"no publication periods found for {generation}")
        for number, (period, page_url) in enumerate(periods, 1):
            page_html = get_cached(page_url, raw_dir / generation / period / "index.html", refresh=refresh, delay=delay)
            found = result_links(generation, period, page_html)
            if not found:
                raise click.ClickException(f"no result links found in {page_url}")
            for result_id, entry in sorted(found.items()):
                records.append(
                    {
                        "generation": generation,
                        "period": period,
                        "result_id": result_id,
                        "index_url": page_url,
                        **entry,
                    }
                )
            click.echo(f"  {period}: {len(found)} results ({number}/{len(periods)})", err=True)
    if manifest.exists() and set(generations) != set(GENERATIONS):
        selected = set(generations)
        for line in manifest.read_text().splitlines():
            previous = json.loads(line)
            if previous["generation"] not in selected:
                records.append(previous)
    generation_order = {generation: number for number, generation in enumerate(GENERATIONS)}
    records.sort(key=lambda record: (generation_order[record["generation"]], record["period"], record["result_id"]))
    manifest.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest.with_name(manifest.name + ".partial")
    with tmp.open("w") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(manifest)
    click.echo(f"Wrote {len(records)} result links to {manifest}", err=True)


def collect_cpu92_rate_index(raw_dir: Path, manifest: Path, delay: float, refresh: bool) -> dict[str, int]:
    """Collect the separately published Netlib CINT92 rate indexes."""
    root = "https://www.netlib.org/performance/html/"
    index = get_cached(root + "spec.html", raw_dir / "cpu92" / "netlib" / "spec.html", refresh=refresh, delay=delay)
    summary_pattern = re.compile(r"spec(?:base)?\.crint92\.\d+_\d+\.col0\.html", re.I)
    detail_pattern = re.compile(r"spec\.[\w.-]+\.crint(?:92)?\.\d+_\d+\.notes\.html", re.I)
    summaries = sorted(
        {
            urlparse(href).path.rsplit("/", 1)[-1]
            for href in links(index)
            if summary_pattern.fullmatch(urlparse(href).path.rsplit("/", 1)[-1])
        }
    )
    if not summaries:
        raise ValueError("no CINT92 rate summaries in Netlib index")
    records = []
    for filename in summaries:
        url = root + filename
        body = get_cached(url, raw_dir / "cpu92" / "netlib" / "rate" / filename, refresh=refresh, delay=delay)
        names = sorted(
            {
                urlparse(href).path.rsplit("/", 1)[-1]
                for href in links(body)
                if detail_pattern.fullmatch(urlparse(href).path.rsplit("/", 1)[-1])
            }
        )
        for name in names:
            records.append(
                {
                    "summary_url": url,
                    "detail_url": root + name,
                    "metric": "SPECrate_base_int92" if filename.startswith("specbase.") else "SPECrate_int92",
                }
            )
        click.echo(f"{filename}: {len(names)} rate disclosures", err=True)
    combined_name = "new.spec.crint92.col0.html"
    combined = get_cached(root + combined_name, raw_dir / "cpu92" / "netlib" / "rate" / combined_name, refresh=refresh, delay=delay)
    combined_names = {
        urlparse(href).path.rsplit("/", 1)[-1]
        for href in links(combined)
        if detail_pattern.fullmatch(urlparse(href).path.rsplit("/", 1)[-1])
    }
    issue_names = {urlparse(row["detail_url"]).path.rsplit("/", 1)[-1] for row in records}
    if combined_names - issue_names:
        raise ValueError(f"combined rate summary has {len(combined_names - issue_names)} disclosures absent from issue summaries")
    issue_only = sorted(issue_names - combined_names)
    if issue_only:
        click.echo(f"Netlib combined rate summary omits {len(issue_only)} issue-linked disclosure(s): {issue_only}", err=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest.with_name(manifest.name + ".partial")
    with tmp.open("w", encoding="utf-8") as stream:
        for record in sorted(records, key=lambda row: (row["summary_url"], row["detail_url"])):
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    tmp.replace(manifest)
    return {
        "issue_summaries": len(summaries),
        "detail_references": len(records),
        "unique_disclosures": len(issue_names),
        "issue_only_disclosures": issue_only,
    }


def fetch_cpu92_rate_details(manifest: Path, raw_dir: Path, limit: int | None, delay: float) -> dict[str, int]:
    if not manifest.exists():
        raise ValueError(f"CPU92 rate manifest missing: {manifest}")
    urls = sorted({json.loads(line)["detail_url"] for line in manifest.read_text().splitlines()})
    downloaded = cached = 0
    for url in urls:
        path = raw_dir / "cpu92" / "netlib" / "rate" / "details" / urlparse(url).path.rsplit("/", 1)[-1]
        if path.exists():
            cached += 1
            continue
        if limit is not None and downloaded >= limit:
            break
        body = get_cached(url, path, refresh=False, delay=delay)
        if b"SPEC Benchmark CINT92" not in body or b"SPECrate_int92" not in body:
            raise ValueError(f"unexpected CPU92 rate disclosure: {url}")
        downloaded += 1
        if downloaded % 25 == 0:
            click.echo(f"Downloaded {downloaded}/{len(urls)} CPU92 rate disclosures", err=True)
    return {"disclosures": len(urls), "downloaded": downloaded, "cached": cached}


def verify_bulk(manifest: Path, raw_dir: Path, generations: tuple[str, ...]) -> None:
    if not manifest.exists():
        raise click.ClickException(f"index manifest does not exist: {manifest}")
    indexed: dict[str, set[tuple[str, str]]] = {generation: set() for generation in generations}
    for line in manifest.read_text().splitlines():
        record = json.loads(line)
        if record["generation"] in indexed:
            indexed[record["generation"]].add((record["period"], record["result_id"]))
    failed = False
    for generation in generations:
        bulk = raw_dir / generation / "bulk.csv"
        if not bulk.exists():
            raise click.ClickException(f"bulk export does not exist: {bulk}")
        exported: set[tuple[str, str]] = set()
        invalid = 0
        rows = 0
        with bulk.open(newline="", encoding="utf-8", errors="replace") as stream:
            for row in csv.DictReader(stream):
                rows += 1
                html_links = [href for href in links((row.get("Disclosure") or "").encode()) if href.lower().endswith(".html")]
                matched = [re.search(r"/results/(res[^/]+)/([^/]+)\.html$", href) for href in html_links]
                match = next((item for item in matched if item), None)
                if match is None:
                    invalid += 1
                else:
                    exported.add((match.group(1), match.group(2)))
        missing_bulk = len(indexed[generation] - exported)
        missing_index = len(exported - indexed[generation])
        duplicates = rows - len(exported) - invalid
        click.echo(
            f"{generation}: rows={rows} index={len(indexed[generation])} "
            f"missing_bulk={missing_bulk} missing_index={missing_index} "
            f"invalid_links={invalid} duplicate_ids={duplicates}",
            err=True,
        )
        failed |= bool(missing_bulk or missing_index or invalid or duplicates)
    if failed:
        raise click.ClickException("bulk CSV and quarterly index disagree")


def collect_bulk(generations: tuple[str, ...], raw_dir: Path, refresh: bool) -> None:
    for generation in generations:
        url = f"{BASE}/cgi-bin/osgresults?conf={generation};op=dump;format=csvdump"
        target = raw_dir / generation / "bulk.csv"
        body = get_cached(url, target, refresh=refresh, delay=0)
        if not body.startswith(b"Benchmark,"):
            raise click.ClickException(f"bulk response is not SPEC result CSV: {url}")
        reader = csv.reader(io.StringIO(body.decode("utf-8-sig", errors="replace")))
        header = next(reader)
        count = sum(1 for _ in reader)
        click.echo(f"{generation}: {count} rows, {len(header)} columns -> {target}", err=True)


def collect_disclosures(
    manifest: Path,
    raw_dir: Path,
    generations: tuple[str, ...],
    selected_track: str,
    period: str | None,
    limit: int | None,
    delay: float,
) -> None:
    if not manifest.exists():
        raise click.ClickException(f"index manifest does not exist: {manifest}")
    completed = 0
    skipped = 0
    unavailable = 0
    for line in manifest.read_text().splitlines():
        record = json.loads(line)
        generation = record["generation"]
        if (
            generation not in generations
            or (selected_track != "all" and record.get("track") != selected_track)
            or (period is not None and record["period"] != period)
        ):
            continue
        formats = record["formats"]
        extension = "html" if generation == "cpu95" else "csv" if "csv" in formats else "html"
        url = formats.get(extension)
        if not url:
            unavailable += 1
            continue
        target = raw_dir / generation / record["period"] / f"{record['result_id']}.{extension}"
        if target.exists():
            skipped += 1
            continue
        if limit is not None and completed >= limit:
            break
        try:
            body, content_type = fetch(url)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            click.echo(f"FAILED {url}: {exc}", err=True)
            unavailable += 1
            continue
        save_raw(target, body, url, content_type)
        completed += 1
        if completed % 25 == 0:
            click.echo(f"Downloaded {completed}; already present {skipped}; failed/unavailable {unavailable}", err=True)
        if delay:
            time.sleep(delay)
    click.echo(f"Downloaded {completed}; already present {skipped}; failed/unavailable {unavailable}", err=True)
    if unavailable:
        raise click.ClickException("some disclosures were unavailable; rerun to retry")


@click.group()
def spec() -> None:
    """Collect published SPEC CPU result files."""


@spec.command("index")
@click.option(
    "--generation", "generations", type=click.Choice(GENERATIONS), multiple=True, help="Repeat to select generations; default: all."
)
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option(
    "--manifest", type=click.Path(path_type=Path), default=Path("data/derived/spec/result-links.jsonl"), show_default=True
)
@click.option("--delay", type=click.FloatRange(min=0), default=0.5, show_default=True, help="Seconds between uncached requests.")
@click.option("--refresh", is_flag=True, help="Refresh cached publication indexes.")
def index_command(generations: tuple[str, ...], raw_dir: Path, manifest: Path, delay: float, refresh: bool) -> None:
    """Cache publication indexes and enumerate individual result files."""
    collect_indexes(generations or GENERATIONS, raw_dir, manifest, delay, refresh)


@spec.command("verify")
@click.option(
    "--generation", "generations", type=click.Choice(GENERATIONS), multiple=True, help="Repeat to select generations; default: all."
)
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option(
    "--manifest", type=click.Path(path_type=Path), default=Path("data/derived/spec/result-links.jsonl"), show_default=True
)
def verify_command(generations: tuple[str, ...], raw_dir: Path, manifest: Path) -> None:
    """Check full-result CSV IDs against quarterly index IDs."""
    verify_bulk(manifest, raw_dir, generations or GENERATIONS)


@spec.command("cpu92-rate-index")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option(
    "--manifest",
    type=click.Path(path_type=Path),
    default=Path("data/derived/spec/cpu92-netlib-rate-links.jsonl"),
    show_default=True,
)
@click.option("--delay", type=click.FloatRange(min=0), default=0.5, show_default=True)
@click.option("--refresh", is_flag=True)
def cpu92_rate_index_command(raw_dir: Path, manifest: Path, delay: float, refresh: bool) -> None:
    """Cache Netlib's surviving CINT92 rate issue and combined indexes."""
    try:
        result = collect_cpu92_rate_index(raw_dir, manifest, delay, refresh)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))


@spec.command("cpu92-rate-fetch")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option(
    "--manifest",
    type=click.Path(path_type=Path),
    default=Path("data/derived/spec/cpu92-netlib-rate-links.jsonl"),
    show_default=True,
)
@click.option("--limit", type=click.IntRange(min=1), help="Maximum new disclosures in this run.")
@click.option("--delay", type=click.FloatRange(min=0), default=0.5, show_default=True)
def cpu92_rate_fetch_command(raw_dir: Path, manifest: Path, limit: int | None, delay: float) -> None:
    """Cache CINT92 rate detail reports while preserving their source URLs."""
    try:
        result = fetch_cpu92_rate_details(manifest, raw_dir, limit, delay)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))


@spec.command("dump")
@click.option(
    "--generation", "generations", type=click.Choice(GENERATIONS), multiple=True, help="Repeat to select generations; default: all."
)
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option("--refresh", is_flag=True, help="Refresh the cached official CSV export.")
def dump_command(generations: tuple[str, ...], raw_dir: Path, refresh: bool) -> None:
    """Download SPEC's official full-result CSV datasets."""
    collect_bulk(generations or GENERATIONS, raw_dir, refresh)


@spec.command("fetch")
@click.option(
    "--generation", "generations", type=click.Choice(GENERATIONS), multiple=True, help="Repeat to select generations; default: all."
)
@click.option(
    "--track",
    "selected_track",
    type=click.Choice(("integer-rate", "floating-point-rate")),
    default="integer-rate",
    show_default=True,
)
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option(
    "--manifest", type=click.Path(path_type=Path), default=Path("data/derived/spec/result-links.jsonl"), show_default=True
)
@click.option("--period", help="Restrict to one publication period, such as res9509.")
@click.option("--limit", type=click.IntRange(min=1), help="Maximum new disclosures to download in this run.")
@click.option("--delay", type=click.FloatRange(min=0), default=0.5, show_default=True, help="Seconds between requests.")
def fetch_command(
    generations: tuple[str, ...],
    selected_track: str,
    raw_dir: Path,
    manifest: Path,
    period: str | None,
    limit: int | None,
    delay: float,
) -> None:
    """Download individual disclosures, preferring CSV when available."""
    collect_disclosures(manifest, raw_dir, generations or GENERATIONS, selected_track, period, limit, delay)
