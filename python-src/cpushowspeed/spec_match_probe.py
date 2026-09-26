"""Processor-level SPEC overlap coverage without accepting candidate matches."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import click
from cpushowspeed.spec_fit import GENERATIONS, Result, collect_speed

METHOD_VERSION = "processor-overlap-probe-v1"
AMBIGUOUS_KEYS = {"xeon", "opteron", "epyc", "pentium", "athlon"}


def _same_configuration_clues(old: Result, new: Result) -> bool:
    if old.clock_mhz is None or new.clock_mhz is None or abs(old.clock_mhz / new.clock_mhz - 1) > 0.01:
        return False
    if old.chips != new.chips:
        return False
    if old.cores is not None and new.cores is not None and old.cores != new.cores:
        return False
    if (
        old.enabled_threads_per_core is not None
        and new.enabled_threads_per_core is not None
        and old.enabled_threads_per_core != new.enabled_threads_per_core
    ):
        return False
    return True


def probe_processor_overlap(raw_dir: Path, output: Path) -> dict[str, object]:
    results = collect_speed(raw_dir)
    by_cpu: dict[str, dict[str, list[Result]]] = {}
    for generation, records in results.items():
        keyed: dict[str, list[Result]] = {}
        for record in records:
            if record.processor_key and record.processor_key not in AMBIGUOUS_KEYS:
                keyed.setdefault(record.processor_key, []).append(record)
        by_cpu[generation] = keyed
    input_hashes = {
        generation: hashlib.sha256(
            "\n".join(sorted(f"{row.source_url} {row.source_container_sha256}" for row in results[generation])).encode()
        ).hexdigest()
        for generation in GENERATIONS
    }
    rows: list[dict[str, object]] = []
    for old, new in zip(GENERATIONS, GENERATIONS[1:]):
        shared = sorted(by_cpu[old].keys() & by_cpu[new].keys())
        processor_only = 0
        same_clues = 0
        same_memory = 0
        for key in shared:
            for old_row in by_cpu[old][key]:
                for new_row in by_cpu[new][key]:
                    processor_only += 1
                    if not _same_configuration_clues(old_row, new_row):
                        continue
                    same_clues += 1
                    if old_row.memory_mib is not None and old_row.memory_mib == new_row.memory_mib:
                        same_memory += 1
        rows.append(
            {
                "method_version": METHOD_VERSION,
                "old_generation": old,
                "new_generation": new,
                "shared_processor_keys": len(shared),
                "processor_only_pairings": processor_only,
                "same_cpu_clock_chip_core_smt_pairings": same_clues,
                "plus_same_memory_pairings": "" if old == "cpu92" else same_memory,
                "old_input_manifest_sha256": input_hashes[old],
                "new_input_manifest_sha256": input_hashes[new],
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    processor_generations: dict[str, set[str]] = {}
    for generation, keyed in by_cpu.items():
        for key in keyed:
            processor_generations.setdefault(key, set()).add(generation)
    triples = {key: sorted(generations) for key, generations in processor_generations.items() if len(generations) >= 3}
    return {"output": str(output), "rows": len(rows), "processor_keys_in_three_or_more_suites": triples}


@click.command("match-coverage")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path("research/data/spec/fitting/processor-match-coverage.csv"),
    show_default=True,
)
def match_coverage_command(raw_dir: Path, output: Path) -> None:
    """Count processor-level overlap candidates without accepting them as bridges."""
    try:
        result = probe_processor_overlap(raw_dir, output)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
