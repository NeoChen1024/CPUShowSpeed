"""Explicit hardware/runtime resource provenance for timeline records."""

from functools import lru_cache
from pathlib import Path

from cpushowspeed.spec_inputs import disclosure

RAW = Path("data/raw/spec")


@lru_cache(None)
def detail(url, generation, track):
    return disclosure(RAW, url, generation, track)


def resource_fields(row, raw, track):
    """Add declared resources without revising scores or inventing CPU topology."""
    generation, mode = row["generation"], row["mode"]
    runtime = dict(track=track, quantity="copies" if track == "rate" else "threads", status="not_collected")
    result = dict(
        cores_per_chip=raw.get("# Cores Per Chip") or raw.get("# cores per chip") or "",
        resource_basis="reported enabled hardware; not benchmark concurrency",
        hardware_context={
            k: v
            for k, v in raw.items()
            if v
            and (
                "Cache" in k
                or k
                in (
                    "Memory",
                    "Processor Characteristics",
                    "CPU(s) Orderable",
                    "Parallel",
                    "Auto Parallelization",
                    "Base Pointer Size",
                    "Peak Pointer Size",
                    "Compiler",
                    "Compiler Category",
                )
            )
        },
    )
    try:
        if int(row.get("cores") or 0) > int(row.get("chips") or 0) * int(result["cores_per_chip"]):
            result["resource_warning"] = "Source reports more enabled cores than chip capacity; topology requires review."
    except (ValueError, TypeError):
        pass
    if generation == "cpu92":
        result.update(resource_basis="legacy reported CPU count; chip equivalence unverified", reported_cpu_count=raw["cpu_count"])
        lo, hi = raw.get(mode + "_copies_min"), raw.get(mode + "_copies_max")
        runtime.update(
            status="reported" if lo else "not_reported_in_parsed_table",
            minimum=lo,
            maximum=hi,
            source_url=row["source_url"],
            source_sha256=raw.get("source_sha256", ""),
        )
    else:
        parsed = detail(row["source_url"], generation, track)
        if parsed["status"] == "parsed":
            runtime.update(
                parsed["modes"][mode],
                source_url=parsed["document_url"],
                source_sha256=parsed["source_sha256"],
                benchmarks=[r for r in parsed["execution"] if r["mode"] == mode],
            )
            result["hardware_context"]["detail_enabled"] = parsed["hardware_raw"].get("enabled", "")
            result["hardware_context"]["detail_max_mhz"] = parsed["hardware_raw"].get("max_mhz", "")
    result["runtime_resources"] = runtime
    if track == "rate" and runtime["status"] == "reported":
        result.update(copies_min=runtime["minimum"], copies_max=runtime["maximum"])
    return result
