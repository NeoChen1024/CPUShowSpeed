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

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from cpushowspeed.curated import (
    sha256,
)
from cpushowspeed.curated_system import brand_prefixes, model_id, system_key

RESULTS = Path("data/derived/schema/result-records.jsonl")
LONGBOTTOM_MIPS = Path("data/derived/classic/longbottom-mips-f2019d91d05a.json")
MODEL_YEARS = Path("data/derived/schema/model-years.jsonl")
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
RESULT_TUPLE = ("scope", "vendor", "system", "processor", "clock_mhz", "chips", "cores", "threads_per_core", "memory_mib")
UNCONFIRMED = {"planned", "announced_future", "prospective_or_not_confirmed_as_delivered", "internally_inconsistent"}
CPU_EVENTS = {"release", "market_release", "introduction", "family_introduction"}
# Every event type dates a machine except an option's announcement.
NOT_HARDWARE = {"option_announcement"}


def month(text):
    """'Jul-1999' or '1999-07' -> '1999-07'; anything else -> None."""
    text = (text or "").strip()
    m = re.fullmatch(r"([A-Za-z]{3})-(\d{4})", text)
    if m and m[1].lower() in MONTHS:
        return f"{m[2]}-{MONTHS[m[1].lower()]:02d}"
    return text if re.fullmatch(r"\d{4}-\d{2}", text) else None


def extract_results(inputs):
    """One row per benchmark result: its hardware tuple and the dates it reports."""
    results = {}
    for line in inputs.read_text().splitlines():
        o = json.loads(line)
        rid = o["result_id"]
        hw = o.get("hardware") or {}
        raw = o.get("raw") or {}
        f = raw.get("fields") or raw
        if rid not in results:
            year = str(f.get("introduction_year_raw") or "").strip()
            results[rid] = dict(
                result_id=rid,
                scope=o["scope"],
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
    """Write result_chronology: candidates of every kind, the selected year and the result's own
    reported dates after reviewed rejections."""
    from cpushowspeed.curated_review import rejected_dates

    if not RESULTS.exists():
        return {"chronology": "skipped: run `cpushowspeed data extract`"}
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
    # Reviewed rejections remove a reported date from every use; it stays in the candidates as rejected.
    rejected = defaultdict(list)
    for (rid, field), review_id in rejected_dates(db).items():
        rejected[rid].append((field, review_id))
    for r in results:
        r["rejected"] = [
            dict(kind="rejected_" + f, date=r[f], review_id=rev) for f, rev in rejected.get(r["result_id"], []) if r[f]
        ]
        for f, _ in rejected.get(r["result_id"], []):
            r[f] = None
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
    # Reviewed exact-text aliases name the system of a catalogue spelling ("DECSTN 5000/200").
    aliases = {a["text"]: a for a in tables["alias"] if a["entity_kind"] == "system_model" and a["status"] != "candidate"}
    if MODEL_YEARS.exists():
        for m in (json.loads(line) for line in MODEL_YEARS.read_text().splitlines()):
            alias = aliases.get(m["system"])
            if alias:
                system_id = alias["entity_id"] if alias["status"] == "accepted" else None
            else:
                _, key, _, _ = system_key(m["system"], "", brands)
                system_id = model_id(key) if key else None
            if system_id:
                model_dates[system_id].append(dict(kind="hardware_model_catalogue", date=m["year"], locator=m["locator"]))

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
        "processor_entity TEXT, date_kind TEXT, year INTEGER, year_low INTEGER, year_high INTEGER, basis TEXT, candidates TEXT, "
        "hardware_availability TEXT, test TEXT, publication TEXT, table_year TEXT)"
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
            "INSERT INTO result_chronology VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                json.dumps(cpu + [c for t in tiers for c in t] + fallback + submission + r["rejected"]),
                r["hardware_availability"],
                r["test"],
                r["publication"],
                r["table_year"],
            ),
        )
    findings = consistency_findings(db, by_subject)
    meta = {"result_records_sha256": sha256(RESULTS)}
    meta.update({f"consistency:{k}": str(v) for k, v in sorted(findings.items())})
    meta.update({f"chronology:observations:{k}": str(v) for k, v in sorted(kinds.items())})
    meta.update({f"chronology:basis:{k}": str(v) for k, v in sorted(bases.items())})
    return meta
