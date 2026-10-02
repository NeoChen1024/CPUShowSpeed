"""Processor identity (schema step 2): entities, aliases, extracted mentions and resolution.

Resolution order for one processor mention (scope, text, nominal clock):
1. an accepted or rejected exact-text alias in scope;
2. a versioned rule (sku-key-v1) whose key names one catalogued SKU and whose
   constraints hold;
3. an accepted family pattern, giving a partial (family-level) resolution.
A mention that fails a SKU rule keeps the failure reason even when a family
pattern resolves it. Nothing is guessed beyond what the text supports.
"""

import csv
import fnmatch
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import click
from cpushowspeed.cpu_chronology import sku_key
from cpushowspeed.curated import CURATED, read_table, sha256, validate, write_jsonl

CATALOG = Path("research/data/historical/cpu-sku-chronology.csv")
INPUTS = Path("data/derived/inputs/observations.jsonl")
MENTIONS = Path("data/derived/schema/processor-mentions.jsonl")
RULES = {"sku-key-v1": sku_key}
FAMILIES = {
    "intel xeon": ("fam:intel-xeon", "Intel", "Xeon"),
    "amd opteron": ("fam:amd-opteron", "AMD", "Opteron"),
    "amd epyc": ("fam:amd-epyc", "AMD", "EPYC"),
}
# Family-level fallbacks seeded with the catalogue; further patterns are curated in alias.jsonl.
FAMILY_PATTERNS = [
    ("intel-xeon", "fam:intel-xeon", r"\bxeon\b"),
    ("amd-opteron", "fam:amd-opteron", r"\bopteron\b"),
    ("amd-epyc", "fam:amd-epyc", r"\bepyc\b"),
]


def slug(text):
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9.+]+", "-", text.lower())).strip("-")


def display_model(key, family_name):
    """'intel xeon gold 6130' -> 'Xeon Gold 6130'; model tokens keep their case."""
    prefix = next(p for p in FAMILIES if key.startswith(p + " "))
    rest = key[len(prefix) + 1 :].split(" ")
    tokens = [
        (
            t.upper()
            if t.isalpha() and len(t) <= 2
            else t.capitalize() if t.isalpha() else t if re.fullmatch(r"v\d+", t) else t[:1].upper() + t[1:]
        )
        for t in rest
    ]
    return " ".join([family_name] + tokens)


def seed_processors(source_rows):
    by_legacy = {legacy: s["source_id"] for s in source_rows for legacy in s["legacy_ids"]}
    with CATALOG.open(newline="") as f:
        catalog = list(csv.DictReader(f))
    groups = defaultdict(list)
    for r in catalog:
        groups[r["sku_key"]].append(r)
    families, skus = {}, []
    for key, rows in sorted(groups.items()):
        prefix = next(p for p in FAMILIES if key.startswith(p + " "))
        family_id, vendor, name = FAMILIES[prefix]
        sources = sorted({by_legacy[f"historical/cpu-sku-sources:{r['source_title']}@{r['source_revision']}"] for r in rows})
        families.setdefault(family_id, dict(family_id=family_id, vendor=vendor, name=name, source_ids=set()))
        families[family_id]["source_ids"].update(sources)
        sku = dict(
            sku_id="sku:" + slug(key),
            family_id=family_id,
            vendor=vendor,
            model=display_model(key, name),
            keys=["sku-key-v1:" + key],
        )
        clocks = sorted({float(r["base_clock_mhz"]) for r in rows if r["base_clock_mhz"]})
        if clocks:
            sku["base_clocks_mhz"] = clocks
        sku["sections"] = sorted({r["source_section"] for r in rows if r["source_section"]})
        sku["source_ids"] = sources
        skus.append(sku)
    family_rows = [dict(f, source_ids=sorted(f["source_ids"])) for f in sorted(families.values(), key=lambda f: f["family_id"])]
    skus.sort(key=lambda s: s["sku_id"])
    today = date.today().isoformat()
    aliases = [
        dict(
            alias_id="alias:rule/sku-key-v1",
            entity_kind="processor_sku",
            match_kind="rule",
            rule_id="sku-key-v1",
            scope="processor",
            constraints=dict(clock_within=0.02),
            status="accepted",
            reviewed_on=today,
            note="Exactly one Xeon/Opteron/EPYC SKU named in the text; tier words are part of the key. "
            "A known nominal clock must lie within 2% of a listed base clock.",
        )
    ] + [
        dict(
            alias_id="alias:pattern/" + name,
            entity_kind="processor_family",
            entity_id=family,
            match_kind="pattern",
            pattern=pattern,
            scope="processor",
            status="accepted",
            reviewed_on=today,
            note="Family-level fallback when no single SKU resolves.",
        )
        for name, family, pattern in FAMILY_PATTERNS
    ]
    return family_rows, skus, sorted(aliases, key=lambda a: a["alias_id"])


@click.command("import-processors")
@click.option("--root", type=click.Path(path_type=Path, file_okay=False), default=CURATED, show_default=True)
@click.option("--force", is_flag=True, help="Overwrite existing processor/alias tables, discarding curated edits.")
def import_processors_command(root, force):
    """One-time seed: processor families, SKUs and initial aliases from the parsed SKU catalogue."""
    names = ["processor_family.jsonl", "processor_sku.jsonl", "alias.jsonl"]
    if any((root / n).exists() for n in names) and not force:
        raise click.ClickException("processor tables exist and are curated data; pass --force to reseed them")
    try:
        sources = read_table(root, dict(file="source.jsonl"))
        for name, rows in zip(names, seed_processors(sources)):
            write_jsonl(root / name, rows)
        _, tables, errors, _ = validate(root)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    for e in errors:
        click.echo(e, err=True)
    json.dump(dict(tables={k: len(v) for k, v in tables.items()}, errors=len(errors)), sys.stdout)
    click.echo()
    if errors:
        sys.exit(1)


def mention_scope(source_record_id):
    """'spec:cpu2006:rate:...' -> 'spec:cpu2006'; the origin and its source or suite."""
    return ":".join(source_record_id.split(":")[:2])


@click.command("extract-mentions")
@click.option("--inputs", type=click.Path(path_type=Path, exists=True, dir_okay=False), default=INPUTS, show_default=True)
@click.option("--output", type=click.Path(path_type=Path, dir_okay=False), default=MENTIONS, show_default=True)
def extract_mentions_command(inputs, output):
    """Extract distinct processor mentions (scope, text, nominal clock) from the input catalogue."""
    counts = Counter()
    for line in inputs.read_text().splitlines():
        o = json.loads(line)
        hw = o.get("hardware") or {}
        text = re.sub(r"\s+", " ", hw.get("processor") or "").strip()
        counts[mention_scope(o["source_record_id"]), text, hw.get("nominal_mhz")] += 1
    rows = [
        dict(scope=s, text=t, clock_mhz=c, observations=n)
        for (s, t, c), n in sorted(counts.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] is None, kv[0][2] or 0))
    ]
    write_jsonl(output, rows)
    from cpushowspeed.curated_system import RECORDS, extract_records

    records = extract_records(inputs)
    write_jsonl(RECORDS, records)
    meta = dict(
        inputs={str(inputs): sha256(inputs)},
        code_sha256={str(p): sha256(p) for p in [Path(__file__), Path(sys.modules[sku_key.__module__].__file__)]},
        mentions=len(rows),
        hardware_records=len(records),
        observations=sum(counts.values()),
    )
    output.with_name(output.name + ".meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    json.dump(meta, sys.stdout, indent=2)
    click.echo()


def in_scope(alias_scope, mention_scope):
    field, _, pattern = alias_scope.partition("@")
    return field == "processor" and (not pattern or fnmatch.fnmatchcase(mention_scope, pattern))


class Resolver:
    def __init__(self, tables):
        aliases = sorted(tables["alias"], key=lambda a: a["alias_id"])
        self.exact = [a for a in aliases if a["match_kind"] == "exact_text" and a["status"] != "candidate"]
        self.rules = [a for a in aliases if a["match_kind"] == "rule" and a["status"] == "accepted"]
        self.patterns = [
            # Case-insensitive by default; a pattern may switch it off locally with (?-i:...).
            (a, re.compile(a["pattern"], re.I))
            for a in aliases
            if a["match_kind"] == "pattern" and a["status"] == "accepted"
        ]
        self.by_key = {}
        for s in tables["processor_sku"]:
            for k in s["keys"]:
                if k in self.by_key:
                    raise ValueError(f"match key {k} names both {self.by_key[k]['sku_id']} and {s['sku_id']}")
                self.by_key[k] = s

    def resolve(self, scope, text, clock):
        result = dict(level="none", entity_kind=None, entity_id=None, alias_id=None, reason=None, detail=None)
        if not text:
            return dict(result, reason="missing_text")
        for a in self.exact:
            if in_scope(a["scope"], scope) and a["text"] == text:
                if a["status"] == "rejected":
                    return dict(result, alias_id=a["alias_id"], reason="rejected_alias")
                level = "sku" if a["entity_kind"] == "processor_sku" else "family"
                return dict(result, level=level, entity_kind=a["entity_kind"], entity_id=a["entity_id"], alias_id=a["alias_id"])
        for a in self.rules:
            if not in_scope(a["scope"], scope):
                continue
            key = RULES[a["rule_id"]](text)
            if key is None:
                result.update(reason="no_single_sku")
                continue
            sku = self.by_key.get(a["rule_id"] + ":" + key)
            if sku is None:
                result.update(reason="sku_not_in_catalog", detail=key)
                continue
            tolerance = (a.get("constraints") or {}).get("clock_within")
            clocks = sku.get("base_clocks_mhz") or []
            if tolerance and clock and clocks and not any(abs(clock - b) <= tolerance * b for b in clocks):
                result.update(reason="clock_conflict", detail=f"{sku['sku_id']} base {clocks} vs {clock}")
                continue
            return dict(result, level="sku", entity_kind="processor_sku", entity_id=sku["sku_id"], alias_id=a["alias_id"])
        plain = re.sub(r"\((?:r|tm)\)|®|™", "", text, flags=re.I)
        hits = [a for a, pattern in self.patterns if in_scope(a["scope"], scope) and pattern.search(plain)]
        if len({a["entity_id"] for a in hits}) > 1:
            # Patterns are meant to be mutually exclusive; overlap is a curation error, not a choice.
            return dict(result, reason="ambiguous_family_patterns", detail=", ".join(a["alias_id"] for a in hits))
        if hits:
            a = hits[0]
            return dict(result, level="family", entity_kind="processor_family", entity_id=a["entity_id"], alias_id=a["alias_id"])
        return dict(result, reason=result["reason"] or "no_match")


def build_resolution(db, tables):
    """Write processor_mention and processor_resolution when extracted mentions exist."""
    if not MENTIONS.exists():
        return {"resolution": "skipped: run `cpushowspeed data extract-mentions`"}
    resolver = Resolver(tables)
    mentions = [json.loads(line) for line in MENTIONS.read_text().splitlines()]
    db.execute("CREATE TABLE processor_mention (scope TEXT, text TEXT, clock_mhz REAL, observations INTEGER)")
    db.execute(
        "CREATE TABLE processor_resolution (scope TEXT, text TEXT, clock_mhz REAL, observations INTEGER, level TEXT, "
        "entity_kind TEXT, entity_id TEXT, alias_id TEXT, reason TEXT, detail TEXT)"
    )
    levels, reasons = Counter(), Counter()
    for m in mentions:
        r = resolver.resolve(m["scope"], m["text"], m["clock_mhz"])
        db.execute("INSERT INTO processor_mention VALUES (?, ?, ?, ?)", (m["scope"], m["text"], m["clock_mhz"], m["observations"]))
        db.execute(
            "INSERT INTO processor_resolution VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                m["scope"],
                m["text"],
                m["clock_mhz"],
                m["observations"],
                *(r[k] for k in ("level", "entity_kind", "entity_id", "alias_id", "reason", "detail")),
            ),
        )
        levels[r["level"]] += m["observations"]
        if r["reason"]:
            reasons[r["reason"]] += m["observations"]
    meta = {"mentions_sha256": sha256(MENTIONS), "mentions": str(len(mentions))}
    meta.update({f"resolution:observations:{k}": str(v) for k, v in sorted(levels.items())})
    meta.update({f"resolution:reason:{k}": str(v) for k, v in sorted(reasons.items())})
    return meta
