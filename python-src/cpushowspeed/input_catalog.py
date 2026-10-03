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


# Printed unit -> metric unit. Dhrystone 1 DMIPS = 1757 Dhrystones/s (VAX-11/780, VMS).
CONVERSIONS = {
    ("Dhrystones/s", "DMIPS"): ("dhrystones-per-second-to-dmips", 1 / 1757),
    ("KWIPS", "MWIPS"): ("kwips-to-mwips", 1 / 1000),
    ("KFLOPS", "MFLOPS"): ("kflops-to-mflops", 1 / 1000),
}


def curated_observations():
    """Hand-transcribed `calibration_input` rows of data/curated/observation.jsonl, one result per report column.

    A row's `reviewed_reading`, when present, replaces its printed value and unit (a wrong or incomplete printed label)."""
    from cpushowspeed.curated import CURATED

    metrics = {m["metric_id"]: m for m in map(json.loads, (CURATED / "metric.jsonl").read_text().splitlines())}
    sources = {s["source_id"]: s for s in map(json.loads, (CURATED / "source.jsonl").read_text().splitlines())}
    for row in map(json.loads, (CURATED / "observation.jsonl").read_text().splitlines()):
        if row["use"] != "calibration_input":
            continue
        metric, source, conditions = metrics[row["metric_id"]], sources[row["source_id"]], row["conditions"]
        reading = row.get("reviewed_reading") or dict(value=row["value"], unit=row["unit_printed"])
        if reading["unit"] == metric["unit"]:
            rule, factor = "none", 1.0
        else:
            rule, factor = CONVERSIONS[reading["unit"], metric["unit"]]
        yield observation(
            "reviewed-vector:" + row["observation_id"].removeprefix("cobs:"),
            row["metric_id"],
            reading["value"] * factor,
            result_id="reviewed-vector:" + row["result_id"].removeprefix("src:"),
            unit=metric["unit"],
            track=metric["track"],
            mode=metric["mode"],
            system=row["system"],
            source=dict(url=source["url"], locator=row["locator"], blake3=source.get("hash"), legacy_id=None),
            hardware=dict(
                processor=conditions.get("processor"),
                nominal_mhz=conditions.get("clock_mhz"),
                memory_mib=conditions.get("memory_mb"),
            ),
            run=dict(os=conditions.get("os"), compiler=conditions.get("compiler"), optimization=conditions.get("optimization")),
            evidence=row["measured_by"],
            verification=row["verification"],
            raw=dict(row, conversion=dict(rule=rule, factor=factor)),
        )


def richardson_dhrystone():
    """C-program rows of Richardson's Usenet Dhrystone lists, one result per row; 2.0 and 2.1 share one metric."""
    from cpushowspeed.usenet_results import richardson_dhrystone as rows
    from cpushowspeed.usenet_results import sources

    table = sources()
    for r in rows():
        if r["excluded"]:
            continue
        version = "1.1" if r["dhrystone_version"] == "1.1" else "2"
        metric = "Dhrystone:v1.1_DMIPS" if version == "1.1" else "Dhrystone:v2.1_DMIPS"
        source = table[r["source_id"]]
        identity = f"classical:richardson-dhrystone-{version}:{r['key']}"
        yield observation(
            identity,
            metric,
            r["dhrystones_per_second"] / 1757,
            unit="DMIPS",
            track="classical",
            mode="reported",
            system=" ".join(x for x in (r["manufacturer"], r["model"]) if x),
            source=dict(url=source["url"], locator=r["locator"], blake3=source["hash"], legacy_id=None),
            hardware=dict(processor=r["processor"] or None, nominal_mhz=r["clock_mhz"]),
            run=dict(os=r["os"], compiler=r["compiler"], optimization=r["options"], language="C"),
            evidence="historical_source_observation",
            verification="parsed_cross_checked",
            raw=dict(r, conversion=dict(rule="Dhrystones/s / 1757", factor=1 / 1757)),
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
    yield from curated_observations()
    yield from richardson_dhrystone()
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
