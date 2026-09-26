"""Validate the research relationship registry and render its human catalog."""

import json
from pathlib import Path

import click


def validate(registry, root):
    errors = []
    maps = {}
    for kind in ("tracks", "metrics", "datasets", "models"):
        items = registry[kind]
        maps[kind] = {r["id"]: r for r in items}
        if len(maps[kind]) != len(items):
            errors.append(f"duplicate {kind} IDs")

    def path_check(path, optional=False):
        target = (root / path).resolve()
        if not target.is_relative_to(root.resolve()):
            errors.append(f"path escapes repository: {path}")
        elif not optional and not target.exists():
            errors.append(f"missing required path: {path}")

    docs = {r["path"] for r in registry["documents"]}
    if len(docs) != len(registry["documents"]):
        errors.append("duplicate document paths")
    for d in registry["documents"]:
        path_check(d["path"])
    actual = {p.relative_to(root).as_posix() for folder in ("docs", "research") for p in (root / folder).rglob("*.md")}
    actual |= {p for p in ("README.md", "AGENTS.md") if (root / p).exists()}
    errors.extend(f"unregistered document: {p}" for p in sorted(actual - docs))
    for d in registry["datasets"]:
        path_check(d["path"], d["optional"])
        if d["owner"] not in docs:
            errors.append(f"unregistered dataset owner: {d['owner']}")
    for t in registry["tracks"]:
        path_check(t["path"])
    for m in registry["models"]:
        if m["track"] not in maps["tracks"]:
            errors.append(f"unknown track in {m['id']}")
        if m["owner"] not in docs:
            errors.append(f"unregistered model owner: {m['owner']}")
        for key, table, values in [
            ("metric", "metrics", m["input_metrics"] + [m["target_metric"]] + m.get("additional_target_metrics", [])),
            ("dataset", "datasets", m["dataset_ids"]),
            ("dependency", "models", m["depends_on"]),
        ]:
            for value in values:
                if value not in maps[table]:
                    errors.append(f"unknown {key} {value} in {m['id']}")
        for output in m["outputs"]:
            path_check(output["path"], output["optional"])
    visited, active = set(), set()

    def visit(key):
        if key in active:
            errors.append("model dependency cycle: " + key)
            return
        if key in visited or key not in maps["models"]:
            return
        active.add(key)
        for dep in maps["models"][key]["depends_on"]:
            visit(dep)
        active.remove(key)
        visited.add(key)

    for key in maps["models"]:
        visit(key)
    return errors


def render(registry):
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [
        "# Research catalog",
        "",
        "Generated from [model-registry.json](model-registry.json); edit the registry and run",
        "`cpushowspeed research render`. Paths in the JSON are relative to the repository root.",
        "Start with the [four-track overview](overview.md).",
        "",
        "## Metrics",
        "",
        "| ID | Meaning | Mode / unit | Status |",
        "| --- | --- | --- | --- |",
    ]
    for m in registry["metrics"]:
        lines.append("| " + " | ".join(map(cell, [m["id"], m["title"], m["mode"] + " / " + m["unit"], m["status"]])) + " |")
    lines += [
        "",
        "## Model relationships",
        "",
        "Arrows below express calculation dependencies. Shared datasets and source lineage",
        "are recorded separately in the JSON; edges do not establish independence.",
        "",
        "```mermaid",
        "flowchart TD",
    ]
    for m in registry["models"]:
        m_id = m["id"].replace("-", "_")
        lines.append(f'    {m_id}["{m["id"]}"]')
        for dep in m["depends_on"]:
            lines.append(f'    {dep.replace("-","_")} --> {m_id}')
    lines += [
        "```",
        "",
        "| Model / owner | Inputs → target | Relationship; role; status | Dependencies |",
        "| --- | --- | --- | --- |",
    ]
    for m in registry["models"]:
        lines.append(
            "| "
            + f'[{m["id"]}](../{m["owner"]})'
            + " | "
            + cell(", ".join(m["input_metrics"]) + " → " + m["target_metric"])
            + " | "
            + cell("; ".join([m["relationship"], m["role"], m["status"]]))
            + " | "
            + cell(", ".join(m["depends_on"]) or "none")
            + " |"
        )
    lines += ["", "## Datasets", "", "| ID | Owner | Path | Availability |", "| --- | --- | --- | --- |"]
    for d in registry["datasets"]:
        lines.append(
            f'| {d["id"]} | [guide](../{d["owner"]}) | `{d["path"]}` | '
            + ("optional derived input" if d["optional"] else "required in checkout")
            + " |"
        )
    lines += [
        "",
        "## Document inventory",
        "",
        "Reports stay at their existing paths to preserve citations. Role distinguishes current",
        "analysis from evidence, diagnostics and retired work.",
        "",
        "| Document | Role | Status |",
        "| --- | --- | --- |",
    ]
    for d in registry["documents"]:
        lines.append(f'| [{cell(d["title"])}](../{d["path"]}) | {d["role"]} | {d["status"]} |')
    return "\n".join(lines) + "\n"


@click.group("research")
def research():
    """Inspect and maintain the research metric/model/document registry."""


@research.command("validate")
@click.option(
    "--registry", type=click.Path(path_type=Path, exists=True), default=Path("research/model-registry.json"), show_default=True
)
def validate_command(registry):
    """Check local references, document coverage and model dependency cycles."""
    root = Path.cwd()
    value = json.loads(registry.read_text())
    errors = validate(value, root)
    click.echo(json.dumps(dict(valid=not errors, errors=errors, models=len(value["models"]), documents=len(value["documents"]))))
    if errors:
        raise click.exceptions.Exit(1)


@research.command("render")
@click.option(
    "--registry", type=click.Path(path_type=Path, exists=True), default=Path("research/model-registry.json"), show_default=True
)
@click.option("--output", type=click.Path(path_type=Path), default=Path("research/catalog.md"), show_default=True)
@click.option("--check", is_flag=True, help="Fail if the saved catalog differs; do not write.")
def render_command(registry, output, check):
    """Render the registry catalog (run from repository root)."""
    content = render(json.loads(registry.read_text()))
    if check:
        matches = output.exists() and output.read_text() == content
        click.echo(json.dumps(dict(current=matches, path=str(output))))
        if not matches:
            raise click.exceptions.Exit(1)
    else:
        output.write_text(content)
        click.echo(json.dumps(dict(path=str(output))))
