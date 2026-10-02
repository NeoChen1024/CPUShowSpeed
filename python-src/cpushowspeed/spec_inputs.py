"""Single source adapter for SPEC numeric fields, identities and execution metadata."""

import csv
import hashlib
import json
import re
import statistics
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from cpushowspeed import spec92_disclosure
from cpushowspeed.input_context import ACTIVE_CATALOG, load_catalog
from cpushowspeed.spec92_rate import BENCHMARKS, _checked
from cpushowspeed.spec_disclosure import load_disclosure
from cpushowspeed.spec_overlap import (
    Result,
    _checked_bulk,
    _frequency,
    _memory_mib,
    _normalized,
    _positive,
    _processor_key,
    _source_url,
)

GENERATIONS = ("cpu95", "cpu2000", "cpu2006", "cpu2017", "cpu2026")
MODES = ("base", "peak")


@lru_cache(None)
def _live_disclosure(raw_dir, url, generation, track):
    return load_disclosure(Path(raw_dir), url, generation, track)


def disclosure(raw_dir, url, generation, track):
    if ACTIVE_CATALOG.get() is not None:
        return load_catalog(str(ACTIVE_CATALOG.get()))["_spec_index"][url, track]["execution"]
    return _live_disclosure(raw_dir, url, generation, track)


def enrich(result, raw_dir, track, raw_fields=None, execution=None):
    if execution is None:
        execution = disclosure(raw_dir, result.source_url, result.generation, track)
    return replace(result, track=track, execution=execution, raw_fields=raw_fields or {})


def collect_integer(raw_dir: Path, track: str) -> dict[str, list[Result]]:
    """Read either metric family without changing reported scores or rate defaults."""
    if ACTIVE_CATALOG.get() is not None:
        all_records = load_catalog(str(ACTIVE_CATALOG.get()))["spec"]
        return {g: [Result(**r) for r in all_records if r["track"] == track and r["generation"] == g] for g in GENERATIONS}
    if track not in {"speed", "rate"}:
        raise ValueError(f"unknown SPEC track: {track}")
    results: dict[str, list[Result]] = {}
    for generation in GENERATIONS:
        rows, digest = _checked_bulk(raw_dir / generation / "bulk.csv")
        selected: list[Result] = []
        seen: set[str] = set()
        for raw in rows:
            if raw["Benchmark"] != "CINT" + generation[3:] + ("rate" if track == "rate" else ""):
                continue
            peak = _positive(raw.get("Result") or raw.get("Peak Result"))
            base = _positive(raw.get("Baseline") or raw.get("Base Result"))
            if peak is None and base is None:
                continue
            processor = raw.get("Processor") or raw.get("CPU") or ""
            chips = raw.get("# chips") or raw.get("# Chips") or ""
            if not processor or not chips.isdigit():
                continue
            url = _source_url(raw["Disclosure"])
            result_id = url.split("/results/", 1)[1].removesuffix(".html")
            if result_id in seen:
                raise ValueError(f"duplicate {generation} integer-{track} result: {result_id}")
            seen.add(result_id)
            cores = raw.get("# Cores") or raw.get("# cores") or ""
            threads = raw.get("# Enabled Threads Per Core") or raw.get("# Threads Per Core") or ""
            selected.append(
                Result(
                    generation,
                    result_id,
                    raw["System"],
                    _normalized(raw["System"]),
                    processor,
                    _processor_key(processor),
                    int(chips),
                    int(cores) if cores.isdigit() else None,
                    int(threads) if threads.isdigit() else None,
                    _frequency(raw, processor),
                    _memory_mib(raw.get("Memory", "")),
                    raw.get("Operating System") or raw.get("Op. Sys.") or "",
                    raw.get("Compiler", ""),
                    peak,
                    base,
                    url,
                    digest,
                    track=track,
                    raw_fields=raw,
                    execution=disclosure(raw_dir, url, generation, track),
                )
            )
        results[generation] = selected
    return results


def collect_cpu92_rate(path: Path, raw_dir: Path | None = None) -> list[Result]:
    """Load checked Netlib-derived records, retaining each original detail URL/hash."""
    if ACTIVE_CATALOG.get() is not None:
        return [
            Result(**r)
            for r in load_catalog(str(ACTIVE_CATALOG.get()))["spec"]
            if r["generation"] == "cpu92" and r["track"] == "rate"
        ]
    results = []
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if raw_dir is not None:
                source_path = raw_dir / "cpu92" / "netlib" / "rate" / "details" / Path(urlparse(row["source_url"]).path).name
                actual = hashlib.sha256(source_path.read_bytes()).hexdigest()
                meta = json.loads(source_path.with_name(source_path.name + ".meta.json").read_text())
                if actual != row["source_sha256"] or actual != meta.get("sha256") or row["source_url"] != meta.get("source_url"):
                    raise ValueError(f"CPU92 source identity mismatch: {source_path}")
            processor = row["processor"]
            results.append(
                Result(
                    "cpu92",
                    row["source_url"].rsplit("/", 1)[-1],
                    row["system"],
                    _normalized(row["system"]),
                    processor,
                    _processor_key(processor),
                    int(row["cpu_count"]),
                    None,
                    None,
                    _frequency({"System": row["system"]}, processor),
                    float(row["memory_mib"]) if row["memory_mib"] else None,
                    row["os"],
                    row["compiler"],
                    float(row["peak_score"]),
                    float(row["base_score"]) if row["base_score"] else None,
                    row["source_url"],
                    row["source_sha256"],
                    track="rate",
                    raw_fields=row,
                    execution=dict(
                        status="parsed",
                        source_url=row["source_url"],
                        source_sha256=row["source_sha256"],
                        modes={
                            mode: dict(
                                quantity="copies",
                                status="reported" if row.get(mode + "_copies_min") else "not_reported_in_parsed_table",
                                minimum=int(row[mode + "_copies_min"]) if row.get(mode + "_copies_min") else None,
                                maximum=int(row[mode + "_copies_max"]) if row.get(mode + "_copies_max") else None,
                            )
                            for mode in MODES
                        },
                    ),
                )
            )
    return results


def parse_speed92(document, url, digest):
    """Check six reported ratios before accepting a CPU92 integer speed result; keep every disclosed field."""
    page = spec92_disclosure.parse(document)
    if page["metric_heading"] != "SPECint92":
        raise ValueError(f"not an integer speed disclosure: {page['metric_heading']}")
    means = page["reported_means"]
    peak = None if means.get("SPECint92", "-") == "-" else float(means["SPECint92"])
    base = float(means["SPECbase_int92"]) if means.get("SPECbase_int92", "-") != "-" else None
    rows = {row[0]: row[1:] for row in page["table"]}
    if sorted(rows) != sorted(BENCHMARKS) or len(page["table"]) != len(BENCHMARKS):
        raise ValueError("benchmark rows missing or repeated")
    ratios = []
    for name in BENCHMARKS:
        values = [None if x == "-" else float(x) for x in rows[name]]
        if len(values) not in ((4,) if base is not None else (2, 3)) or any(x is not None and x <= 0 for x in values):
            raise ValueError(f"invalid speed columns: {name}")
        ratios.append(values[-2:] if base is not None else [values[-1], None])
    for mode, score, index in (("peak", peak, 0), ("base", base, 1)):
        if any((r[index] is None) != (score is None) for r in ratios):
            raise ValueError(f"{mode} summary/benchmark availability mismatch")
        if score is not None and abs(statistics.geometric_mean(r[index] for r in ratios) - score) > 0.2:
            raise ValueError(f"{mode} summary disagrees with six rounded ratios")
    fields = page["fields"]
    system, processor = page["system"], fields["CPU"]
    chips = re.match(r"\d+", fields["Number of CPUs"])
    if chips is None:
        raise ValueError("missing CPU count")
    raw = dict(
        company=page["company"],
        volume=page["volume"],
        issue=page["issue"],
        publication_month=page["publication_month"],
        hardware_availability_month=page["hardware_availability_month"],
        software_availability_month=page["software_availability_month"],
        test_month=page["test_month"],
        reported_means=means,
        table=page["table"],
        notes=page["notes"],
        **fields,
    )
    return Result(
        "cpu92",
        url.rsplit("/", 1)[-1],
        system,
        _normalized(system),
        processor,
        _processor_key(processor),
        int(chips[0]),
        None,
        None,
        _frequency({"System": system}, processor),
        _memory_mib(fields["Memory"]),
        fields["O/S & Version"],
        fields["Compilers & Version"],
        peak,
        base,
        url,
        digest,
        track="speed",
        execution=dict(status="parsed", modes={m: dict(quantity="threads", status="not_reported_in_parsed_table") for m in MODES}),
        raw_fields=raw,
    )


def collect_speed92(raw):
    if ACTIVE_CATALOG.get() is not None:
        records = [
            Result(**r)
            for r in load_catalog(str(ACTIVE_CATALOG.get()))["spec"]
            if r["generation"] == "cpu92" and r["track"] == "speed"
        ]
        return records, [
            dict(source_url=r.source_url, sha256=r.source_container_sha256, status="included", reason="validated_input_snapshot")
            for r in records
        ]
    records, audit = [], []
    summaries = {}
    for path in sorted((raw / "cpu92/netlib").glob("spec*.cint92.*.col0.html")):
        meta = json.loads(path.with_name(path.name + ".meta.json").read_text())
        body, digest = _checked(path, meta["source_url"])
        mode = "base" if path.name.startswith("specbase.") else "peak"
        for name, score in re.findall(r'(spec\.[^/"#]+\.notes\.html)[^>]*>.*?</A>\s*([0-9.]+)', body, re.I):
            summaries.setdefault((name, mode), []).append((float(score), meta["source_url"], digest))
    for path in sorted((raw / "cpu92/netlib/details").glob("*.cint92.*.html")):
        meta = json.loads(path.with_name(path.name + ".meta.json").read_text())
        # Hash/identity failures are fatal; unsupported document layouts are audited.
        body, digest = _checked(path, meta["source_url"])
        try:
            result = parse_speed92(body, meta["source_url"], digest)
        except ValueError as exc:
            audit.append(dict(source_url=meta["source_url"], sha256=digest, status="excluded", reason=str(exc)))
        else:
            checked = []
            for mode in MODES:
                score = getattr(result, mode)
                entries = summaries.get((path.name, mode), [])
                if score is not None and entries:
                    if any(value != score for value, _, _ in entries):
                        raise ValueError(f"CPU92 {mode} summary/detail mismatch: {path}")
                    checked.extend(dict(mode=mode, url=url, sha256=sha) for _, url, sha in entries)
            records.append(result)
            audit.append(
                dict(
                    source_url=meta["source_url"],
                    sha256=digest,
                    status="included",
                    reason="six_ratios_checked",
                    summary_checks=json.dumps(checked, sort_keys=True),
                )
            )
    return records, audit


def runtime_fingerprint(raw):
    """Freeze discovery of missing as well as present detail files in a saved model."""
    if ACTIVE_CATALOG.get() is not None:
        return load_catalog(str(ACTIVE_CATALOG.get()))["_manifest"]["runtime_fingerprint"]
    entries = []
    for generation in (*GENERATIONS, "cpu92"):
        for path in sorted((Path(raw) / generation).rglob("*")):
            if path.suffix in (".html", ".csv") and path.name not in ("bulk.csv", "index.html"):
                entries.append((str(path.relative_to(raw)), hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
