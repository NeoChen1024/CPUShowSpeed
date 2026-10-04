"""Processor identity (schema step 2): entities, aliases, extracted mentions and resolution.

Resolution order for one processor mention (scope, text, nominal clock):
1. an accepted or rejected exact-text alias in scope;
2. a versioned rule (sku-key-v1) whose key names one catalogued SKU and whose
   constraints hold;
3. an accepted family pattern, giving a partial (family-level) resolution.
A mention that fails a SKU rule keeps the failure reason even when a family
pattern resolves it. Nothing is guessed beyond what the text supports.
"""

import fnmatch
import json
import re
import sys
from collections import Counter
from pathlib import Path

import click
from cpushowspeed.database.curated_tables import sha256, write_jsonl
from cpushowspeed.database.processor_keys import sku_key
from cpushowspeed.parallel import jobs_option

MENTIONS = Path("data/derived/schema/processor-mentions.jsonl")
RULES = {"sku-key-v1": sku_key}


@click.command("extract")
@click.option("--raw-dir", type=click.Path(path_type=Path, file_okay=False), default=Path("data/raw/spec"), show_default=True)
@jobs_option
def extract_command(raw_dir, jobs):
    """Run every source adapter into benchmark-observation-v2, then extract mentions, hardware and results."""
    from cpushowspeed.database.extract_adapters import records
    from cpushowspeed.database.observation_records import write_jsonl as write_observations
    from cpushowspeed.database.observations import OBSERVATIONS
    from cpushowspeed.spec import source_fields

    source_fields.JOBS = jobs
    observations = write_observations(OBSERVATIONS, records(raw_dir))
    counts = Counter()
    with OBSERVATIONS.open() as stream:
        for line in stream:
            o = json.loads(line)
            text = re.sub(r"\s+", " ", o["hardware"].get("processor") or "").strip()
            counts[o["scope"], text, o["hardware"].get("nominal_mhz")] += 1
    rows = [
        dict(scope=s, text=t, clock_mhz=c, observations=n)
        for (s, t, c), n in sorted(counts.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] is None, kv[0][2] or 0))
    ]
    write_jsonl(MENTIONS, rows)
    from cpushowspeed.database.system_identity import RECORDS, extract_records

    records_ = extract_records(OBSERVATIONS)
    write_jsonl(RECORDS, records_)
    from cpushowspeed.database.dates import MODEL_YEARS, RESULTS, extract_model_years, extract_results

    results = extract_results(OBSERVATIONS)
    write_jsonl(RESULTS, results)
    write_jsonl(MODEL_YEARS, extract_model_years())
    meta = dict(
        observations={str(OBSERVATIONS): sha256(OBSERVATIONS)},
        code_sha256={str(p): sha256(p) for p in [Path(__file__), Path(sys.modules[sku_key.__module__].__file__)]},
        mentions=len(rows),
        hardware_records=len(records_),
        results=len(results),
        observation_count=observations,
    )
    MENTIONS.with_name(MENTIONS.name + ".meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    json.dump(meta, sys.stdout, indent=2)
    click.echo()


def in_scope(alias_scope, mention_scope, field="processor"):
    """'processor' aliases apply to processor text and to the system-name fallback;
    'processor-from-system' aliases apply only to that fallback."""
    kind, _, pattern = alias_scope.partition("@")
    fits = kind == field or (kind == "processor" and field == "processor-from-system")
    return fits and (not pattern or fnmatch.fnmatchcase(mention_scope, pattern))


def clock_fits(alias, clock):
    want = (alias.get("constraints") or {}).get("clock_mhz")
    # Only a known, different clock rules the alias out; the alias text already names its part.
    return want is None or clock is None or abs(clock - want) <= 0.01 * want


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

    def resolve(self, scope, text, clock, field="processor"):
        result = dict(level="none", entity_kind=None, entity_id=None, alias_id=None, reason=None, detail=None)
        if not text:
            return dict(result, reason="missing_text")
        for a in self.exact:
            if in_scope(a["scope"], scope, field) and a["text"] == text and clock_fits(a, clock):
                if a["status"] == "rejected":
                    return dict(result, alias_id=a["alias_id"], reason="rejected_alias")
                level = "sku" if a["entity_kind"] == "processor_sku" else "family"
                return dict(result, level=level, entity_kind=a["entity_kind"], entity_id=a["entity_id"], alias_id=a["alias_id"])
        for a in self.rules:
            if not in_scope(a["scope"], scope, field):
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
        hits = [a for a, pattern in self.patterns if in_scope(a["scope"], scope, field) and pattern.search(plain)]
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
        return {"resolution": "skipped: run `cpushowspeed data extract`"}
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
