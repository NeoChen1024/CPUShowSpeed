"""Secondary-source CPU SKU release chronology from cached Wikipedia processor tables.

Dates describe CPU SKU release, not system availability. `sku_key` is the versioned
identity rule `sku-key-v1`; matching against observations happens in curated_identity.
"""

import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

import click
from bs4 import BeautifulSoup

CATALOG = Path("research/data/historical/cpu-sku-chronology.csv")
SOURCES = Path("research/data/historical/cpu-sku-sources.json")
AUDIT = Path("research/data/historical/cpu-sku-audit.json")
CACHE = Path("data/derived/documents/cpu-chronology")
API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "CPUShowSpeed CPU chronology research (https://github.com/NeoChen1024/CPUShowSpeed)"

PAGES = [
    "List of Intel Xeon processors (P6-based)",
    "List of Intel Xeon processors (NetBurst-based)",
    "List of Intel Xeon processors (Yonah-based)",
    "List of Intel Xeon processors (Core-based)",
    "List of Intel Xeon processors (Nehalem-based)",
    "List of Intel Xeon processors (Sandy Bridge–based)",
    "List of Intel Xeon processors (Ivy Bridge–based)",
    "List of Intel Xeon processors (Haswell-based)",
    "List of Intel Xeon processors (Broadwell-based)",
    "List of Intel Xeon processors (Skylake-based)",
    "List of Intel Xeon processors (Kaby Lake-based)",
    "List of Intel Xeon processors (Coffee Lake-based)",
    "List of Intel Xeon processors (Cascade Lake–based)",
    "List of Intel Xeon processors (Ice Lake-based)",
    "List of Intel Xeon processors (Comet Lake-based)",
    "List of Intel Xeon processors (Rocket Lake-based)",
    "Sapphire Rapids",
    "Emerald Rapids",
    "Granite Rapids",
    "Sierra Forest",
    "List of AMD Opteron processors",
    "Epyc",
]

FIELDS = [
    "sku_key",
    "model_text",
    "base_clock_mhz",
    "release_date",
    "release_date_raw",
    "source_title",
    "source_url",
    "source_locator",
    "source_section",
    "source_revision",
    "snapshot_sha256",
    "reviewed_on",
]

MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


# ---------------------------------------------------------------- SKU identity

_NOISE = re.compile(r"\((?:r|tm)\)|®|™|\bintel\b|\bamd\b|\bprocessors?\b|\bcpu\b|\b(?:dual|quad|six|multi)-core\b|@.*$", re.I)
_INTEL_MODEL = re.compile(
    r"\b(?:(?P<tier>platinum|gold|silver|bronze|max|w|d|e[357]?)(?:\s+|-))?"
    r"(?P<num>[a-z]?\d{4}[a-z]{0,2})(?:\s+(?P<ver>v\d))?\b",
    re.I,
)
# EPYC models may carry letters inside the number (7H12, 75F3, 4584PX).
_AMD_MODEL = re.compile(r"\b(?P<num>\d(?=(?:[a-z]*\d){1,})[0-9a-z]{2,5})(?:\s+(?P<suffix>se|he|ee))?\b", re.I)


def _clean(text):
    # Trademarks first, then every parenthetical: clocks, buses, caches, sockets ("939-pin") are never the model.
    text = _NOISE.sub(" ", str(text or "").replace("\xa0", " "))
    text = re.sub(r"\([^)]*\)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def sku_key(text):
    """Return one normalized SKU key, or None when the text is not exactly one known SKU."""
    s = _clean(text)
    low = s.lower()
    if "xeon" in low:
        rest = low.split("xeon", 1)[1]
        models = list(_INTEL_MODEL.finditer(rest))
        if len(models) != 1 or not re.search(r"\d", models[0]["num"]):
            return None
        m = models[0]
        if rest[: m.start()].strip() not in ("", "6", "scalable"):
            return None
        tier = (m["tier"] or "").lower()
        tier = {"w": "w-", "d": "d-", "e": "e-", "e3": "e3-", "e5": "e5-", "e7": "e7-"}.get(tier, tier + " " if tier else "")
        return "intel xeon " + tier + m["num"].upper() + (" " + m["ver"].lower() if m["ver"] else "")
    for family in ("epyc", "opteron"):
        if family in low:
            rest = low.split(family, 1)[1]
            models = list(_AMD_MODEL.finditer(rest))
            if len(models) != 1 or rest[: models[0].start()].strip():
                return None
            m = models[0]
            num, suffix = m["num"].upper(), (m["suffix"] or "").upper()
            attached = re.fullmatch(r"(\d{3,4})(SE|HE|EE)", num) if family == "opteron" else None
            if attached and not suffix:
                num, suffix = attached[1], attached[2]
            return "amd " + family + " " + num + (" " + suffix if suffix else "")
    return None


# ---------------------------------------------------------------- dates and clocks


def parse_dates(text):
    """Every date in a cell at its stated precision; quarters keep only the year."""
    s = str(text or "").replace("\xa0", " ")
    out = []
    for m in re.finditer(
        r"(?:(?P<dd>\d{1,2})\s+(?P<mon3>[A-Za-z]{3,9})\.?,?\s+(?P<y3>(?:19|20)\d{2}))"
        r"|(?:(?P<mon>[A-Za-z]{3,9})\.?,?\s+(?:(?P<day>\d{1,2}),?\s+)?(?P<y1>(?:19|20)\d{2}))"
        r"|(?:(?P<y2>(?:19|20)\d{2})-(?P<m2>\d{2})(?:-(?P<d2>\d{2}))?)"
        r"|(?:Q[1-4]\s*'?\s*(?P<yq>(?:19|20)?\d{2})\b)",
        s,
    ):
        if m["y3"]:
            month = MONTHS.get(m["mon3"][:3].lower())
            if month is None:
                continue
            out.append(f"{m['y3']}-{month:02d}-{int(m['dd']):02d}")
        elif m["y1"]:
            month = MONTHS.get(m["mon"][:3].lower())
            if month is None:
                continue
            out.append(f"{m['y1']}-{month:02d}" + (f"-{int(m['day']):02d}" if m["day"] else ""))
        elif m["y2"]:
            out.append(m["y2"] + "-" + m["m2"] + ("-" + m["d2"] if m["d2"] else ""))
        else:
            y = m["yq"]
            out.append(y if len(y) == 4 else "20" + y)
    if not out and "$" not in s:
        # A bare year only; numbers that are prices or part of larger numbers are not dates.
        out = re.findall(r"(?<![\d.,$])\b(?:19|20)\d{2}\b(?![\d.,])", s)
    return list(dict.fromkeys(out))


def parse_clock_mhz(text, header=""):
    """Base clock in MHz; a bare number takes its unit from the column header."""
    text = str(text or "").replace("\xa0", " ")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ghz|mhz)", text, re.I)
    if m:
        unit = m[2].lower()
    else:
        m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", text)
        unit = next((u for u in ("ghz", "mhz") if u in header.lower()), None)
        if not m or unit is None:
            return None
    v = float(m[1])
    return round(v * 1000 if unit == "ghz" else v, 1)


# ---------------------------------------------------------------- fetching


def _get(params, attempts=6):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == attempts - 1:
                raise
            wait = int(exc.headers.get("Retry-After") or 30 * (attempt + 1))
            click.echo(f"rate limited; waiting {wait}s", err=True)
            time.sleep(wait)


def fetch_page(title, cache_dir):
    slug = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")
    meta_path = cache_dir / (slug + ".json")
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    data = _get(dict(action="parse", page=title, prop="text|revid", format="json", redirects=1, formatversion=2))
    if "error" in data:
        raise ValueError(f"{title}: {data['error'].get('info')}")
    html = data["parse"]["text"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    html_path = cache_dir / (slug + ".html")
    html_path.write_text(html)
    meta = dict(
        title=data["parse"]["title"],
        requested_title=title,
        url="https://en.wikipedia.org/wiki/" + urllib.parse.quote(data["parse"]["title"].replace(" ", "_")),
        revision_id=str(data["parse"]["revid"]),
        path=str(html_path),
        sha256=hashlib.sha256(html.encode()).hexdigest(),
        retrieved_on=date.today().isoformat(),
    )
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    time.sleep(5)
    return meta


# ---------------------------------------------------------------- table parsing


def table_grid(table):
    """Expand rowspan/colspan into a rectangular list of cell texts."""
    grid, pending = [], {}
    for tr in table.find_all("tr"):
        row, col = [], 0
        cells = tr.find_all(["th", "td"], recursive=False)
        it = iter(cells)
        while True:
            if col in pending:
                text, left = pending[col]
                row.append(text)
                pending[col] = (text, left - 1)
                if left - 1 == 0:
                    del pending[col]
                col += 1
                continue
            cell = next(it, None)
            if cell is None:
                break
            for sup in cell.find_all("sup", class_="reference"):
                sup.decompose()
            text = cell.get_text(" ", strip=True)
            span = int(re.sub(r"\D", "", cell.get("colspan") or "1") or 1)
            down = int(re.sub(r"\D", "", cell.get("rowspan") or "1") or 1)
            for _ in range(span):
                row.append(text)
                if down > 1:
                    pending[col] = (text, down - 1)
                col += 1
        while col in pending:
            text, left = pending[col]
            row.append(text)
            pending[col] = (text, left - 1)
            if left - 1 == 0:
                del pending[col]
            col += 1
        grid.append((tr, row))
    return grid


def _column(header, *names):
    for i, h in enumerate(header):
        h = h.lower()
        if any(n in h for n in names):
            return i
    return None


def _date_column(header):
    """A release/launch date column; price columns such as 'Release price' never qualify."""
    for i, h in enumerate(header):
        h = h.lower().strip()
        if "price" in h or "msrp" in h:
            continue
        if "date" in h or re.fullmatch(r"released?|launch(?:ed)?|introduced", h):
            return i
    return None


def model_variants(model):
    """'7443 (P)' names two SKUs, 7443 and 7443P; other text is one model."""
    m = re.fullmatch(r"\s*(\S*\d\S*)\s*\(([A-Za-z]{1,3})\)\s*", model)
    return [m[1], m[1] + m[2]] if m else [model]


def table_section(table):
    """Verbatim heading path above a table (h2 › h3 › h4); generation labels are not interpreted."""
    path = []
    for level in ("h2", "h3", "h4"):
        heading = table.find_previous(level)
        if heading is None:
            continue
        # A lower heading belongs to the path only if it follows the higher one.
        if path and path[-1][0].find_all_next(level, limit=1) and heading not in path[-1][0].find_all_next(level):
            continue
        path.append((heading, re.sub(r"\s+", " ", heading.get_text(" ", strip=True).replace("[ edit ]", "")).strip()))
    return " › ".join(text for _, text in path)


def parse_page(meta, family_hint):
    soup = BeautifulSoup(Path(meta["path"]).read_text(), "html.parser")
    rows = []
    for t_index, table in enumerate(soup.find_all("table", class_="wikitable")):
        section = table_section(table)
        grid = table_grid(table)
        header = None
        for r_index, (tr, cells) in enumerate(grid):
            if tr.find("td") is None:
                # Header rows may stack; the last one with a model column defines positions.
                if _column(cells, "model", "sku") is not None and _date_column(cells) is not None:
                    header = cells
                    headers = []
                if header is not None:
                    headers.append(cells)
                continue
            if header is None or len(cells) < len(header) or len(set(cells)) == 1:
                continue
            mi = _column(header, "model", "sku")
            di = _date_column(header)
            fi = _column(header, "frequency", "base clock", "clock rate", "clock", "base")
            if di == mi or (fi is not None and fi in (mi, di)):
                fi = None if fi in (mi, di) else fi
            model = cells[mi]
            prefix = "" if any(f in model.lower() for f in ("xeon", "epyc", "opteron")) else family_hint + " "
            keys = [k for k in dict.fromkeys(sku_key(prefix + m) for m in model_variants(model)) if k]
            dates = parse_dates(cells[di])
            if not keys or not dates:
                continue
            clock = parse_clock_mhz(cells[fi], " ".join(h[fi] for h in headers)) if fi is not None else None
            for key, d in ((k, d) for k in keys for d in dates):
                rows.append(
                    dict(
                        sku_key=key,
                        model_text=model,
                        base_clock_mhz="" if clock is None else clock,
                        release_date=d,
                        release_date_raw=cells[di],
                        source_title=meta["title"],
                        source_url=meta["url"],
                        source_locator=f"wikitable {t_index + 1}, row {r_index + 1}",
                        source_section=section,
                        source_revision=meta["revision_id"],
                        snapshot_sha256=meta["sha256"],
                        reviewed_on=meta["retrieved_on"],
                    )
                )
    return rows


# ---------------------------------------------------------------- command


@click.command("cpu-chronology")
@click.option("--cache-dir", type=click.Path(path_type=Path), default=CACHE, show_default=True)
@click.option("--refresh", is_flag=True, help="Refetch every page even when a cached revision exists.")
def cpu_chronology_command(cache_dir, refresh):
    """Build the Wikipedia CPU SKU release catalog; coverage is reported by `data build`."""
    try:
        if refresh:
            for p in cache_dir.glob("*.json"):
                p.unlink()
        sources, rows = [], []
        for title in PAGES:
            meta = fetch_page(title, cache_dir)
            if hashlib.sha256(Path(meta["path"]).read_bytes()).hexdigest() != meta["sha256"]:
                raise ValueError("cached snapshot changed: " + meta["path"])
            hint = "Opteron" if "Opteron" in title else "EPYC" if title == "Epyc" else "Xeon"
            page_rows = parse_page(meta, hint)
            rows += page_rows
            sources.append(dict(meta, catalog_rows=len(page_rows)))
            click.echo(f"{len(page_rows):5d} rows  {meta['title']} @ {meta['revision_id']}", err=True)
        seen, unique = set(), []
        for r in rows:
            ident = (r["sku_key"], r["release_date"], r["base_clock_mhz"], r["source_url"])
            if ident not in seen:
                seen.add(ident)
                unique.append(r)
        unique.sort(key=lambda r: (r["sku_key"], r["release_date"], r["source_url"], r["source_locator"]))
        CATALOG.parent.mkdir(parents=True, exist_ok=True)
        with open(CATALOG, "w", newline="") as f:
            w = csv.DictWriter(f, FIELDS, lineterminator="\n")
            w.writeheader()
            w.writerows(unique)
        for s in sources:
            s.pop("path")
        SOURCES.write_text(json.dumps(sources, indent=2, ensure_ascii=False) + "\n")
        years = defaultdict(set)
        for r in unique:
            years[r["sku_key"]].add(r["release_date"][:4])
        audit = dict(
            catalog_rows=len(unique),
            sku_keys=len(years),
            sku_keys_with_conflicting_years=sorted(k for k, v in years.items() if len(v) > 1),
            catalog_sha256=hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
        )
        AUDIT.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
        json.dump({k: v for k, v in audit.items() if k != "sku_keys_with_conflicting_years"}, sys.stdout, indent=2)
        click.echo()
    except (OSError, ValueError, KeyError, urllib.error.URLError) as exc:
        raise click.ClickException(str(exc)) from exc


