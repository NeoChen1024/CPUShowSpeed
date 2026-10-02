"""System identity (schema step 2b): vendors, system models and hardware configurations.

A hardware record is one distinct (scope, vendor text, system text, processor text,
clock, chips, cores, threads/core, memory) tuple from the input catalogue. Build:
1. vendor text -> vendor by accepted exact-text alias;
2. processor text -> processor entity; when that fails, the system text is tried
   and the result is marked as read from the system name;
3. system text -> curated system model by exact alias, else, for SPEC records with
   a resolved vendor, the rule spec-system-v1 derives a model key;
4. a hardware configuration is the tuple of system model, processor entity,
   nominal clock, chips, cores, threads/core and memory; equal tuples share one ID.
"""

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import click
from cpushowspeed.curated import CURATED, read_table, sha256, validate, write_jsonl
from cpushowspeed.curated_identity import Resolver

RECORDS = Path("data/derived/schema/hardware-records.jsonl")
SUFFIX = r"\b(?:inc|incorporated|corp|corporation|corportation|co|ltd|limited|llc|gmbh|ag|s ?a|sas|plc|company|computers?|kk)\b"
# Brand words that SPEC system names repeat before the model; curated per vendor after seeding.
PREFIXES = {
    "org:dell": ["dell"],
    "org:hewlett-packard": ["hewlett-packard", "hewlett packard", "hp"],
    "org:hewlett-packard-enterprise": ["hewlett packard enterprise", "hpe", "hp"],
    "org:lenovo-global-technology": ["lenovo"],
    "org:lenovo-group": ["lenovo"],
    "org:huawei": ["huawei"],
    "org:xfusion": ["xfusion"],
    "org:fujitsu": ["fujitsu"],
    "org:fujitsu-siemens": ["fujitsu siemens", "fujitsu"],
    "org:ibm": ["ibm"],
    "org:supermicro": ["supermicro", "super micro"],
    "org:cisco-systems": ["cisco"],
    "org:nec": ["nec"],
    "org:asustek": ["asus"],
    "org:asus-international": ["asus"],
    "org:acer": ["acer"],
    "org:intel": ["intel"],
    "org:sun-microsystems": ["sun microsystems", "sun"],
    "org:oracle": ["oracle", "sun"],
    "org:inspur": ["inspur"],
    "org:new-h3c-technologies": ["h3c"],
    "org:h3c": ["h3c"],
    "org:tyrone-systems": ["tyrone"],
    "org:sugon": ["sugon"],
    "org:nettrix": ["nettrix"],
    "org:gigabyte-technology": ["gigabyte", "giga-byte"],
    "org:compaq": ["compaq"],
    "org:digital-equipment": ["digital", "dec"],
    "org:sgi": ["sgi"],
    "org:silicon-graphics": ["sgi", "silicon graphics"],
    "org:bull": ["bull"],
    "org:hitachi": ["hitachi"],
    "org:unisys": ["unisys"],
    "org:zte": ["zte"],
    "org:apple": ["apple"],
}
# Spellings of one company that the conservative normalisation keeps apart.
MERGES = {"giga byte technology": "gigabyte technology"}


def vendor_norm(name):
    k = re.sub(r"\((?:r|tm)\)|®|™", "", name.lower())
    k = re.sub(r"[.,]", " ", k)
    k = re.sub(r"[^a-z0-9& -]", " ", k).replace("-", " ")
    k = " ".join(re.sub(SUFFIX, " ", k).split())
    return MERGES.get(k, k)


def seed_vendors(records):
    spellings = Counter()
    for r in records:
        if r["vendor"]:
            spellings[r["vendor"]] += r["observations"]
    groups = defaultdict(Counter)
    for name, n in spellings.items():
        groups[vendor_norm(name)][name] += n
    today = date.today().isoformat()
    vendors, aliases = [], []
    for key, names in sorted(groups.items()):
        vid = "org:" + re.sub(r"[^a-z0-9.+]+", "-", key).strip("-")
        row = dict(vendor_id=vid, name=names.most_common(1)[0][0])
        if vid in PREFIXES:
            row["model_prefixes"] = PREFIXES[vid]
        if key in MERGES.values():
            row["note"] = "Merges spellings that normalisation keeps apart (GIGA-BYTE / Gigabyte)."
        vendors.append(row)
        for name in sorted(names):
            # Spellings differing only in case or punctuation share a slug; the text hash keeps IDs unique and stable.
            slug = re.sub(r"[^a-z0-9.+]+", "-", name.lower()).strip("-.")
            aid = f"alias:vendor/{slug}.{hashlib.sha256(name.encode()).hexdigest()[:6]}"
            aliases.append(
                dict(
                    alias_id=aid,
                    entity_kind="vendor",
                    entity_id=vid,
                    match_kind="exact_text",
                    text=name,
                    scope="vendor",
                    status="accepted",
                    reviewed_on=today,
                )
            )
    return vendors, aliases


_PROSE = re.compile(
    r"\b(?:intel|amd|xeon|opteron|epyc|pentium|processors?|cpus?|cores?|ghz|mhz|linux|windows|solaris|gcc|icc|64-bit|32-bit|sles|rhel)\b",
    re.I,
)


def spec_system_key(system, processor, prefixes):
    """Rule spec-system-v1: model name without CPU, clock, cache or vendor prefix; None if nothing remains."""
    text = re.sub(r"\((?:r|tm)\)|®|™", "", system or "", flags=re.I)
    outer = []
    while re.search(r"\([^()]*\)", text):  # innermost first, so nested CPU descriptions go too
        outer = re.findall(r"\(([^()]*)\)", text)  # the final pass holds the outermost groups
        text = re.sub(r"\([^()]*\)", " ", text)
    text = text.replace("(", " ").replace(")", " ")
    if not text.strip(" ,;-") and outer:
        text = outer[0]  # the whole name was parenthesised; its first outermost group is the name
    # A comma followed by processor, clock, OS or compiler words starts configuration prose.
    head, *rest = text.split(",")
    if rest and _PROSE.search(",".join(rest)):
        text = head
    if processor:
        cpu = re.sub(r"\((?:r|tm)\)|®|™", "", processor, flags=re.I).strip()
        if cpu:
            text = re.sub(r"(?<![0-9a-z])" + re.escape(cpu) + r"(?![0-9a-z])", " ", text, flags=re.I)
    text = re.sub(r"\b\d+(?:\.\d+)?\s*[mg]hz\b|\b\d+\s*[kmg]b\b", " ", text, flags=re.I)
    text = " ".join(text.split()).strip(" ,;:/-")
    for prefix in sorted(prefixes, key=len, reverse=True):
        if text.lower().startswith(prefix + " "):
            text = text[len(prefix) + 1 :].strip()
            break
    text = text.strip(" ,;:/-")
    return (text, " ".join(text.lower().split())) if text else (None, None)


def scope_of(source_record_id):
    return ":".join(source_record_id.split(":")[:2])


def extract_records(inputs):
    counts = Counter()
    for line in inputs.read_text().splitlines():
        o = json.loads(line)
        hw = o.get("hardware") or {}
        f = (o.get("raw") or {}).get("fields") or {}
        vendor = (f.get("Hardware Vendor") or f.get("Company") or f.get("company") or "").strip()
        key = (
            scope_of(o["source_record_id"]),
            vendor,
            " ".join((o.get("system") or "").split()),
            " ".join((hw.get("processor") or "").split()),
            hw.get("nominal_mhz"),
            hw.get("enabled_chips"),
            hw.get("enabled_cores"),
            hw.get("hardware_threads_per_core"),
            hw.get("memory_mib"),
        )
        counts[key] += 1
    fields = ["scope", "vendor", "system", "processor", "clock_mhz", "chips", "cores", "threads_per_core", "memory_mib"]
    return [dict(zip(fields, k), observations=n) for k, n in sorted(counts.items(), key=lambda kv: json.dumps(kv[0]))]


@click.command("import-vendors")
@click.option("--root", type=click.Path(path_type=Path, file_okay=False), default=CURATED, show_default=True)
@click.option("--force", is_flag=True, help="Overwrite vendor/system tables and vendor aliases, discarding curated edits.")
def import_vendors_command(root, force):
    """One-time seed: vendors and their exact-text aliases from extracted SPEC hardware records."""
    if any((root / n).exists() for n in ("vendor.jsonl", "system_model.jsonl")) and not force:
        raise click.ClickException("vendor tables exist and are curated data; pass --force to reseed them")
    if not RECORDS.exists():
        raise click.ClickException("run `cpushowspeed data extract-mentions` first")
    records = [json.loads(line) for line in RECORDS.read_text().splitlines()]
    vendors, vendor_aliases = seed_vendors(records)
    aliases = [a for a in read_table(root, dict(file="alias.jsonl")) if a["entity_kind"] != "vendor"]
    write_jsonl(root / "vendor.jsonl", vendors)
    if not (root / "system_model.jsonl").exists():
        write_jsonl(root / "system_model.jsonl", [])
    write_jsonl(root / "alias.jsonl", sorted(aliases + vendor_aliases, key=lambda a: a["alias_id"]))
    _, tables, errors, _ = validate(root)
    for e in errors:
        click.echo(e, err=True)
    json.dump(dict(tables={k: len(v) for k, v in tables.items()}, errors=len(errors)), sys.stdout)
    click.echo()
    if errors:
        sys.exit(1)


def build_systems(db, tables):
    """Write hardware_record, system_model_derived and hardware_config tables."""
    if not RECORDS.exists():
        return {"systems": "skipped: run `cpushowspeed data extract-mentions`"}
    records = [json.loads(line) for line in RECORDS.read_text().splitlines()]
    resolver = Resolver(tables)
    vendor_alias = {a["text"]: a for a in tables["alias"] if a["entity_kind"] == "vendor" and a["status"] == "accepted"}
    system_alias = {a["text"]: a for a in tables["alias"] if a["entity_kind"] == "system_model" and a["status"] == "accepted"}
    prefixes = {v["vendor_id"]: v.get("model_prefixes", []) for v in tables["vendor"]}
    models, configs, stats = {}, {}, Counter()
    db.execute(
        "CREATE TABLE hardware_record (scope TEXT, vendor TEXT, system TEXT, processor TEXT, clock_mhz REAL, chips INTEGER, "
        "cores INTEGER, threads_per_core INTEGER, memory_mib REAL, observations INTEGER, vendor_id TEXT, processor_level TEXT, "
        "processor_entity TEXT, processor_basis TEXT, processor_reason TEXT, system_id TEXT, system_basis TEXT, hardware_id TEXT)"
    )
    for r in records:
        n = r["observations"]
        va = vendor_alias.get(r["vendor"])
        vendor_id = va["entity_id"] if va else None
        p = resolver.resolve(r["scope"], r["processor"], r["clock_mhz"])
        basis = "processor_text"
        if p["level"] == "none" and r["system"]:
            q = resolver.resolve(r["scope"], r["system"], r["clock_mhz"])
            if q["level"] != "none":
                p, basis = q, "system_text"
        if p["level"] == "none":
            basis = None
        sa = system_alias.get(r["system"])
        system_id = system_basis = None
        if sa:
            system_id, system_basis = sa["entity_id"], "alias"
        elif r["scope"].startswith("spec:") and vendor_id:
            name, key = spec_system_key(r["system"], r["processor"], prefixes.get(vendor_id, []))
            if key:
                system_id = "sys:spec/" + re.sub(r"[^a-z0-9.+/]+", "-", key).strip("-")
                system_basis = "rule:spec-system-v1"
                m = models.setdefault(system_id, dict(name=name, vendors=set(), scopes=set(), observations=0))
                m["vendors"].add(vendor_id)
                m["scopes"].add(r["scope"])
                m["observations"] += n
        hardware_id = None
        if system_id and p["level"] != "none":
            parts = [system_id, p["entity_id"]] + [r[k] for k in ("clock_mhz", "chips", "cores", "threads_per_core", "memory_mib")]
            hardware_id = "hw:" + hashlib.sha256(json.dumps(parts).encode()).hexdigest()[:16]
            c = configs.setdefault(hardware_id, dict(parts=parts, scopes=set(), observations=0))
            c["scopes"].add(r["scope"])
            c["observations"] += n
        db.execute(
            "INSERT INTO hardware_record VALUES (" + ", ".join("?" * 18) + ")",
            (
                *(r[k] for k in ("scope", "vendor", "system", "processor", "clock_mhz", "chips", "cores", "threads_per_core")),
                r["memory_mib"],
                n,
                vendor_id,
                p["level"],
                p["entity_id"],
                basis,
                p["reason"],
                system_id,
                system_basis,
                hardware_id,
            ),
        )
        stats["observations"] += n
        stats["vendor_resolved"] += n if vendor_id else 0
        stats["processor_from_system_text"] += n if basis == "system_text" else 0
        stats["system_resolved"] += n if system_id else 0
        stats["hardware_resolved"] += n if hardware_id else 0
    db.execute(
        "CREATE TABLE system_model_derived (system_id TEXT PRIMARY KEY, name TEXT, vendor_ids TEXT, scopes TEXT, observations INTEGER)"
    )
    db.executemany(
        "INSERT INTO system_model_derived VALUES (?, ?, ?, ?, ?)",
        [
            (k, m["name"], json.dumps(sorted(m["vendors"])), json.dumps(sorted(m["scopes"])), m["observations"])
            for k, m in sorted(models.items())
        ],
    )
    db.execute(
        "CREATE TABLE hardware_config (hardware_id TEXT PRIMARY KEY, system_id TEXT, processor_entity TEXT, clock_mhz REAL, "
        "chips INTEGER, cores INTEGER, threads_per_core INTEGER, memory_mib REAL, scopes TEXT, observations INTEGER)"
    )
    db.executemany(
        "INSERT INTO hardware_config VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(k, *c["parts"], json.dumps(sorted(c["scopes"])), c["observations"]) for k, c in sorted(configs.items())],
    )
    meta = {"hardware_records_sha256": sha256(RECORDS), "hardware_records": str(len(records))}
    meta.update({f"systems:observations:{k}": str(v) for k, v in sorted(stats.items())})
    meta["systems:derived_models"] = str(len(models))
    meta["systems:models_with_several_vendors"] = str(sum(len(m["vendors"]) > 1 for m in models.values()))
    meta["systems:models_in_several_spec_suites"] = str(sum(len(m["scopes"]) > 1 for m in models.values()))
    meta["systems:hardware_configs"] = str(len(configs))
    meta["systems:hardware_configs_in_several_spec_suites"] = str(sum(len(c["scopes"]) > 1 for c in configs.values()))
    return meta
