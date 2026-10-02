"""System identity (schema step 2b): vendors, system models and hardware configurations.

A hardware record is one distinct (scope, vendor text, system text, processor text,
clock, chips, cores, threads/core, memory) tuple from the input catalogue. Build:
1. vendor text -> vendor by accepted exact-text alias;
2. processor text -> processor entity; when that fails, the system text is tried
   and the result is marked as read from the system name;
3. system text -> system model by exact alias, else by rule: spec-system-v1 for SPEC
   records with a resolved vendor (that vendor's prefixes), name-system-v1 otherwise
   (every known brand prefix). Both rules share one key space, so a machine named
   in a classical table and in a SPEC disclosure becomes one model; a curated model
   with the same ID supplies its name;
4. a hardware configuration is the tuple of system model, processor entity, nominal
   clock, chips, cores, threads/core, memory and hardware options (FPA, FPU); equal
   tuples share one ID and an unknown value never equals a known one.
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
    "org:compaq": ["compaq", "digital", "dec"],
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


# Hardware options are configuration facts, not part of the model name.
_OPTIONS = re.compile(r"(?<![0-9a-z])(no[\s-]*fpa|nofpa|with\s+fpa|fpa|w/\s*(?:68)?88[12]|with\s+fpu|eae)(?![0-9a-z])", re.I)
# Brand words that machine names repeat in sources without a vendor field.
BRANDS = [
    "dec",
    "digital",
    "sun",
    "hp",
    "ibm",
    "sgi",
    "cray",
    "cray research",
    "apple",
    "compaq",
    "data general",
    "mips",
    "convex",
    "amdahl",
    "control data",
    "cdc",
    "honeywell",
    "univac",
    "burroughs",
    "ncr",
    "prime",
    "wang",
    "siemens",
]
# Canonical brand word restored when a stripped name has no letters left ("Control Data 7600" -> "cdc 7600").
CANONICAL_BRAND = {
    "control data": "cdc",
    "cdc": "cdc",
    "digital": "dec",
    "dec": "dec",
    "digital equipment": "dec",
    "hewlett-packard": "hp",
    "hewlett packard": "hp",
    "hewlett packard enterprise": "hp",
    "hpe": "hp",
    "hp": "hp",
    "sun microsystems": "sun",
    "sun": "sun",
    "silicon graphics": "sgi",
    "sgi": "sgi",
    "cray research": "cray",
    "cray": "cray",
}
_PROSE = re.compile(
    r"\b(?:intel|amd|xeon|opteron|epyc|pentium|processors?|cpus?|cores?|ghz|mhz|linux|windows|solaris|gcc|icc|64-bit|32-bit|sles|rhel)\b",
    re.I,
)


def system_key(system, processor, prefixes, vendor_brand=None):
    """Model name without CPU, clock, cache, option or brand prefix.

    Returns (name, key, options, prefix); name and key are None when nothing remains.
    """
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
            # Hyphens bind model suffixes ("SPARC T3-1" is a system, "SPARC T3" its processor).
            text = re.sub(r"(?<![0-9a-z-])" + re.escape(cpu) + r"(?![0-9a-z-])", " ", text, flags=re.I)
    text = re.sub(r"\b\d+(?:\.\d+)?\s*[mg]hz\b|\b\d+\s*[kmg]b\b", " ", text, flags=re.I)
    options = sorted(
        {re.sub(r"^no\s*fpa$", "no fpa", " ".join(m.lower().replace("-", " ").split())) for m in _OPTIONS.findall(text)}
    )
    stripped = _OPTIONS.sub(" ", text)
    if stripped.strip(" ,;:/-"):
        text = stripped
    else:
        options = []
    text = " ".join(text.split()).strip(" ,;:/-")
    used = None
    for prefix in sorted(prefixes, key=len, reverse=True):
        if text.lower().startswith(prefix.lower() + " "):
            text, used = text[len(prefix) + 1 :].strip(" ,;:/-"), prefix.lower()
            break
    text = text.strip(" ,;:/-")
    if not text:
        return None, None, [], None
    # Key-only spelling equivalences: "3000 Model 700" and "3000/700", "6 /901" and "6/901".
    key = " ".join(text.lower().split())
    key = re.sub(r"\s+models?\s+(?=[0-9a-z])", "/", key)
    key = re.sub(r"\s*/\s*", "/", key)
    key = re.sub(r"\s+axp$", "", key)  # DEC's Alpha marketing suffix: "7000/610 AXP" is the 7000/610
    key = re.sub(r"^(hp\s*)?9000 series \d00/", r"\g<1>9000/", key)  # "HP 9000 Series 700 Model 720" is the HP 9000/720
    if not re.search(r"[a-z]", key):
        # A bare number ("750", "4/260") is not a model name without its brand; with no brand it names nothing.
        if not (used or vendor_brand):
            return None, None, [], None
        brand = CANONICAL_BRAND.get(used, used) if used else vendor_brand
        text = (brand.upper() if len(brand) <= 3 else brand.title()) + " " + text
        key = brand + " " + key
    return text, key, options, used


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


def brand_prefixes(tables):
    """Every brand word name-system-v1 may strip: built-in brands, vendor prefixes, names and spellings."""
    prefixes = [p for v in tables["vendor"] for p in v.get("model_prefixes", [])]
    return sorted(
        set(BRANDS)
        | {p.lower() for p in prefixes}
        | {v["name"].lower() for v in tables["vendor"]}
        | {a["text"].lower() for a in tables["alias"] if a["entity_kind"] == "vendor"}
    )


def model_id(key):
    # Spaces and hyphens are spelling only ("UCS C240 M5" / "UCS C240M5", "VAX-11/780").
    return "sys:" + re.sub(r"[^a-z0-9.+/]", "", key)


def build_systems(db, tables):
    """Write hardware_record, system_model_derived and hardware_config tables."""
    if not RECORDS.exists():
        return {"systems": "skipped: run `cpushowspeed data extract-mentions`"}
    records = [json.loads(line) for line in RECORDS.read_text().splitlines()]
    resolver = Resolver(tables)
    vendor_alias = {a["text"]: a for a in tables["alias"] if a["entity_kind"] == "vendor" and a["status"] == "accepted"}
    system_alias = {a["text"]: a for a in tables["alias"] if a["entity_kind"] == "system_model" and a["status"] != "candidate"}
    prefixes = {v["vendor_id"]: v.get("model_prefixes", []) for v in tables["vendor"]}
    brands = brand_prefixes(tables)
    curated = {m["system_id"]: m for m in tables["system_model"]}
    models, configs, stats = {}, {}, Counter()
    db.execute(
        "CREATE TABLE hardware_record (scope TEXT, vendor TEXT, system TEXT, processor TEXT, clock_mhz REAL, chips INTEGER, "
        "cores INTEGER, threads_per_core INTEGER, memory_mib REAL, observations INTEGER, vendor_id TEXT, processor_level TEXT, "
        "processor_entity TEXT, processor_basis TEXT, processor_reason TEXT, system_id TEXT, system_basis TEXT, options TEXT, "
        "hardware_id TEXT)"
    )
    for r in records:
        n = r["observations"]
        va = vendor_alias.get(r["vendor"])
        vendor_id = va["entity_id"] if va else None
        p = resolver.resolve(r["scope"], r["processor"], r["clock_mhz"])
        basis = "processor_text"
        if p["level"] == "none" and r["system"]:
            q = resolver.resolve(r["scope"], r["system"], r["clock_mhz"], field="processor-from-system")
            if q["level"] != "none":
                p, basis = q, "system_text"
        if p["level"] == "none":
            basis = None
        system_id = system_basis = brand = None
        name, options = None, []
        sa = system_alias.get(r["system"])
        if sa and sa["status"] == "rejected":
            system_basis = "rejected_alias"  # not a machine name (parsing residue); left unresolved
        elif sa:
            system_id, system_basis = sa["entity_id"], "alias"
            _, _, options, _ = system_key(r["system"], r["processor"], [])
        elif r["system"]:
            spec = r["scope"].startswith("spec:") and vendor_id
            vendor_brand = (prefixes.get(vendor_id) or [vendor_norm(r["vendor"]).split(" ")[0]])[0] if vendor_id else None
            name, key, options, brand = system_key(
                r["system"], r["processor"], prefixes.get(vendor_id, []) if spec else brands, vendor_brand
            )
            if key:
                # One key space for every rule, so a machine links across sources.
                system_id = model_id(key)
                system_basis = "rule:" + ("spec-system-v1" if spec else "name-system-v1")
        if system_id:
            m = models.setdefault(system_id, dict(name=name, vendors=set(), brands=set(), scopes=set(), observations=0))
            m["name"] = m["name"] or name
            if vendor_id:
                m["vendors"].add(vendor_id)
            if brand:
                m["brands"].add(brand)
            m["scopes"].add(r["scope"])
            m["observations"] += n
        hardware_id = None
        if system_id and p["level"] != "none":
            parts = [system_id, p["entity_id"]] + [r[k] for k in ("clock_mhz", "chips", "cores", "threads_per_core", "memory_mib")]
            parts.append(options)
            hardware_id = "hw:" + hashlib.sha256(json.dumps(parts).encode()).hexdigest()[:16]
            c = configs.setdefault(hardware_id, dict(parts=parts, scopes=set(), observations=0))
            c["scopes"].add(r["scope"])
            c["observations"] += n
        db.execute(
            "INSERT INTO hardware_record VALUES (" + ", ".join("?" * 19) + ")",
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
                json.dumps(options) if options else None,
                hardware_id,
            ),
        )
        stats["observations"] += n
        stats["vendor_resolved"] += n if vendor_id else 0
        stats["processor_from_system_text"] += n if basis == "system_text" else 0
        stats["system_resolved"] += n if system_id else 0
        stats["hardware_resolved"] += n if hardware_id else 0
    db.execute(
        "CREATE TABLE system_model_derived (system_id TEXT PRIMARY KEY, name TEXT, curated INTEGER, vendor_ids TEXT, "
        "brands TEXT, scopes TEXT, observations INTEGER)"
    )
    db.executemany(
        "INSERT INTO system_model_derived VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                k,
                curated[k]["name"] if k in curated else m["name"],
                int(k in curated),
                json.dumps(sorted(m["vendors"] | set(curated.get(k, {}).get("vendor_ids", [])))),
                json.dumps(sorted(m["brands"])),
                json.dumps(sorted(m["scopes"])),
                m["observations"],
            )
            for k, m in sorted(models.items())
        ],
    )
    db.execute(
        "CREATE TABLE hardware_config (hardware_id TEXT PRIMARY KEY, system_id TEXT, processor_entity TEXT, clock_mhz REAL, "
        "chips INTEGER, cores INTEGER, threads_per_core INTEGER, memory_mib REAL, options TEXT, scopes TEXT, observations INTEGER)"
    )
    db.executemany(
        "INSERT INTO hardware_config VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                k,
                *c["parts"][:-1],
                json.dumps(c["parts"][-1]) if c["parts"][-1] else None,
                json.dumps(sorted(c["scopes"])),
                c["observations"],
            )
            for k, c in sorted(configs.items())
        ],
    )
    spec_scopes = lambda m: {s for s in m["scopes"] if s.startswith("spec:")}  # noqa: E731
    meta = {"hardware_records_sha256": sha256(RECORDS), "hardware_records": str(len(records))}
    meta.update({f"systems:observations:{k}": str(v) for k, v in sorted(stats.items())})
    meta["systems:models"] = str(len(models))
    meta["systems:models_with_several_vendors"] = str(sum(len(m["vendors"]) > 1 for m in models.values()))
    meta["systems:models_with_several_brand_prefixes"] = str(sum(len(m["brands"]) > 1 for m in models.values()))
    meta["systems:models_in_several_spec_suites"] = str(sum(len(spec_scopes(m)) > 1 for m in models.values()))
    meta["systems:models_linking_spec_and_other_sources"] = str(
        sum(bool(spec_scopes(m)) and len(m["scopes"]) > len(spec_scopes(m)) for m in models.values())
    )
    meta["systems:hardware_configs"] = str(len(configs))
    meta["systems:hardware_configs_in_several_spec_suites"] = str(
        sum(len({s for s in c["scopes"] if s.startswith("spec:")}) > 1 for c in configs.values())
    )
    return meta
