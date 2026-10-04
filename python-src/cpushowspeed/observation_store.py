"""Read access to the built database for fitters: observations, results and input identity.

Fitters never re-derive identity. A SPEC result's `system_key` is its resolved
`system_id`; its `processor_key` is the resolved processor:

- `sku`: a catalogued SKU;
- `uncatalogued_model`: the family plus the model the SKU rule parsed but the
  catalogue lacks (`fam:intel-xeon#intel xeon 6787p`);
- `clock_variants_only`: a family whose members differ only in clock or cores;
- `broad_family`: any other family; such a key cannot establish equal hardware.

Unresolved values are empty and do not pair.
"""

import hashlib
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

from cpushowspeed.curated import DATABASE
from cpushowspeed.spec_overlap import Result

MODES = ("base", "peak")


def connect(database: Path = DATABASE) -> sqlite3.Connection:
    if not Path(database).exists():
        raise ValueError(f"{database} is missing; run `cpushowspeed data extract` and `cpushowspeed data build`")
    db = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    if db.execute("SELECT 1 FROM sqlite_master WHERE name = 'observation'").fetchone() is None:
        db.close()
        raise ValueError(f"{database} has no observation table; run `cpushowspeed data extract` and rebuild")
    return db


def inputs_digest(db: sqlite3.Connection) -> str:
    """One digest of every curated table, extracted file and schema the database was built from."""
    rows = db.execute("SELECT key, value FROM _meta WHERE key LIKE '%sha256' ORDER BY key").fetchall()
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def processor_keys(db: sqlite3.Connection, scope: str) -> dict[tuple, tuple[str, str]]:
    """(text, clock) -> (pairing key, basis) for one scope."""
    single = {r[0] for r in db.execute("SELECT family_id FROM processor_family WHERE clock_variants_only = 1")}
    keys = {}
    query = "SELECT text, clock_mhz, level, entity_id, reason, detail FROM processor_resolution WHERE scope = ?"
    for text, clock, level, entity, reason, detail in db.execute(query, (scope,)):
        if level == "sku":
            keys[text, clock] = entity, "sku"
        elif level == "family" and reason == "sku_not_in_catalog" and detail:
            keys[text, clock] = f"{entity}#{detail.lower()}", "uncatalogued_model"
        elif level == "family":
            keys[text, clock] = entity, "clock_variants_only" if entity in single else "broad_family"
        else:
            keys[text, clock] = "", "unresolved"
    return keys


def spec_results(db: sqlite3.Connection, generation: str, track: str) -> list[Result]:
    """One Result per SPEC disclosure with its base and peak scores, ordered by result."""
    prefix = f"spec:{generation}:{track}:"
    keys = processor_keys(db, f"spec:{generation}")
    grouped = defaultdict(dict)
    systems = {}
    query = "SELECT result_id, mode, record, system_id FROM observation WHERE scope = ? AND track = ? ORDER BY result_id, mode"
    for result_id, mode, record, system_id in db.execute(query, (f"spec:{generation}", track)):
        grouped[result_id][mode] = json.loads(record)
        systems[result_id] = system_id or ""
    results = []
    for result_id, modes in grouped.items():
        first = next(iter(modes.values()))
        hw, run = first["hardware"], first["run"]
        execution = dict(
            status=first["execution"].get("status", "not_collected"),
            modes={
                m: {k: v for k, v in o["execution"].items() if k in ("quantity", "status", "minimum", "maximum")}
                for m, o in modes.items()
            },
            execution=[b for o in modes.values() for b in o["execution"].get("benchmarks", [])],
            document_url=first["execution"].get("source_url"),
            source_sha256=first["execution"].get("source_sha256"),
        )
        text = " ".join((hw.get("processor") or "").split())
        processor_key, basis = keys.get((text, hw.get("nominal_mhz")), ("", "unresolved"))
        results.append(
            Result(
                generation,
                result_id.removeprefix(prefix),
                first["system"],
                systems[result_id],
                hw.get("processor") or "",
                processor_key,
                hw.get("enabled_chips") or hw.get("legacy_cpu_count"),
                hw.get("enabled_cores"),
                hw.get("hardware_threads_per_core"),
                hw.get("nominal_mhz"),
                hw.get("memory_mib"),
                run.get("os", ""),
                run.get("compiler", ""),
                modes["peak"]["value"] if "peak" in modes else None,
                modes["base"]["value"] if "base" in modes else None,
                first["source"]["url"],
                first["source"].get("sha256") or "",
                track=track,
                processor_basis=basis,
                execution=execution,
                raw_fields=(first["raw"] or {}).get("fields") or {},
            )
        )
    return results


def result_pair_reviews(db: sqlite3.Connection, left_prefix: str, right_prefix: str) -> dict[tuple[str, str], tuple[str, str]]:
    """(left id, right id) without prefixes -> (review id, decision) for reviewed result pairs."""
    sides = defaultdict(dict)
    query = "SELECT review_id, side, decision, result_id FROM review_result WHERE target_kind = 'result_pair'"
    for review_id, side, decision, result_id in db.execute(query):
        sides[review_id, decision][side] = result_id
    return {
        (ids["left"].removeprefix(left_prefix), ids["right"].removeprefix(right_prefix)): (review_id, decision)
        for (review_id, decision), ids in sides.items()
        if ids.get("left", "").startswith(left_prefix) and ids.get("right", "").startswith(right_prefix)
    }
