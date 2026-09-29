"""Export all active source adapters into the same observation envelope."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import click
from cpushowspeed.benchmark_records import (
    SCHEMA,
    classical_values,
    observation,
    spec_observations,
    write_jsonl,
)
from cpushowspeed.research_io import code_hashes, read_csv
from cpushowspeed.spec_inputs import (
    collect_cpu92_rate,
    collect_integer,
    collect_speed92,
    runtime_fingerprint,
)


def score_unit(metric):
    if "DMIPS" in metric:
        return "DMIPS"
    if "MWIPS" in metric:
        return "MWIPS"
    if "MFLOPS" in metric:
        return "MFLOPS"
    if "KIPS" in metric:
        return "KIPS"
    return "native_suite_points"


def historical_observation(record, metric, score, prefix):
    return observation(
        prefix + ":" + record["id"] + ":" + metric,
        metric,
        score,
        unit=score_unit(metric),
        track="rate" if "SPECrate" in metric else "speed" if metric.startswith("SPEC") else "classical",
        mode="base" if "base" in metric.lower() else "reported",
        system=record.get("system") or record.get("machine"),
        source=dict(
            url=record["source_url"],
            locator=record.get("locator") or record.get("pdf_page"),
            sha256=record.get("source_container_sha256") or record.get("source_sha256"),
            blake3=record.get("source_blake3") or record.get("pdf_blake3"),
        ),
        hardware=dict(
            processor=record.get("processor_raw"),
            nominal_mhz=record.get("clock_mhz"),
            legacy_cpu_count=record.get("cpu_count") or record.get("reported_processor_count"),
        ),
        software=dict(os=record.get("os_raw") or record.get("os")),
        evidence=record.get("evidence_class") or record.get("evidence_kind") or "historical_source_observation",
        raw=record,
        qualification=record.get("qualification", ""),
    )


def records(raw):
    for track in ("rate", "speed"):
        for group in collect_integer(raw, track).values():
            for result in group:
                yield from spec_observations(result)
    for result in collect_cpu92_rate(Path("data/derived/spec/cpu92-rate/cpu92-rate-records.csv"), raw):
        yield from spec_observations(result)
    for result in collect_speed92(raw)[0]:
        yield from spec_observations(result)
    pages = Path("data/derived/classic/netlib-linpack-report.txt").read_text().split("\f")
    for line in Path("data/derived/classic/overlap-spec/classical-records.jsonl").read_text().splitlines():
        r = json.loads(line)
        for metric, score in classical_values(r, pages).items():
            yield historical_observation(r, metric, score, "classical")
    for line in Path("data/derived/classic/overlap-spec/spec-records.jsonl").read_text().splitlines():
        r = json.loads(line)
        for metric, score in r["metrics_raw"].items():
            try:
                value = float(score)
            except (ValueError, TypeError):
                continue
            if value > 0:
                yield historical_observation(r, metric, value, "historical-spec")
    for line in Path("data/derived/classic/source-pair-fit/vectors.jsonl").read_text().splitlines():
        r = json.loads(line)
        for metric, score in {**r["scores"], **r["targets"]}.items():
            yield historical_observation(r, metric, score, "reviewed-vector")
    for row in read_csv(Path("data/derived/classic/mix-study/mix-records.csv")):
        if not row.get("kips"):
            continue
        metric = "InstructionMix:" + {"Gibson Mix": "Gibson", "ADP Mix": "ADP"}[row["mix"]] + "_KIPS"
        yield observation(
            "mix:" + row["mix_id"],
            metric,
            row["kips"],
            unit="KIPS",
            track="instruction_mix",
            mode="reported",
            system=row["system"],
            source=dict(url=row["source_url"], locator=row["source_locator"], sha256=row["source_snapshot_sha256"]),
            evidence=row["evidence_kind"],
            raw=row,
            qualification=row["fit_eligible"],
        )


@click.group("inputs")
def inputs():
    """Shared source-normalization and input contracts."""


@inputs.command("build")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/inputs"), show_default=True)
def build(raw_dir, output):
    """Write one versioned JSONL observation format for active SPEC/classical/mix inputs."""
    from cpushowspeed.input_context import ACTIVE_CATALOG

    if ACTIVE_CATALOG.get() is not None:
        raise click.ClickException("inputs build requires raw adapters, not --input-catalog")
    count = write_jsonl(output / "observations.jsonl", records(raw_dir))
    with (output / "sources.jsonl").open("w") as stream:

        def emit(view, record):
            stream.write(json.dumps(dict(schema_version="benchmark-source-v1", view=view, record=record), allow_nan=False) + "\n")

        for track in ("rate", "speed"):
            for group in collect_integer(raw_dir, track).values():
                for r in group:
                    emit("spec", asdict(r))
        for r in collect_cpu92_rate(Path("data/derived/spec/cpu92-rate/cpu92-rate-records.csv"), raw_dir):
            emit("spec", asdict(r))
        for r in collect_speed92(raw_dir)[0]:
            emit("spec", asdict(r))
        for view, path in (
            ("classical", "data/derived/classic/overlap-spec/classical-records.jsonl"),
            ("historical-spec", "data/derived/classic/overlap-spec/spec-records.jsonl"),
            ("vectors", "data/derived/classic/source-pair-fit/vectors.jsonl"),
        ):
            for line in Path(path).read_text().splitlines():
                emit(view, json.loads(line))
        for row in read_csv(Path("data/derived/classic/mix-study/mix-records.csv")):
            emit("mixes", row)
    audit = dict(
        schema=SCHEMA,
        runtime_fingerprint=runtime_fingerprint(raw_dir),
        files_sha256={
            name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in ("observations.jsonl", "sources.jsonl")
        },
        observations=count,
        code_sha256=code_hashes(__file__),
        qualification="Duplicate publications and source adapters remain distinct; do not pool blindly. Raw values retained; no fitting.",
    )
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(schema=SCHEMA, observations=count)))
