"""Export all active source adapters into the same observation envelope."""

import hashlib
import json
from pathlib import Path

import click
from cpushowspeed.benchmark_records import (
    classical_values,
    observation,
    spec_observations,
)
from cpushowspeed.classic_values import numeric
from cpushowspeed.research_io import read_csv
from cpushowspeed.spec_inputs import (
    collect_cpu92_rate,
    collect_integer,
    collect_speed92,
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


SPEC89_PACKAGE = Path("research/data/spec89/v2.0.0")


def package_source(record):
    """SPEC89 package rows cite a package source ID and, for saved messages, the saved bytes."""
    raw = record.get("raw_record") if isinstance(record.get("raw_record"), dict) else {}
    found = {}
    if raw.get("source_id"):
        found["legacy_id"] = "spec89/v2.0.0/sources:" + raw["source_id"]
    if raw.get("source_file"):
        path = next(p for p in (Path(raw["source_file"]), SPEC89_PACKAGE / raw["source_file"]) if p.exists())
        found["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def historical_observation(record, metric, score, prefix):
    """One source row or report column is one result; each of its metrics is one observation."""
    return observation(
        prefix + ":" + record["id"] + ":" + metric,
        metric,
        score,
        result_id=prefix + ":" + record["id"],
        unit=score_unit(metric),
        track="rate" if "SPECrate" in metric else "speed" if metric.startswith("SPEC") else "classical",
        mode="base" if "base" in metric.lower() else "reported",
        system=record.get("system") or record.get("machine"),
        source=dict(
            dict(
                url=record["source_url"],
                locator=record.get("locator") or record.get("pdf_page"),
                sha256=record.get("source_container_sha256") or record.get("source_sha256"),
                blake3=record.get("source_blake3") or record.get("pdf_blake3"),
            ),
            **package_source(record),
        ),
        hardware=dict(
            processor=record.get("processor_raw"),
            nominal_mhz=record.get("clock_mhz"),
            legacy_cpu_count=record.get("cpu_count") or record.get("reported_processor_count"),
        ),
        run=dict(
            os=record.get("os_raw") or record.get("os"),
            language=record.get("language_raw"),
            optimization=record.get("optimization_raw"),
        ),
        evidence=record.get("evidence_class") or record.get("evidence_kind") or "historical_source_observation",
        raw=record,
        qualification=record.get("qualification", ""),
    )


def spec89_bridges():
    """SPEC89 package rows reporting SPEC89 and SPEC92 values for one system in one source."""
    import csv

    path = SPEC89_PACKAGE / "csv" / "bridges89_92.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            yield dict(
                id="spec89-bridge:" + row["bridge_id"],
                system=row["system"],
                os_raw=row["operating_system"],
                source_url=row["source_url"],
                locator=row["page_table"],
                qualification=row["notes"],
                evidence_class="contemporary_collector",
                raw_record=row,
                **{k: row[k] for k in ("SPECmark89", "SPECint89", "SPECfp89", "SPECint92", "SPECfp92")},
            )


def dec_vectors():
    """DEC N3909 report columns: classical scores and SPEC targets measured for one machine."""
    from cpushowspeed.classic_source_data import source_vectors

    root = Path("research/data/classic/pdf-extraction")
    tables = [json.loads(line) for line in (root / "tables.jsonl").read_text().splitlines()]
    return source_vectors(tables, read_csv(root / "dec-interpreted.csv"))[0]


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
        if r["cohort"] == "SPEC92 rate Netlib":
            continue  # the same Netlib pages are the spec:cpu92 rate results
        for metric, score in r["metrics_raw"].items():
            try:
                value = float(score)
            except (ValueError, TypeError):
                continue
            if value > 0:
                yield historical_observation(r, metric, value, "historical-spec")
    for r in spec89_bridges():
        for metric in ("SPECmark89", "SPECint89", "SPECfp89", "SPECint92", "SPECfp92"):
            if numeric(r[metric]):
                yield historical_observation(r, metric, numeric(r[metric]), "historical-spec")
    for r in dec_vectors():
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
