"""Shared observation contract and adapters; reported scores are never overwritten."""

import hashlib
import json
import math

from cpushowspeed.classic_values import linpack_n100, numeric

SCHEMA = "benchmark-observation-v2"


def classical_values(record, pages):
    """One owner for classical version/precision selection and LINPACK column parsing."""
    family, metrics = record["benchmark"], record["metrics_raw"]
    if family == "Dhrystone":
        return {"Dhrystone:" + k: numeric(metrics.get(k)) for k in ("v1.1_DMIPS", "v2.1_DMIPS") if numeric(metrics.get(k))}
    if family == "Whetstone":
        return {"Whetstone:" + k: numeric(metrics.get(k)) for k in ("MWIPS", "MWIPS_DP") if numeric(metrics.get(k))}
    if family == "LINPACK":
        score = linpack_n100(record, pages)
        return {"LINPACK:n100_MFLOPS": score} if score else {}
    return {}


def observation(
    identity,
    metric_id,
    value,
    *,
    unit,
    track,
    mode,
    system,
    source,
    result_id=None,
    hardware=None,
    execution=None,
    run=None,
    evidence="reported_measurement",
    verification="parsed_unreviewed",
    raw=None,
    qualification="",
):
    """One positive score per metric/mode; hardware capacity never fills execution counts.

    `result_id` names the reported result the score belongs to (one SPEC disclosure
    carries base and peak); chronology and reviews address results, not scores.
    `run` holds how the benchmark was run (OS, compiler, language, options), as text.
    """
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("observation must have a finite positive score")
    if not identity or not metric_id or not source.get("url"):
        raise ValueError("observation requires identity, metric and source URL")
    return dict(
        schema_version=SCHEMA,
        observation_id=hashlib.sha256(identity.encode()).hexdigest(),
        source_record_id=identity,
        result_id=result_id or identity,
        scope=":".join(identity.split(":")[:2]),
        metric_id=metric_id,
        value=value,
        unit=unit,
        track=track,
        mode=mode,
        system=system,
        hardware=hardware or {},
        run={k: v for k, v in (run or {}).items() if v not in (None, "")},
        execution=execution or dict(status="not_reported", observed_worker_count=None),
        evidence_class=evidence,
        verification=verification,
        source=source,
        raw=raw,
        qualification=qualification,
    )


def spec_observations(result):
    for mode in ("base", "peak"):
        value = getattr(result, mode)
        if value is None:
            continue
        legacy = result.generation == "cpu92"
        hardware = dict(
            processor=result.processor,
            nominal_mhz=result.clock_mhz,
            memory_mib=result.memory_mib,
            enabled_chips=None if legacy else result.chips,
            enabled_cores=result.cores,
            hardware_threads_per_core=result.enabled_threads_per_core,
            legacy_cpu_count=result.chips if legacy else None,
            count_basis="legacy_cpu_count_proxy" if legacy else "reported_enabled_hardware",
        )
        runtime = dict(result.execution.get("modes", {}).get(mode, {}))
        runtime.setdefault("status", result.execution.get("status", "not_collected"))
        runtime.setdefault("quantity", "copies" if result.track == "rate" else "threads")
        runtime["observed_worker_count"] = None
        runtime["benchmarks"] = [r for r in result.execution.get("execution", []) if r["mode"] == mode]
        runtime["source_url"] = result.execution.get("document_url") or result.execution.get("source_url")
        runtime["source_sha256"] = result.execution.get("source_sha256")
        yield observation(
            f"spec:{result.generation}:{result.track}:{result.result_id}:{mode}",
            f"{result.generation}:integer:{result.track}:{mode}",
            value,
            unit="native_suite_points",
            track=result.track,
            mode=mode,
            system=result.system,
            hardware=hardware,
            execution=runtime,
            result_id=f"spec:{result.generation}:{result.track}:{result.result_id}",
            run=dict(os=result.os, compiler=result.compiler),
            source=dict(url=result.source_url, sha256=result.source_container_sha256),
            raw=dict(
                score=result.raw_fields.get("Baseline" if mode == "base" else "Result")
                or result.raw_fields.get("Base Result" if mode == "base" else "Peak Result"),
                fields=result.raw_fields,
            ),
        )


def write_jsonl(path, records):
    """Stable JSONL, null for unknown quantities, no NaN or Python repr dictionaries."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count, seen = 0, set()
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w") as stream:
        for row in records:
            if row["schema_version"] != SCHEMA or row["observation_id"] in seen:
                raise ValueError("schema mismatch or duplicate observation identity")
            seen.add(row["observation_id"])
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n")
            count += 1
    temporary.replace(path)
    return count


def read_jsonl(path):
    with path.open() as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("schema_version") != SCHEMA or not math.isfinite(row["value"]) or row["value"] <= 0:
                raise ValueError("invalid canonical observation")
            yield row
