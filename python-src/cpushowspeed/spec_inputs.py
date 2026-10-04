"""Single source adapter for SPEC numeric fields, identities and execution metadata."""

import csv
import hashlib
import json
import re
import statistics
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlparse

from cpushowspeed import spec92_disclosure
from cpushowspeed.parallel import pmap
from cpushowspeed.spec92_rate import BENCHMARKS, read_checked_source
from cpushowspeed.spec_disclosure import load_disclosure
from cpushowspeed.spec_overlap import (
    Result,
    clock_mhz,
    disclosure_url,
    memory_mib,
    normalized,
    positive,
    processor_text_key,
    read_checked_bulk,
)

GENERATIONS = ("cpu95", "cpu2000", "cpu2006", "cpu2017", "cpu2026")
MODES = ("base", "peak")


# Parsed disclosures by (raw_dir, url, generation, track); filled lazily or in parallel by prefetch.
_DISCLOSURES = {}
JOBS = 0


def _load(key):
    raw_dir, url, generation, track = key
    return load_disclosure(Path(raw_dir), url, generation, track)


def disclosure(raw_dir, url, generation, track):
    key = (str(raw_dir), url, generation, track)
    if key not in _DISCLOSURES:
        _DISCLOSURES[key] = _load(key)
    return _DISCLOSURES[key]


def prefetch(keys, jobs=None):
    """Parse the not yet loaded disclosures of (raw_dir, url, generation, track) keys in worker processes."""
    missing = list(dict.fromkeys(k for k in ((str(r), u, g, t) for r, u, g, t in keys) if k not in _DISCLOSURES))
    _DISCLOSURES.update(zip(missing, pmap(_load, missing, JOBS if jobs is None else jobs, chunksize=64)))


def collect_integer(raw_dir: Path, track: str) -> dict[str, list[Result]]:
    """Read either metric family without changing reported scores or rate defaults."""
    if track not in {"speed", "rate"}:
        raise ValueError(f"unknown SPEC track: {track}")
    results: dict[str, list[Result]] = {}
    for generation in GENERATIONS:
        rows, digest = read_checked_bulk(raw_dir / generation / "bulk.csv")
        selected: list[Result] = []
        seen: set[str] = set()
        for raw in rows:
            if raw["Benchmark"] != "CINT" + generation[3:] + ("rate" if track == "rate" else ""):
                continue
            peak = positive(raw.get("Result") or raw.get("Peak Result"))
            base = positive(raw.get("Baseline") or raw.get("Base Result"))
            if peak is None and base is None:
                continue
            processor = raw.get("Processor") or raw.get("CPU") or ""
            chips = raw.get("# chips") or raw.get("# Chips") or ""
            if not processor or not chips.isdigit():
                continue
            url = disclosure_url(raw["Disclosure"])
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
                    normalized(raw["System"]),
                    processor,
                    processor_text_key(processor),
                    int(chips),
                    int(cores) if cores.isdigit() else None,
                    int(threads) if threads.isdigit() else None,
                    clock_mhz(raw, processor),
                    memory_mib(raw.get("Memory", "")),
                    raw.get("Operating System") or raw.get("Op. Sys.") or "",
                    raw.get("Compiler", ""),
                    peak,
                    base,
                    url,
                    digest,
                    track=track,
                    raw_fields=raw,
                )
            )
        results[generation] = selected
    # Disclosures parse independently; load them together, then attach in order.
    prefetch((raw_dir, r.source_url, r.generation, track) for group in results.values() for r in group)
    return {
        generation: [replace(r, execution=disclosure(raw_dir, r.source_url, r.generation, track)) for r in group]
        for generation, group in results.items()
    }


def collect_cpu92_rate(path: Path, raw_dir: Path | None = None) -> list[Result]:
    """Load checked Netlib-derived records, retaining each original detail URL/hash."""
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
                    normalized(row["system"]),
                    processor,
                    processor_text_key(processor),
                    int(row["cpu_count"]),
                    None,
                    None,
                    clock_mhz({"System": row["system"]}, processor),
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
        normalized(system),
        processor,
        processor_text_key(processor),
        int(chips[0]),
        None,
        None,
        clock_mhz({"System": system}, processor),
        memory_mib(fields["Memory"]),
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
    records, audit = [], []
    summaries = {}
    for path in sorted((raw / "cpu92/netlib").glob("spec*.cint92.*.col0.html")):
        meta = json.loads(path.with_name(path.name + ".meta.json").read_text())
        body, digest = read_checked_source(path, meta["source_url"])
        mode = "base" if path.name.startswith("specbase.") else "peak"
        for name, score in re.findall(r'(spec\.[^/"#]+\.notes\.html)[^>]*>.*?</A>\s*([0-9.]+)', body, re.I):
            summaries.setdefault((name, mode), []).append((float(score), meta["source_url"], digest))
    for path in sorted((raw / "cpu92/netlib/details").glob("*.cint92.*.html")):
        meta = json.loads(path.with_name(path.name + ".meta.json").read_text())
        # Hash/identity failures are fatal; unsupported document layouts are audited.
        body, digest = read_checked_source(path, meta["source_url"])
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
