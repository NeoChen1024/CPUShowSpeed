"""Join source-checked hardware introduction evidence to immutable SPEC89 observations."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import click

DEFAULT_AGGREGATE = Path("research/data/spec89/aggregate89-plus-helman.csv")
DEFAULT_CATALOG = Path("research/data/spec89/hardware-introductions.csv")
DEFAULT_OUTPUT = Path("data/derived/spec89/aggregate89-with-hardware-years.csv")


@click.command("hardware-years")
@click.option("--aggregate", type=click.Path(path_type=Path), default=DEFAULT_AGGREGATE, show_default=True)
@click.option("--catalog", type=click.Path(path_type=Path), default=DEFAULT_CATALOG, show_default=True)
@click.option("--output", type=click.Path(path_type=Path), default=DEFAULT_OUTPUT, show_default=True)
def hardware_years_command(aggregate: Path, catalog: Path, output: Path) -> None:
    """Join documented model years to SPEC89 rows; leave unresolved dates blank."""
    try:
        result = build_hardware_years(aggregate, catalog, output)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))


def build_hardware_years(aggregate: Path, catalog: Path, output: Path) -> dict[str, object]:
    with aggregate.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        source_fields = reader.fieldnames
        observations = list(reader)
    if not source_fields or not observations:
        raise ValueError("SPEC89 aggregate is empty")
    with catalog.open(encoding="utf-8-sig", newline="") as stream:
        catalog_rows = list(csv.DictReader(stream))
    by_name: dict[str, dict[str, str]] = {}
    for item in catalog_rows:
        name = item["system_normalized"]
        if not name or name in by_name:
            raise ValueError(f"empty or duplicate hardware name: {name!r}")
        date, year, status = item["hardware_introduced_at"], item["hardware_introduction_year"], item["status"]
        if status == "source_checked":
            if not date or not year or date[:4] != year or not item["source_url"] or not item["source_locator"]:
                raise ValueError(f"incomplete source-checked hardware date: {name}")
        elif status == "unresolved":
            if date or year:
                raise ValueError(f"unresolved model has assigned hardware date: {name}")
        else:
            raise ValueError(f"unknown catalog status for {name}: {status}")
        by_name[name] = item
    names = {row["system_normalized"] for row in observations}
    if names != set(by_name):
        raise ValueError(f"catalog model mismatch: missing={sorted(names - set(by_name))}, extra={sorted(set(by_name) - names)}")
    counts = Counter(row["system_normalized"] for row in observations)
    for name, item in by_name.items():
        if item["observations"] != str(counts[name]):
            raise ValueError(f"catalog observation count differs for {name}")
    if len({row["record_id"] for row in observations}) != len(observations):
        raise ValueError("duplicate SPEC89 record_id")
    extra_fields = [
        "hardware_introduced_at",
        "hardware_introduction_year",
        "hardware_date_event_type",
        "hardware_date_status",
        "hardware_date_source_url",
        "hardware_date_source_locator",
        "hardware_date_reviewed_on",
        "hardware_date_notes",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[*source_fields, *extra_fields])
        writer.writeheader()
        for row in observations:
            item = by_name[row["system_normalized"]]
            writer.writerow(
                {
                    **row,
                    "hardware_introduced_at": item["hardware_introduced_at"],
                    "hardware_introduction_year": item["hardware_introduction_year"],
                    "hardware_date_event_type": item["event_type"],
                    "hardware_date_status": item["status"],
                    "hardware_date_source_url": item["source_url"],
                    "hardware_date_source_locator": item["source_locator"],
                    "hardware_date_reviewed_on": item["reviewed_on"],
                    "hardware_date_notes": item["notes"],
                }
            )
    dated = sum(bool(by_name[row["system_normalized"]]["hardware_introduction_year"]) for row in observations)
    return {
        "output": str(output),
        "models": len(names),
        "dated_models": sum(bool(item["hardware_introduction_year"]) for item in by_name.values()),
        "unresolved_models": sum(not item["hardware_introduction_year"] for item in by_name.values()),
        "observations": len(observations),
        "dated_observations": dated,
    }
