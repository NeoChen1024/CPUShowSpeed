"""Dates (schema step 3): date events, extracted result dates and chronology selection.

Chronology for one result: CPU release of its processor entity (the SKU, else its
family), then hardware, then reviewed fallback proxies, then result publication as
a submission-era proxy. The hardware kind takes the first non-empty tier: (a) a
date the configuration itself reports (SPEC hardware availability); (b) primary
curated events of its system model; (c) the result's own compilation table year;
(d) model-level dates reported elsewhere for the same system model (compilation
and catalogue years, SPEC hardware availability of other configurations).
Fallback proxies (processor or system families) only fill gaps. Within the chosen kind, conflicting years give the range and the
integer midpoint of distinct years; announced, planned or inconsistent claims and
excluded events never select a year.
"""

import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import click
from cpushowspeed.curated import CURATED, DATABASE, read_table, sha256, validate, write_jsonl
from cpushowspeed.curated_identity import CATALOG, slug
from cpushowspeed.curated_sources import norm_url
from cpushowspeed.curated_system import brand_prefixes, model_id, system_key

RESULTS = Path("data/derived/schema/result-records.jsonl")
PROXIES = Path("research/data/historical/cpu-release-proxies.csv")
EVIDENCE = Path("research/data/historical/hardware-date-evidence.csv")
OVERRIDES = Path("research/data/historical/timeline-year-overrides.csv")
SPEC89_INTRODUCTIONS = Path("research/data/spec89/hardware-introductions.csv")
LONGBOTTOM_MIPS = Path("data/derived/classic/longbottom-mips-f2019d91d05a.json")
MODEL_YEARS = Path("data/derived/schema/model-years.jsonl")
# SPEC89 introduction rows that date the processor, not the machine.
PROCESSOR_PROXIES = {"processor_introduction", "processor_family_introduction"}
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
RESULT_TUPLE = ("scope", "vendor", "system", "processor", "clock_mhz", "chips", "cores", "threads_per_core", "memory_mib")
UNCONFIRMED = {"planned", "announced_future", "prospective_or_not_confirmed_as_delivered", "internally_inconsistent"}
CPU_EVENTS = {"release", "market_release", "introduction", "family_introduction"}
# Every event type dates a machine except an option's announcement.
NOT_HARDWARE = {"option_announcement"}

# Reviewed CPU interpretations of the former configuration proxies, at the granularity they state.
X86 = {
    "fam:x86-486dx": ("Intel and compatibles", "486DX"),
    "fam:x86-486dx2": ("Intel and compatibles", "486DX2"),
    "fam:intel-486dx4": ("Intel", "486DX4 (IntelDX4)"),
    "fam:intel-pentium-p5": ("Intel", "Pentium (P5/P54C)"),
    "fam:intel-celeron": ("Intel", "Celeron"),
    "fam:intel-xeon-nocona": ("Intel", "Xeon (Nocona)"),
    "fam:intel-xeon-woodcrest": ("Intel", "Xeon (Woodcrest)"),
    "fam:amd-am386": ("AMD", "Am386"),
    "fam:amd-am486": ("AMD", "Am486"),
    "fam:amd-am5x86": ("AMD", "Am5x86"),
    "fam:amd-k6-2": ("AMD", "K6-2"),
    "fam:amd-athlon-thunderbird": ("AMD", "Athlon (Thunderbird)"),
    "fam:amd-athlon-xp": ("AMD", "Athlon XP"),
    "fam:amd-athlon-mp": ("AMD", "Athlon MP"),
    "fam:amd-duron": ("AMD", "Duron"),
    "fam:cyrix-5x86": ("Cyrix", "5x86"),
}
INTERPRETATION = {  # interpretation -> (entity id, family id for SKUs, model name, base clock)
    "Intel-compatible 486DX-33": ("sku:x86-486dx-33", "fam:x86-486dx", "486DX-33", 33.0),
    "Intel-compatible 486DX-50": ("sku:x86-486dx-50", "fam:x86-486dx", "486DX-50", 50.0),
    "Intel-compatible 486DX2": ("fam:x86-486dx2", None, None, None),
    "Intel-compatible 486DX2-66": ("sku:x86-486dx2-66", "fam:x86-486dx2", "486DX2-66", 66.0),
    "Intel DX4": ("fam:intel-486dx4", None, None, None),
    "Intel Pentium 60 MHz": ("sku:intel-pentium-60", "fam:intel-pentium-p5", "Pentium 60", 60.0),
    "Intel Pentium 66 MHz": ("sku:intel-pentium-66", "fam:intel-pentium-p5", "Pentium 66", 66.0),
    "Intel Pentium 66": ("sku:intel-pentium-66", "fam:intel-pentium-p5", "Pentium 66", 66.0),
    "Intel Pentium 75 MHz": ("sku:intel-pentium-75", "fam:intel-pentium-p5", "Pentium 75", 75.0),
    "Intel Pentium 90 MHz": ("sku:intel-pentium-90", "fam:intel-pentium-p5", "Pentium 90", 90.0),
    "Intel Pentium 100 MHz": ("sku:intel-pentium-100", "fam:intel-pentium-p5", "Pentium 100", 100.0),
    "Intel Pentium 120 MHz": ("sku:intel-pentium-120", "fam:intel-pentium-p5", "Pentium 120", 120.0),
    "Intel Pentium 133 MHz": ("sku:intel-pentium-133", "fam:intel-pentium-p5", "Pentium 133", 133.0),
    "Intel Pentium 166 MHz": ("sku:intel-pentium-166", "fam:intel-pentium-p5", "Pentium 166", 166.0),
    "Intel Pentium Pro": ("fam:intel-pentium-pro", None, None, None),
    "Intel Pentium III 600": ("sku:intel-pentium-iii-600", "fam:intel-pentium-iii", "Pentium III 600", 600.0),
    "Intel Pentium III-S 1266": ("sku:intel-pentium-iii-s-1266", "fam:intel-pentium-iii", "Pentium III-S 1266", 1266.0),
    "Intel Celeron 433": ("sku:intel-celeron-433", "fam:intel-celeron", "Celeron 433", 433.0),
    "Intel Xeon Nocona": ("fam:intel-xeon-nocona", None, None, None),
    "Intel Xeon Woodcrest": ("fam:intel-xeon-woodcrest", None, None, None),
    "AMD Am386": ("fam:amd-am386", None, None, None),
    "AMD Am486 DX2-80": ("sku:amd-am486dx2-80", "fam:amd-am486", "Am486 DX2-80", 80.0),
    "AMD Am486 DX4-100": ("sku:amd-am486dx4-100", "fam:amd-am486", "Am486 DX4-100", 100.0),
    "AMD Am5x86": ("fam:amd-am5x86", None, None, None),
    "AMD K6-2 350": ("sku:amd-k6-2-350", "fam:amd-k6-2", "K6-2 350", 350.0),
    "AMD K6-2 500": ("sku:amd-k6-2-500", "fam:amd-k6-2", "K6-2 500", 500.0),
    "AMD Athlon Thunderbird 1200": ("sku:amd-athlon-1200", "fam:amd-athlon-thunderbird", "Athlon 1200", 1200.0),
    "AMD Athlon Thunderbird 1400": ("sku:amd-athlon-1400", "fam:amd-athlon-thunderbird", "Athlon 1400", 1400.0),
    "AMD Athlon XP 1800+": ("sku:amd-athlon-xp-1800+", "fam:amd-athlon-xp", "Athlon XP 1800+", 1533.0),
    "AMD Athlon MP 1800+": ("sku:amd-athlon-mp-1800+", "fam:amd-athlon-mp", "Athlon MP 1800+", 1533.0),
    "AMD Duron 900": ("sku:amd-duron-900", "fam:amd-duron", "Duron 900", 900.0),
    "AMD Opteron 240": ("sku:amd-opteron-240", None, None, None),
    "AMD Opteron 242": ("sku:amd-opteron-242", None, None, None),
    "AMD Opteron 275": ("sku:amd-opteron-275", None, None, None),
    "Cyrix 5x86": ("fam:cyrix-5x86", None, None, None),
}
# Former processor-family year overrides: a fragment of the override's regex text chooses the family.
FAMILY_OVERRIDES = [
    ("Pentium\\s+(?:III|3)", "fam:intel-pentium-iii"),
    ("Pentium\\s+(?:II|2)", "fam:intel-pentium-ii"),
    ("Pentium\\s+Pro", "fam:intel-pentium-pro"),
    ("Pentium\\s*4|P4", "fam:intel-pentium-4"),
]


def precision_of(value):
    if re.fullmatch(r"\d{4}", value):
        return "year"
    if re.fullmatch(r"\d{4}-Q[1-4]", value):
        return "quarter"
    return "month" if re.fullmatch(r"\d{4}-\d{2}", value) else "day"


def period_end(value):
    """Last day a partially known date can denote, for 'not yet happened' tests."""
    y = int(value[:4])
    if len(value) == 4:
        return date(y, 12, 31)
    if value[5] == "Q":
        m = int(value[6]) * 3
    else:
        m = int(value[5:7])
        if len(value) == 10:
            return date(y, m, int(value[8:10]))
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return date.fromordinal(nxt.toordinal() - 1)


def short_hash(*parts):
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8]


def source_finder(sources):
    by_legacy = {legacy: s["source_id"] for s in sources for legacy in s["legacy_ids"]}
    by_url = {}
    for s in sources:
        for u in [s.get("url"), s.get("final_url"), *s.get("alternate_urls", [])]:
            if u:
                by_url.setdefault(norm_url(u), s["source_id"])
    return by_legacy, by_url


def new_source(url, legacy, today, revision=None, snapshot=None):
    host = urlsplit(url).netloc.lower()
    wiki = "wikipedia.org" in host
    row = dict(
        source_id="src:web/"
        + re.sub(r"[^a-z0-9._/@+-]+", "-", (host.removeprefix("www.") + urlsplit(url).path).lower()).strip("-/")[:80]
        + "@"
        + short_hash(url),
        kind="wiki_revision" if wiki else "web_page",
        url=url,
    )
    if revision:
        row["revision"] = revision
    if snapshot:
        row.update(hash_algo="sha256", hash=snapshot)
    row.update(
        provenance_class=(
            "modern_secondary" if wiki else "vendor" if host.endswith("intel.com") or host.endswith("amd.com") else "unclassified"
        ),
        acquisition_status="not_acquired",
        reviews=[],
        legacy_ids=[legacy],
    )
    return row


def seed_dates(tables, db):
    """Convert the SKU catalogue, CPU proxies, hardware date evidence and year overrides."""
    today = date.today().isoformat()
    sources = list(tables["source"])
    by_legacy, by_url = source_finder(sources)
    families = {f["family_id"]: f for f in tables["processor_family"]}
    skus = {s["sku_id"]: s for s in tables["processor_sku"]}
    aliases = {a["alias_id"]: a for a in tables["alias"]}
    systems = {m["system_id"]: m for m in tables["system_model"]}
    events, report = [], defaultdict(list)

    def source_for(url, legacy, **extra):
        sid = by_url.get(norm_url(url))
        if sid:
            row = next(s for s in sources if s["source_id"] == sid)
            if legacy not in row["legacy_ids"]:
                row["legacy_ids"] = sorted(row["legacy_ids"] + [legacy])
            return sid
        row = new_source(url, legacy, today, **extra)
        sources.append(row)
        by_url[norm_url(url)] = row["source_id"]
        return row["source_id"]

    # 1. SKU catalogue: parsed release dates.
    with CATALOG.open(newline="") as f:
        for r in csv.DictReader(f):
            q = re.search(r"Q([1-4])\s*'?\s*((?:19|20)?\d{2})", r["release_date_raw"])
            value = f"{r['release_date'][:4]}-Q{q[1]}" if q and len(r["release_date"]) == 4 else r["release_date"]
            future = period_end(value) >= date.fromisoformat(r["reviewed_on"])
            locator = r["source_locator"] + (f" › {r['source_section']}" if r["source_section"] else "")
            events.append(
                dict(
                    event_id=f"evt:sku/{slug(r['sku_key'])}/{short_hash(locator, value)}",
                    subject_kind="processor_sku",
                    subject_id="sku:" + slug(r["sku_key"]),
                    event_type="release",
                    date=value,
                    date_precision=precision_of(value),
                    date_raw=r["release_date_raw"],
                    claim_status="announced_future" if future else "reported",
                    chronology="excluded" if future else "primary",
                    source_id=by_legacy[f"historical/cpu-sku-sources:{r['source_title']}@{r['source_revision']}"],
                    locator=locator,
                    verification="parsed_unreviewed",
                    reviewed_on=r["reviewed_on"],
                    legacy_ids=[f"historical/cpu-sku-chronology:{r['sku_key']}@{r['source_locator']}"],
                )
            )

    # 2. CPU release proxies: entities at the stated granularity, release events, and aliases.
    proxy_events = {}
    with PROXIES.open(newline="") as f:
        for r in csv.DictReader(f):
            entity, family, model, clock = INTERPRETATION[r["cpu_interpretation"]]
            kind = "processor_sku" if entity.startswith("sku:") else "processor_family"
            for fid in [f for f in (family, entity if kind == "processor_family" else None) if f]:
                if fid not in families:
                    vendor, name = X86[fid]
                    families[fid] = dict(
                        family_id=fid, vendor=vendor, name=name, note=f"Added {today} from reviewed CPU interpretations."
                    )
            legacy = f"historical/cpu-release-proxies:{r['configuration_id']}"
            sid = source_for(
                r["source_url"], legacy, revision=r.get("source_revision") or None, snapshot=r.get("snapshot_sha256") or None
            )
            if kind == "processor_sku" and entity not in skus:
                skus[entity] = dict(
                    sku_id=entity,
                    family_id=family,
                    vendor=families[family]["vendor"],
                    model=model,
                    keys=["reviewed:" + r["cpu_interpretation"]],
                    base_clocks_mhz=[clock],
                    source_ids=[sid],
                )
            elif kind == "processor_sku" and sid not in skus[entity]["source_ids"]:
                skus[entity]["source_ids"] = sorted(skus[entity]["source_ids"] + [sid])
            value = r["release_date"]
            key = (entity, value, sid)
            if key not in proxy_events:
                proxy_events[key] = dict(
                    event_id=f"evt:cpu/{entity.split(':')[1]}/{short_hash(value, sid)}",
                    subject_kind=kind,
                    subject_id=entity,
                    event_type="release",
                    date=value,
                    date_precision=precision_of(value),
                    claim_status="reported",
                    chronology="primary",
                    source_id=sid,
                    locator=r["source_locator"],
                    verification="web_text_checked",
                    reviewed_on=r["reviewed_on"],
                    legacy_ids=[],
                )
                if r["notes"]:
                    proxy_events[key]["note"] = r["notes"]
            proxy_events[key]["legacy_ids"].append(legacy)
            clock_value = float(r["clock_mhz"]) if r["clock_mhz"] else None
            text, scope = (r["cpu"], "processor") if r["cpu"] else (r["system"], "processor-from-system")
            aid = f"alias:{scope}/{slug(text)}.{short_hash(text, clock_value)[:6]}"
            alias = dict(alias_id=aid, entity_kind=kind, entity_id=entity, match_kind="exact_text", text=text, scope=scope)
            if clock_value:
                alias["constraints"] = dict(clock_mhz=clock_value)
            alias.update(
                status="accepted",
                reviewed_on=r["reviewed_on"],
                source_id=sid,
                note="Reviewed CPU interpretation: " + r["cpu_interpretation"],
            )
            if aid in aliases and aliases[aid]["entity_id"] != entity:
                report["alias_conflicts"].append([text, clock_value, aliases[aid]["entity_id"], entity])
            aliases[aid] = alias
    for e in proxy_events.values():
        e["legacy_ids"] = sorted(set(e["legacy_ids"]))
        events.append(e)

    # 3. Hardware date evidence: events on the system model its machine name keys to.
    brands = brand_prefixes(tables)
    with EVIDENCE.open(newline="") as f:
        for r in csv.DictReader(f):
            name, key, _, _ = system_key(r["machine"], "", brands)
            if not key:
                report["evidence_without_model"].append(r["id"])
                continue
            sys_id = model_id(key)
            systems.setdefault(
                sys_id, dict(system_id=sys_id, name=r["machine"], note=f"Machine with curated date evidence; added {today}.")
            )
            value = f"{r['date'][:4]}-Q{r['quarter']}" if r["date_precision"] == "quarter" and r["quarter"] else r["date"]
            locator = "; ".join(
                x
                for x in [
                    f"PDF page {r['pdf_page']}" if r["pdf_page"] else "",
                    f"printed {r['printed_page']}" if r["printed_page"] else "",
                    r["source_locator"],
                ]
                if x
            )
            e = dict(
                event_id="evt:hw/" + r["id"].removeprefix("hardware-date-"),
                subject_kind="system_model",
                subject_id=sys_id,
                event_type=r["event_type"],
                date=value,
                date_precision=precision_of(value),
            )
            if r["date_raw"]:
                e["date_raw"] = r["date_raw"]
            e.update(
                claim_status=r["event_status"],
                chronology="primary" if r["use_for_timeline"] == "true" else "excluded",
                source_id=by_legacy[f"historical/hardware-date-evidence:{r['id']}"],
            )
            if locator:
                e["locator"] = locator
            e.update(verification=r["verification"], reviewed_on=r["reviewed_on"])
            if r["notes"]:
                e["note"] = r["notes"]
            e["legacy_ids"] = [f"historical/hardware-date-evidence:{r['id']}"]
            events.append(e)

    # 3b. SPEC89 machine introductions (curated; only rows with a date).
    with SPEC89_INTRODUCTIONS.open(newline="") as f:
        for n, r in enumerate(csv.DictReader(f), 1):
            value = r["hardware_introduced_at"] or r["hardware_introduction_year"]
            if not value:
                continue
            name, key, _, _ = system_key(r["system_normalized"], "", brands)
            if not key:
                report["spec89_without_model"].append(r["system_normalized"])
                continue
            sys_id = model_id(key)
            systems.setdefault(
                sys_id,
                dict(
                    system_id=sys_id, name=r["system_normalized"], note=f"SPEC89 machine with a dated introduction; added {today}."
                ),
            )
            legacy = f"spec89/hardware-introductions:{r['system_normalized']}"
            e = dict(
                event_id=f"evt:spec89/{slug(key)}/{short_hash(value, r['event_type'])}",
                subject_kind="system_model",
                subject_id=sys_id,
                event_type=r["event_type"],
                date=value,
                date_precision=precision_of(value),
                claim_status="inferred_proxy" if r["event_type"] in PROCESSOR_PROXIES else "reported",
                chronology="primary",
                source_id=source_for(r["source_url"], legacy),
            )
            if r["source_locator"]:
                e["locator"] = r["source_locator"]
            e.update(verification="web_text_checked", reviewed_on=r["reviewed_on"])
            if r["notes"]:
                e["note"] = r["notes"]
            e["legacy_ids"] = [legacy]
            events.append(e)

    # 4. Year overrides: proxies on the models (or processor families) their regex selected.
    texts = defaultdict(set)
    for system, sys_id in db.execute("SELECT DISTINCT system, system_id FROM hardware_record WHERE system_id IS NOT NULL"):
        texts[sys_id].add(system)
    with OVERRIDES.open(newline="") as f:
        for n, r in enumerate(csv.DictReader(f), 1):
            legacy = f"historical/timeline-year-overrides:{r['system_regex']}"
            if not r["year"]:
                report["overrides_pending_review"].append(r["system_regex"])
                continue
            sid = source_for(r["source_url"], legacy)
            family = next((fid for fragment, fid in FAMILY_OVERRIDES if fragment in r["system_regex"]), None)
            subjects = (
                [("processor_family", family)]
                if family
                else [
                    ("system_model", s) for s, ts in sorted(texts.items()) if any(re.search(r["system_regex"], t, re.I) for t in ts)
                ]
            )
            if not subjects:
                report["overrides_without_subject"].append(r["system_regex"])
            for kind, subject in subjects:
                if kind == "system_model":
                    systems.setdefault(
                        subject,
                        dict(
                            system_id=subject,
                            name=sorted(texts[subject])[0],
                            note=f"Model with a reviewed year proxy; added {today}.",
                        ),
                    )
                events.append(
                    dict(
                        event_id=f"evt:override/{n}/{slug(subject.split(':')[1])}",
                        subject_kind=kind,
                        subject_id=subject,
                        event_type="family_introduction" if "family" in r["method"] else "introduction",
                        date=r["year"],
                        date_precision="year",
                        claim_status="inferred_proxy",
                        chronology="fallback" if r["fallback"] == "true" else "primary",
                        source_id=sid,
                        verification="reviewed_proxy",
                        reviewed_on=r["reviewed_on"],
                        note=f"{r['method']}: {r['notes']} Selected by regex {r['system_regex']!r}.",
                        legacy_ids=[legacy],
                    )
                )
    return (
        dict(
            source=sorted(sources, key=lambda s: s["source_id"]),
            processor_family=sorted(families.values(), key=lambda f: f["family_id"]),
            processor_sku=sorted(skus.values(), key=lambda s: s["sku_id"]),
            alias=sorted(aliases.values(), key=lambda a: a["alias_id"]),
            system_model=sorted(systems.values(), key=lambda m: m["system_id"]),
            date_event=sorted(events, key=lambda e: e["event_id"]),
        ),
        report,
    )


@click.command("import-dates")
@click.option("--root", type=click.Path(path_type=Path, file_okay=False), default=CURATED, show_default=True)
@click.option("--force", is_flag=True, help="Overwrite an existing date_event table, discarding curated edits.")
def import_dates_command(root, force):
    """One-time migration: date events from the SKU catalogue, CPU proxies, date evidence and year overrides."""
    if (root / "date_event.jsonl").exists() and not force:
        raise click.ClickException("date_event.jsonl exists and is curated data; pass --force to rebuild it")
    if not DATABASE.exists():
        raise click.ClickException("run `cpushowspeed data build` first; overrides are matched against built system models")
    names = ["source", "processor_family", "processor_sku", "alias", "system_model", "vendor"]
    tables = {n: read_table(root, dict(file=n + ".jsonl")) for n in names}
    with closing(sqlite3.connect(DATABASE)) as db:
        out, report = seed_dates(tables, db)
    for name, rows in out.items():
        write_jsonl(root / f"{name}.jsonl", rows)
    _, tables, errors, _ = validate(root)
    for e in errors:
        click.echo(e, err=True)
    json.dump(dict(tables={k: len(v) for k, v in tables.items()}, report=report, errors=len(errors)), sys.stdout, indent=2)
    click.echo()
    if errors:
        sys.exit(1)


def month(text):
    """'Jul-1999' or '1999-07' -> '1999-07'; anything else -> None."""
    text = (text or "").strip()
    m = re.fullmatch(r"([A-Za-z]{3})-(\d{4})", text)
    if m and m[1].lower() in MONTHS:
        return f"{m[2]}-{MONTHS[m[1].lower()]:02d}"
    return text if re.fullmatch(r"\d{4}-\d{2}", text) else None


def extract_results(inputs):
    """One row per benchmark result: its hardware tuple and the dates it reports."""
    from cpushowspeed.curated_system import scope_of

    results = {}
    for line in inputs.read_text().splitlines():
        o = json.loads(line)
        rid = (
            re.sub(r":(?:base|peak)$", "", o["source_record_id"])
            if o["source_record_id"].startswith("spec:")
            else o["source_record_id"]
        )
        hw = o.get("hardware") or {}
        raw = o.get("raw") or {}
        f = raw.get("fields") or raw
        if rid not in results:
            year = str(f.get("introduction_year_raw") or "").strip()
            results[rid] = dict(
                result_id=rid,
                scope=scope_of(o["source_record_id"]),
                vendor=(f.get("Hardware Vendor") or f.get("Company") or f.get("company") or "").strip(),
                system=" ".join((o.get("system") or "").split()),
                processor=" ".join((hw.get("processor") or "").split()),
                clock_mhz=hw.get("nominal_mhz"),
                chips=hw.get("enabled_chips"),
                cores=hw.get("enabled_cores"),
                threads_per_core=hw.get("hardware_threads_per_core"),
                memory_mib=hw.get("memory_mib"),
                hardware_availability=month(f.get("HW Avail") or f.get("hardware_availability_month")),
                publication=month(f.get("Published") or f.get("publication_month")),
                test=month(f.get("Test Date") or f.get("test_month")),
                table_year=year if re.fullmatch(r"(?:19|20)\d{2}", year) else None,
                observations=0,
            )
        results[rid]["observations"] += 1
    return [results[k] for k in sorted(results)]


def extract_model_years():
    """Longbottom's MIPS catalogue years: compilation dates for named machines (model level)."""
    from cpushowspeed.classic_overlap import full_name

    if not LONGBOTTOM_MIPS.exists():
        return []
    page = json.loads(LONGBOTTOM_MIPS.read_text())
    rows = []
    for block in page["blocks"]:
        if block.get("kind") != "preformatted":
            continue
        vendor = ""
        for line_number, line in enumerate(block["text"].splitlines(), 1):
            if not line.strip() or line.strip() == "To Index" or line.startswith(("Manufacturer", "Processor")):
                continue
            name, tail = line[:19].strip(), line[19:]
            if name and (not tail.strip() or tail.strip().startswith("OS ")):
                vendor = name
                continue
            year = line[61:67].strip()
            if name and re.fullmatch(r"(?:19|20)\d{2}", year):
                rows.append(
                    dict(
                        system=full_name(vendor, name),
                        year=year,
                        source_id="src:longbottom-mips",
                        locator=f"pre:{block.get('pre_index')}:line:{line_number}",
                    )
                )
    return rows


def consistency_findings(db, by_subject):
    """Report, never resolve: contradictions between sources stay visible for review."""
    db.execute("CREATE TABLE consistency_finding (finding TEXT, subject TEXT, detail TEXT)")
    counts = Counter()
    for rid, cands in db.execute("SELECT result_id, candidates FROM result_chronology WHERE date_kind = 'cpu'"):
        cands = json.loads(cands)
        cpu = min(int(c["date"][:4]) for c in cands if c["kind"] == "cpu")
        reported = [int(c["date"][:4]) for c in cands if c["kind"] == "hardware_reported"]
        if reported and cpu > max(reported):
            db.execute(
                "INSERT INTO consistency_finding VALUES (?, ?, ?)",
                ("cpu_release_after_hardware_availability", rid, f"cpu {cpu} > hardware {max(reported)}"),
            )
            counts["cpu_release_after_hardware_availability"] += 1
    for subject, events in by_subject.items():
        years = sorted({int(e["date"][:4]) for e in events if e["chronology"] == "primary"})
        if len(years) > 1 and years[-1] - years[0] > 1:
            db.execute(
                "INSERT INTO consistency_finding VALUES (?, ?, ?)", ("event_years_more_than_one_apart", subject, json.dumps(years))
            )
            counts["event_years_more_than_one_apart"] += 1
    return counts


def select(candidates):
    years = sorted({int(c["date"][:4]) for c in candidates})
    return (years[(len(years) - 1) // 2] + years[len(years) // 2]) // 2, years[0], years[-1]


def build_chronology(db, tables):
    """Write result_chronology: candidates of every kind and the selected year."""
    if not RESULTS.exists():
        return {"chronology": "skipped: run `cpushowspeed data extract-mentions`"}
    usable = [e for e in tables["date_event"] if e["chronology"] != "excluded" and e["claim_status"] not in UNCONFIRMED]
    by_subject = defaultdict(list)
    for e in usable:
        by_subject[e["subject_id"]].append(e)
    family_of = {s["sku_id"]: s["family_id"] for s in tables["processor_sku"]}
    hw = {}
    cols = "scope, vendor, system, processor, clock_mhz, chips, cores, threads_per_core, memory_mib"
    for row in db.execute(f"SELECT {cols}, hardware_id, system_id, processor_entity FROM hardware_record"):
        hw[tuple(row[:9])] = row[9:]
    results = [json.loads(line) for line in RESULTS.read_text().splitlines()]
    # Model-level dates reported elsewhere for the same system model: compilation table and
    # catalogue years, and SPEC hardware availability of other configurations of that model.
    model_dates = defaultdict(list)
    for r in results:
        _, sys_id, _ = hw.get(tuple(r[k] for k in RESULT_TUPLE), (None, None, None))
        if sys_id and r["table_year"]:
            model_dates[sys_id].append(dict(kind="hardware_model_compilation", date=r["table_year"], result_id=r["result_id"]))
        if sys_id and r["hardware_availability"]:
            model_dates[sys_id].append(dict(kind="hardware_model_spec", date=r["hardware_availability"], result_id=r["result_id"]))
    brands = brand_prefixes(tables)
    if MODEL_YEARS.exists():
        for m in (json.loads(line) for line in MODEL_YEARS.read_text().splitlines()):
            _, key, _, _ = system_key(m["system"], "", brands)
            if key:
                model_dates[model_id(key)].append(dict(kind="hardware_model_catalogue", date=m["year"], locator=m["locator"]))

    def model_level(system_id, r):
        if not system_id:
            return []
        found = [d for d in model_dates.get(system_id, []) if d.get("result_id") != r["result_id"]]
        if not found and r["clock_mhz"]:
            # Catalogues list clock variants ("HP 9000/715/50"); match this record's clock.
            found = model_dates.get(f"{system_id}/{r['clock_mhz']:g}", [])
        return found

    db.execute(
        "CREATE TABLE result_chronology (result_id TEXT PRIMARY KEY, scope TEXT, hardware_id TEXT, system_id TEXT, "
        "processor_entity TEXT, date_kind TEXT, year INTEGER, year_low INTEGER, year_high INTEGER, basis TEXT, candidates TEXT)"
    )
    kinds, bases = Counter(), Counter()
    for r in results:
        key = tuple(r[k] for k in RESULT_TUPLE)
        hardware_id, system_id, entity = hw.get(key, (None, None, None))

        def events(subject, kinds_, tier):
            return [
                dict(kind=tier, date=e["date"], event_id=e["event_id"])
                for e in by_subject.get(subject, [])
                if (e["event_type"] not in NOT_HARDWARE if kinds_ is None else e["event_type"] in kinds_)
                and e["chronology"] == ("fallback" if tier.endswith("fallback") else "primary")
            ]

        cpu = cpu_fallback = []
        if entity:
            cpu = events(entity, CPU_EVENTS, "cpu") or events(family_of.get(entity), CPU_EVENTS, "cpu")
            cpu_fallback = events(entity, CPU_EVENTS, "cpu_fallback") or events(family_of.get(entity), CPU_EVENTS, "cpu_fallback")
        tiers = [
            [dict(kind="hardware_reported", date=r["hardware_availability"])] if r["hardware_availability"] else [],
            events(system_id, None, "hardware_model") if system_id else [],
            [dict(kind="hardware_table_year", date=r["table_year"])] if r["table_year"] else [],
            model_level(system_id, r),
        ]
        # Reviewed family proxies only fill gaps: below every reported or evidenced date.
        fallback = cpu_fallback + (events(system_id, None, "hardware_fallback") if system_id else [])
        hardware = next((t for t in tiers if t), [])
        submission = [dict(kind="publication", date=r["publication"])] if r["publication"] else []
        order = (("cpu", cpu), ("hardware", hardware), ("fallback", fallback), ("submission", submission))
        chosen = next(((k, c) for k, c in order if c), (None, []))
        year = low = high = None
        if chosen[1]:
            year, low, high = select(chosen[1])
        basis = chosen[1][0]["kind"] if chosen[1] else None
        kinds[chosen[0] or "unknown"] += r["observations"]
        bases[basis or "unknown"] += r["observations"]
        db.execute(
            "INSERT INTO result_chronology VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r["result_id"],
                r["scope"],
                hardware_id,
                system_id,
                entity,
                chosen[0] or "unknown",
                year,
                low,
                high,
                basis,
                json.dumps(cpu + [c for t in tiers for c in t] + fallback + submission),
            ),
        )
    findings = consistency_findings(db, by_subject)
    meta = {"result_records_sha256": sha256(RESULTS)}
    meta.update({f"consistency:{k}": str(v) for k, v in sorted(findings.items())})
    meta.update({f"chronology:observations:{k}": str(v) for k, v in sorted(kinds.items())})
    meta.update({f"chronology:basis:{k}": str(v) for k, v in sorted(bases.items())})
    return meta
