"""Curated table contract: load data/curated, validate against schema.json, build SQLite."""

import hashlib
import json
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import click
import jsonschema
from referencing import Registry, Resource

CURATED = Path("data/curated")
DATABASE = Path("data/derived/schema/cpushowspeed.sqlite")
INVENTORY = Path("data/derived/documents/inventory.sqlite")
PRECISION = {
    "year": r"[0-9]{4}",
    "quarter": r"[0-9]{4}-Q[1-4]",
    "month": r"[0-9]{4}-[0-9]{2}",
    "day": r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_schema(root=CURATED):
    schema = json.loads((root / "schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    return schema


def row_validator(schema, pointer):
    registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
    return jsonschema.Draft202012Validator({"$ref": schema["$id"] + pointer}, registry=registry)


def read_table(root, spec):
    path = root / spec["file"]
    if not spec["file"].endswith(".jsonl"):
        raise ValueError("unsupported curated table format: " + spec["file"])
    rows = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            raise ValueError(f"{path}:{number}: blank line")
        rows.append(json.loads(line))
    return rows


def load_tables(root=CURATED):
    schema = load_schema(root)
    return schema, {name: read_table(root, spec) for name, spec in schema["x-tables"].items()}


def row_errors(table, spec, rows, validator):
    """Schema errors, primary-key duplicates and cross-field rules JSON Schema cannot express."""
    errors, seen = [], set()
    key = spec["primary_key"]
    for i, row in enumerate(rows, 1):
        where = f"{table}[{i}] {row.get(key, '?')}"
        for e in validator.iter_errors(row):
            errors.append(f"{where}: {'/'.join(map(str, e.absolute_path)) or '<row>'}: {e.message}")
        if row.get(key) in seen:
            errors.append(f"{where}: duplicate {key}")
        seen.add(row.get(key))
        precision = row.get("date_precision")
        if precision and row.get("date") and not re.fullmatch(PRECISION[precision], row["date"]):
            errors.append(f"{where}: date {row['date']} does not have {precision} precision")
    if [r.get(key) for r in rows] != sorted(r.get(key) for r in rows):
        errors.append(f"{table}: rows are not sorted by {key}")
    return errors


def local_findings(rows):
    """Compare stored hashes with the local stores; missing stores are reported, not failed."""
    findings = []
    inventory = {}
    root = None
    if INVENTORY.exists():
        with closing(sqlite3.connect(INVENTORY)) as db:
            root = db.execute("SELECT value FROM metadata WHERE key = 'root'").fetchone()[0]
            inventory = dict(db.execute("SELECT relative_path, blake3 FROM files"))
    for row in rows:
        if "local_path" not in row:
            continue
        sid, path = row["source_id"], row["local_path"]
        if row["store"] == "bitsavers_mirror":
            if not inventory:
                findings.append(f"{sid}: no document inventory to check {path}")
            elif path not in inventory:
                findings.append(f"{sid}: {path} not in inventory under {root}")
            elif row.get("hash_algo") == "blake3" and inventory[path] != row["hash"]:
                findings.append(f"{sid}: inventory BLAKE3 differs for {path}")
        else:
            local = Path(path)
            if not local.exists():
                findings.append(f"{sid}: missing {path}")
            elif row.get("hash_algo") == "sha256" and sha256(local) != row["hash"]:
                findings.append(f"{sid}: SHA-256 differs for {path}")
            elif row.get("hash_algo") == "blake3":
                from blake3 import blake3

                if blake3(local.read_bytes()).hexdigest() != row["hash"]:
                    findings.append(f"{sid}: BLAKE3 differs for {path}")
    return findings


def foreign_key_errors(schema, tables):
    """Every referenced ID exists; a target of '@field' names the table in that row field."""
    keys = {name: {r[spec["primary_key"]] for r in tables[name]} for name, spec in schema["x-tables"].items()}
    errors = []
    for name, spec in schema["x-tables"].items():
        pk = spec["primary_key"]
        for column, target in spec.get("foreign_keys", {}).items():
            for row in tables[name]:
                values = row.get(column)
                values = values if isinstance(values, list) else [] if values is None else [values]
                table = row.get(target[1:]) if target.startswith("@") else target
                for value in values:
                    if value not in keys.get(table, set()):
                        errors.append(f"{name} {row[pk]}: {column} {value} not found in {table}")
    return errors


def validate(root=CURATED, check_local=False):
    schema, tables = load_tables(root)
    errors, findings = [], []
    for name, spec in schema["x-tables"].items():
        errors += row_errors(name, spec, tables[name], row_validator(schema, spec["row"]))
        if check_local:
            findings += local_findings(tables[name])
    errors += foreign_key_errors(schema, tables)
    return schema, tables, errors, findings


def column_type(prop):
    kind = prop.get("type")
    return {"integer": "INTEGER", "number": "REAL"}.get(kind, "TEXT")


def resolve(schema, prop):
    while "$ref" in prop:
        prop = schema["$defs"][prop["$ref"].rsplit("/", 1)[-1]]
    return prop


def build(root=CURATED, database=DATABASE):
    schema, tables, errors, _ = validate(root)
    if errors:
        raise ValueError(f"{len(errors)} validation errors; run `cpushowspeed data validate`")
    database.parent.mkdir(parents=True, exist_ok=True)
    partial = database.with_name(database.name + ".partial")
    partial.unlink(missing_ok=True)
    with closing(sqlite3.connect(partial)) as db:
        db.execute("CREATE TABLE _meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        meta = {"schema_version": schema["x-schema-version"], "schema_sha256": sha256(root / "schema.json")}
        for name, spec in schema["x-tables"].items():
            row_schema = resolve(schema, {"$ref": spec["row"]})
            props = row_schema["properties"]
            columns = []
            for column, prop in props.items():
                prop = resolve(schema, prop)
                nested = prop.get("type") in ("array", "object")
                suffix = " PRIMARY KEY" if column == spec["primary_key"] else ""
                columns.append(f'"{column}" {"TEXT" if nested else column_type(prop)}{suffix}')
            db.execute(f'CREATE TABLE "{name}" ({", ".join(columns)})')
            placeholders = ", ".join("?" for _ in props)
            db.executemany(
                f'INSERT INTO "{name}" VALUES ({placeholders})',
                [
                    [json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for v in (r.get(c) for c in props)]
                    for r in tables[name]
                ],
            )
            meta[f"table:{name}:rows"] = str(len(tables[name]))
            meta[f"table:{name}:sha256"] = sha256(root / spec["file"])
        from cpushowspeed.database.processor_identity import build_resolution
        from cpushowspeed.database.system_identity import build_systems

        meta.update(build_resolution(db, tables))
        meta.update(build_systems(db, tables))
        from cpushowspeed.database.dates import build_chronology
        from cpushowspeed.database.reviews import build_reviews

        meta.update(build_reviews(db, tables))

        meta.update(build_chronology(db, tables))
        from cpushowspeed.database.observations import build_observations

        meta.update(build_observations(db, tables))
        db.executemany("INSERT INTO _meta VALUES (?, ?)", sorted(meta.items()))
        db.commit()
    partial.replace(database)
    return meta


def write_jsonl(path, rows):
    """Deterministic curated JSONL: one row per line, schema field order preserved by the caller."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, separators=(", ", ": ")) + "\n" for r in rows))


@click.group("data")
def data():
    """Curated data tables (docs/data-schema.md)."""


@data.command("validate")
@click.option("--root", type=click.Path(path_type=Path, file_okay=False), default=CURATED, show_default=True)
@click.option("--check-local", is_flag=True, help="Also compare stored hashes with local stores and the document inventory.")
def validate_command(root, check_local):
    """Validate every curated table against schema.json; exit nonzero on errors."""
    try:
        schema, tables, errors, findings = validate(root, check_local)
    except (OSError, ValueError, jsonschema.SchemaError) as exc:
        raise click.ClickException(str(exc)) from exc
    for line in errors + findings:
        click.echo(line, err=True)
    json.dump(
        dict(
            valid=not errors,
            tables={k: len(v) for k, v in tables.items()},
            errors=len(errors),
            local_findings=len(findings) if check_local else None,
        ),
        sys.stdout,
    )
    click.echo()
    if errors:
        sys.exit(1)


@data.command("build")
@click.option("--root", type=click.Path(path_type=Path, file_okay=False), default=CURATED, show_default=True)
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
def build_command(root, database):
    """Validate, then write the SQLite database from curated tables."""
    try:
        meta = build(root, database)
    except (OSError, ValueError, jsonschema.SchemaError) as exc:
        raise click.ClickException(str(exc)) from exc
    json.dump(dict(database=str(database), **meta), sys.stdout, indent=2)
    click.echo()
