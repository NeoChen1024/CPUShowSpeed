"""Parse hash-checked Netlib SPEC CPU92 integer-rate disclosures."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import click
from cpushowspeed import spec92_disclosure
from cpushowspeed.spec_overlap import _memory_mib

METHOD_VERSION = "netlib-cpu92-rate-v3"
BENCHMARKS = ("008.espresso", "022.li", "023.eqntott", "026.compress", "072.sc", "085.gcc")
DETAIL_FIELDS = (
    "method_version",
    "source_url",
    "source_sha256",
    "summary_url",
    "summary_sha256",
    "base_summary_url",
    "base_summary_sha256",
    "company",
    "system",
    "processor",
    "cpu_count",
    "memory",
    "memory_mib",
    "primary_cache",
    "secondary_cache",
    "os",
    "compiler",
    "hardware_availability_month",
    "software_availability_month",
    "test_month",
    "publication_month",
    "peak_metric",
    "peak_score",
    "base_metric",
    "base_score",
    "peak_copies_min",
    "peak_copies_max",
    "base_copies_min",
    "base_copies_max",
    "evidence_class",
)
BENCHMARK_FIELDS = (
    "source_url",
    "benchmark",
    "peak_copies",
    "peak_seconds",
    "peak_rate",
    "base_copies",
    "base_seconds",
    "base_rate",
)


def _checked(path: Path, expected_url: str) -> tuple[str, str]:
    body = path.read_bytes()
    meta = json.loads(path.with_name(path.name + ".meta.json").read_text())
    digest = hashlib.sha256(body).hexdigest()
    if meta.get("source_url") != expected_url or meta.get("sha256") != digest:
        raise ValueError(f"cached source identity mismatch: {path}")
    return body.decode("latin1"), digest


def _summary_score(path: Path, url: str, detail_name: str) -> tuple[float, str]:
    body, digest = _checked(path, url)
    match = re.search(re.escape(detail_name) + r"[^>]*>.*?</A>\s*([0-9]+(?:\.[0-9]+)?)", body, re.I | re.S)
    if match is None:
        raise ValueError(f"detail absent from rate summary: {detail_name} {url}")
    return float(match.group(1)), digest


def _detail(document: str, url: str, digest: str, summary: dict[str, tuple[str, Path]]) -> tuple[dict, list[dict]]:
    page = spec92_disclosure.parse(document)
    if page["metric_heading"] != "SPECrate_int92":
        raise ValueError(f"not an integer-rate disclosure: {url}")
    means = page["reported_means"]
    if means.get("SPECrate_int92", "-") == "-":
        raise ValueError(f"missing peak score: {url}")
    peak_score = float(means["SPECrate_int92"])
    base_score = float(means["SPECrate_base_int92"]) if means.get("SPECrate_base_int92", "-") != "-" else None
    rows = {row[0]: row[1:] for row in page["table"]}
    if sorted(rows) != sorted(BENCHMARKS) or len(page["table"]) != len(BENCHMARKS):
        raise ValueError(f"benchmark row missing or repeated: {url}")
    benchmark_rows = []
    for name in BENCHMARKS:
        numbers = rows[name]
        if len(numbers) == 3:
            peak_copies, peak_seconds, peak_rate = numbers
            base_copies = base_seconds = base_rate = ""
        elif len(numbers) == 6:
            peak_copies, peak_seconds, base_copies, base_seconds, peak_rate, base_rate = numbers
        else:
            raise ValueError(f"unexpected benchmark columns: {name} {numbers} {url}")
        benchmark_rows.append(
            {
                "source_url": url,
                "benchmark": name,
                "peak_copies": int(peak_copies),
                "peak_seconds": float(peak_seconds),
                "peak_rate": float(peak_rate),
                "base_copies": int(base_copies) if base_copies else "",
                "base_seconds": float(base_seconds) if base_seconds else "",
                "base_rate": float(base_rate) if base_rate else "",
            }
        )
    if (base_score is None) != (benchmark_rows[0]["base_copies"] == ""):
        raise ValueError(f"base score/benchmark fields disagree: {url}")
    for mode, reported in (("peak", peak_score), ("base", base_score)):
        if reported is None:
            continue
        calculated = math.exp(statistics.mean(math.log(float(row[f"{mode}_rate"])) for row in benchmark_rows))
        if abs(calculated - reported) > 1.0:
            raise ValueError(f"{mode} composite disagrees with six benchmark rates: {url}")
    detail_name = urlparse(url).path.rsplit("/", 1)[-1]
    peak_summary_url, peak_summary_path = summary["SPECrate_int92"]
    published_peak, peak_summary_sha = _summary_score(peak_summary_path, peak_summary_url, detail_name)
    if published_peak != peak_score:
        raise ValueError(f"rate detail and issue summary disagree: {url}")
    base_summary_url = base_summary_sha = ""
    if "SPECrate_base_int92" in summary:
        base_summary_url, base_summary_path = summary["SPECrate_base_int92"]
        published_base, base_summary_sha = _summary_score(base_summary_path, base_summary_url, detail_name)
        if base_score is None or published_base != base_score:
            raise ValueError(f"base rate detail and issue summary disagree: {url}")
    fields = page["fields"]
    cpu_count = re.match(r"\d+", fields["Number of CPUs"])
    if cpu_count is None or not fields["CPU"] or not fields["O/S & Version"] or page["test_month"] is None:
        raise ValueError(f"missing CPU, CPU count, OS or test date: {url}")
    parsed_memory = _memory_mib(fields["Memory"])
    return (
        {
            "method_version": METHOD_VERSION,
            "source_url": url,
            "source_sha256": digest,
            "summary_url": peak_summary_url,
            "summary_sha256": peak_summary_sha,
            "base_summary_url": base_summary_url,
            "base_summary_sha256": base_summary_sha,
            "company": page["company"],
            "system": page["system"],
            "processor": fields["CPU"],
            "cpu_count": int(cpu_count[0]),
            "memory": fields["Memory"],
            "memory_mib": parsed_memory if parsed_memory is not None else "",
            "primary_cache": fields["Primary Cache"],
            "secondary_cache": fields["Secondary Cache"],
            "os": fields["O/S & Version"],
            "compiler": fields["Compilers & Version"],
            "hardware_availability_month": page["hardware_availability_month"] or "",
            "software_availability_month": page["software_availability_month"] or "",
            "test_month": page["test_month"],
            "publication_month": page["publication_month"],
            "peak_metric": "SPECrate_int92",
            "peak_score": peak_score,
            "base_metric": "SPECrate_base_int92" if base_score is not None else "",
            "base_score": base_score if base_score is not None else "",
            "peak_copies_min": min(row["peak_copies"] for row in benchmark_rows),
            "peak_copies_max": max(row["peak_copies"] for row in benchmark_rows),
            "base_copies_min": min(row["base_copies"] for row in benchmark_rows) if base_score is not None else "",
            "base_copies_max": max(row["base_copies"] for row in benchmark_rows) if base_score is not None else "",
            "evidence_class": "reported_measurement",
        },
        benchmark_rows,
    )


def analyze_cpu92_rate(raw_dir: Path, manifest: Path, output_dir: Path) -> dict[str, object]:
    refs: dict[str, dict[str, tuple[str, Path]]] = defaultdict(dict)
    for line in manifest.read_text().splitlines():
        row = json.loads(line)
        url = row["detail_url"]
        name = urlparse(row["summary_url"]).path.rsplit("/", 1)[-1]
        path = raw_dir / "cpu92" / "netlib" / "rate" / name
        metric = row["metric"]
        if metric in refs[url] and refs[url][metric][0] != row["summary_url"]:
            raise ValueError(f"multiple {metric} summaries for {url}")
        refs[url][metric] = row["summary_url"], path
    records, benchmarks, exclusions = [], [], []
    for url, summaries in sorted(refs.items()):
        name = urlparse(url).path.rsplit("/", 1)[-1]
        path = raw_dir / "cpu92" / "netlib" / "rate" / "details" / name
        if not path.exists():
            exclusions.append({"source_url": url, "reason": "detail_not_cached"})
            continue
        try:
            document, digest = _checked(path, url)
            record, rows = _detail(document, url, digest, summaries)
        except (ValueError, IndexError) as exc:
            exclusions.append({"source_url": url, "reason": str(exc)})
            continue
        records.append(record)
        benchmarks.extend(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, fields, rows in (
        ("cpu92-rate-records.csv", DETAIL_FIELDS, records),
        ("cpu92-rate-benchmarks.csv", BENCHMARK_FIELDS, benchmarks),
        ("cpu92-rate-exclusions.csv", ("source_url", "reason"), exclusions),
    ):
        with (output_dir / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    summary = {
        "method_version": METHOD_VERSION,
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "source_disclosures": len(refs),
        "parsed_records": len(records),
        "excluded": len(exclusions),
        "benchmarks": len(benchmarks),
        "publication_months": dict(sorted(Counter(row["publication_month"] for row in records).items())),
        "earliest_test_month": min((row["test_month"] for row in records), default=""),
        "records_csv": str(output_dir / "cpu92-rate-records.csv"),
        "benchmarks_csv": str(output_dir / "cpu92-rate-benchmarks.csv"),
        "exclusions_csv": str(output_dir / "cpu92-rate-exclusions.csv"),
    }
    (output_dir / "cpu92-rate-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


@click.command("legacy92-rate-parse")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option(
    "--manifest",
    type=click.Path(path_type=Path),
    default=Path("data/derived/spec/cpu92-netlib-rate-links.jsonl"),
    show_default=True,
)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec/cpu92-rate"), show_default=True)
def legacy92_rate_parse_command(raw_dir: Path, manifest: Path, output_dir: Path) -> None:
    """Verify cached CINT92 rate details against their issue summaries."""
    try:
        result = analyze_cpu92_rate(raw_dir, manifest, output_dir)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
