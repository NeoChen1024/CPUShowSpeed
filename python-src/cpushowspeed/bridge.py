"""Audited overlap evidence for historical SPEC generations."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

import click
from cpushowspeed.bridge_scatter import write_overlap_scatter
from cpushowspeed.plot import Cpu92Record, collect_cpu92
from cpushowspeed.spec import get_cached
from cpushowspeed.spec_fit import fit_generations_command
from cpushowspeed.spec_match_probe import match_coverage_command

PAIR_FIELDS = (
    "system",
    "cpu92_reported_model",
    "cpu95_reported_model",
    "processor",
    "cpu_count",
    "cpu92_score",
    "cpu95_score",
    "cpu92_per_cpu95",
    "cpu92_base_score",
    "cpu95_base_score",
    "cpu92_base_per_cpu95_base",
    "cpu92_test_month",
    "cpu95_test_month",
    "cpu92_memory",
    "cpu95_memory",
    "cpu92_primary_cache",
    "cpu95_primary_cache",
    "cpu92_secondary_cache",
    "cpu95_secondary_cache",
    "cpu92_os",
    "cpu95_os",
    "cpu92_compiler",
    "cpu95_compiler",
    "cpu92_source_url",
    "cpu92_source_sha256",
    "cpu95_source_url",
    "cpu95_source_sha256",
    "cache_capacity_agrees",
    "memory_capacity_agrees",
    "test_month_gap",
    "plot_tier",
    "review_status",
    "architecture",
    "vendor",
)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _clean(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def _read_checked(path: Path, expected_host: str) -> tuple[str, str, str]:
    body = path.read_bytes()
    meta_path = path.with_name(path.name + ".meta.json")
    metadata = json.loads(meta_path.read_text())
    digest = hashlib.sha256(body).hexdigest()
    if digest != metadata.get("sha256"):
        raise ValueError(f"source hash mismatch: {path}")
    url = metadata.get("source_url")
    if not isinstance(url, str) or not url.startswith(expected_host):
        raise ValueError(f"unexpected source URL: {path}")
    return body.decode("utf-8", errors="replace"), url, digest


def _field92(document: str, label: str) -> str:
    match = re.search(r"<DD>" + re.escape(label) + r":\s*(.*?)(?=<DD|<DT|</DL>)", document, re.I | re.S)
    if match is None:
        raise ValueError(f"CPU92 field missing: {label}")
    return _clean(match.group(1))


def _field95(document: str, label: str) -> str:
    match = re.search(r"<TH[^>]*>\s*" + re.escape(label) + r":?\s*<TD[^>]*>\s*(.*?)(?=<TR|</TABLE>)", document, re.I | re.S)
    if match is None:
        raise ValueError(f"CPU95 field missing: {label}")
    return _clean(match.group(1))


def _score92_base(document: str) -> float:
    match = re.search(r"SPECbase_int92:\s*([0-9]+(?:\.[0-9]+)?)", document, re.I)
    if match is None:
        raise ValueError("CPU92 base score missing")
    return float(match.group(1))


def _score95(document: str, label: str) -> float:
    match = re.search(r"<TR>\s*<TH[^>]*>\s*" + re.escape(label) + r"\s*<TH[^>]*>\s*([0-9]+(?:\.[0-9]+)?)", document, re.I)
    if match is None:
        raise ValueError(f"CPU95 score missing: {label}")
    return float(match.group(1))


def _memory_mib(value: str) -> int | None:
    match = re.search(r"\b(\d+)\s*(MB|GB)\b", value, re.I)
    if match is None:
        return None
    return int(match.group(1)) * (1024 if match.group(2).upper() == "GB" else 1)


def _cache_sizes(value: str) -> list[str]:
    return sorted(re.findall(r"\d+\s*(?:KB|MB|GB)", value.upper()))


def _architecture(processor: str) -> str:
    name = processor.lower()
    if "pa-risc" in name:
        return "PA-RISC"
    if "21064" in name or "21164" in name:
        return "Alpha"
    if "pentium" in name:
        return "x86"
    if "sparc" in name:
        return "SPARC"
    if "r4600" in name:
        return "MIPS"
    return "Other"


def _month95(value: str) -> str:
    match = re.fullmatch(r"([A-Za-z]{3})-(\d{2}|\d{4})", value)
    if match is None:
        raise ValueError(f"unexpected CPU95 test month: {value}")
    year = int(match.group(2))
    if year < 100:
        year += 1900
    month = {
        name: number
        for number, name in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)
    }.get(match.group(1).title())
    if month is None:
        raise ValueError(f"unexpected CPU95 test month: {value}")
    return f"{year:04d}-{month:02d}"


def _month_distance(first: str, second: str) -> int:
    ay, am = map(int, first.split("-"))
    by, bm = map(int, second.split("-"))
    return abs((ay * 12 + am) - (by * 12 + bm))


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8", errors="replace") as stream:
        return list(csv.DictReader(stream))


def _reviewed(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    rows = _csv_rows(path)
    reviewed: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = row["cpu92_source_url"], row["cpu95_source_url"]
        if key in reviewed:
            raise ValueError(f"duplicate reviewed pair: {key}")
        reviewed[key] = row
    if not reviewed:
        raise ValueError(f"no reviewed pairs in {path}")
    return reviewed


def analyze_cpu92_cpu95(
    raw_dir: Path, manifest_path: Path, review_path: Path, output_dir: Path, figure_dir: Path, fetch_missing: bool, delay: float
) -> dict[str, object]:
    old, _ = collect_cpu92(raw_dir)
    by_hardware: dict[tuple[str, str, int], list[Cpu92Record]] = defaultdict(list)
    for record in old:
        by_hardware[_normalize(record.system), _normalize(record.processor), record.cpu_count].append(record)

    bulk_path = raw_dir / "cpu95" / "bulk.csv"
    _read_checked(bulk_path, "https://www.spec.org/cgi-bin/osgresults?")
    bulk = _csv_rows(bulk_path)
    manifest = {}
    for line in manifest_path.read_text().splitlines():
        result = json.loads(line)
        if result["generation"] == "cpu95":
            manifest[result["period"], result["result_id"]] = result
    reviewed = _reviewed(review_path)
    found_reviewed: set[tuple[str, str]] = set()
    pair_rows: list[dict[str, object]] = []
    detail_count = 0

    for bulk_row in bulk:
        if bulk_row["Benchmark"] != "CINT95" or float(bulk_row["Result"]) <= 0:
            continue
        key = (_normalize(bulk_row["System"]), _normalize(bulk_row["Processor"]), int(bulk_row["# chips"]))
        if key not in by_hardware:
            continue
        disclosure = re.search(r"/results/(res[^/]+)/([^/]+)\.html", bulk_row["Disclosure"])
        if disclosure is None:
            raise ValueError(f"CPU95 bulk row has no disclosure URL: {bulk_row['System']}")
        result_key = disclosure.group(1), disclosure.group(2)
        result = manifest.get(result_key)
        if result is None:
            raise ValueError(f"CPU95 disclosure absent from index: {result_key}")
        url = result["formats"].get("html")
        if url is None:
            raise ValueError(f"CPU95 HTML disclosure unavailable: {result_key}")
        detail_path = raw_dir / "cpu95" / result_key[0] / (result_key[1] + ".html")
        if not detail_path.exists():
            if not fetch_missing:
                raise ValueError(f"CPU95 detail missing: {detail_path}; rerun with --fetch-missing")
            get_cached(url, detail_path, refresh=False, delay=delay)
        document95, checked_url, digest95 = _read_checked(detail_path, "https://www.spec.org/cpu95/results/")
        if checked_url != url:
            raise ValueError(f"CPU95 detail URL differs from index: {detail_path}")
        score95 = _score95(document95, "SPECint95")
        base95 = _score95(document95, "SPECint_base95")
        if not math.isclose(score95, float(bulk_row["Result"]), rel_tol=0, abs_tol=1e-8) or not math.isclose(
            base95, float(bulk_row["Baseline"]), rel_tol=0, abs_tol=1e-8
        ):
            raise ValueError(f"CPU95 bulk and detail scores differ: {detail_path}")
        processor95 = _field95(document95, "CPU")
        cpu_count95 = int(_field95(document95, "Number of CPU(s)"))
        if _normalize(processor95) != key[1] or cpu_count95 != key[2]:
            raise ValueError(f"CPU95 bulk and detail hardware disagree: {detail_path}")
        detail_count += 1
        fields95 = {
            "model": _field95(document95, "Model Name"),
            "memory": _field95(document95, "Memory"),
            "primary_cache": _field95(document95, "Primary Cache"),
            "secondary_cache": _field95(document95, "Secondary Cache"),
            "os": _field95(document95, "Operating System"),
            "compiler": _field95(document95, "Compiler"),
            "test_month": _month95(_field95(document95, "Test Date")),
        }
        for record92 in by_hardware[key]:
            source92 = raw_dir / "cpu92" / "netlib" / "details" / record92.source_url.rsplit("/", 1)[-1]
            document92, checked92, _ = _read_checked(source92, "https://www.netlib.org/performance/html/")
            if checked92 != record92.source_url:
                raise ValueError(f"CPU92 source URL mismatch: {source92}")
            base92 = _score92_base(document92)
            fields92 = {
                "model": _field92(document92, "Model Number"),
                "memory": _field92(document92, "Memory"),
                "primary_cache": _field92(document92, "Primary Cache"),
                "secondary_cache": _field92(document92, "Secondary Cache"),
                "os": _field92(document92, "O/S & Version"),
                "compiler": _field92(document92, "Compilers & Version"),
            }
            review_key = record92.source_url, checked_url
            decision = reviewed.get(review_key)
            if decision is not None:
                if not math.isclose(float(decision["cpu92_score"]), record92.score, rel_tol=0, abs_tol=1e-8) or not math.isclose(
                    float(decision["cpu95_score"]), score95, rel_tol=0, abs_tol=1e-8
                ):
                    raise ValueError(f"reviewed pair scores differ from source: {review_key}")
                if not math.isclose(float(decision["cpu92_base_score"]), base92, rel_tol=0, abs_tol=1e-8) or not math.isclose(
                    float(decision["cpu95_base_score"]), base95, rel_tol=0, abs_tol=1e-8
                ):
                    raise ValueError(f"reviewed pair base scores differ from source: {review_key}")
                if _memory_mib(fields92["memory"]) is None or _memory_mib(fields92["memory"]) != _memory_mib(fields95["memory"]):
                    raise ValueError(f"reviewed pair memory differs: {review_key}")
                for cache in ("primary_cache", "secondary_cache"):
                    if _cache_sizes(fields92[cache]) != _cache_sizes(fields95[cache]):
                        raise ValueError(f"reviewed pair {cache} differs: {review_key}")
                if _month_distance(record92.tested_month, fields95["test_month"]) > 3:
                    raise ValueError(f"reviewed pair test months differ by over three months: {review_key}")
                found_reviewed.add(review_key)
            pair_rows.append(
                {
                    "system": record92.system,
                    "cpu92_reported_model": fields92["model"],
                    "cpu95_reported_model": fields95["model"],
                    "processor": record92.processor,
                    "cpu_count": record92.cpu_count,
                    "cpu92_score": record92.score,
                    "cpu95_score": score95,
                    "cpu92_per_cpu95": record92.score / score95,
                    "cpu92_base_score": base92,
                    "cpu95_base_score": base95,
                    "cpu92_base_per_cpu95_base": base92 / base95 if base95 > 0 else None,
                    "cpu92_test_month": record92.tested_month,
                    "cpu95_test_month": fields95["test_month"],
                    **{f"cpu92_{name}": value for name, value in fields92.items() if name != "model"},
                    **{f"cpu95_{name}": value for name, value in fields95.items() if name not in {"model", "test_month"}},
                    "cpu92_source_url": record92.source_url,
                    "cpu92_source_sha256": record92.source_sha256,
                    "cpu95_source_url": checked_url,
                    "cpu95_source_sha256": digest95,
                    "cache_capacity_agrees": all(
                        _cache_sizes(fields92[name]) == _cache_sizes(fields95[name])
                        for name in ("primary_cache", "secondary_cache")
                    ),
                    "memory_capacity_agrees": _memory_mib(fields92["memory"]) is not None
                    and _memory_mib(fields92["memory"]) == _memory_mib(fields95["memory"]),
                    "test_month_gap": _month_distance(record92.tested_month, fields95["test_month"]),
                    "plot_tier": (
                        "reviewed"
                        if decision
                        else (
                            "relaxed_cache_agrees"
                            if all(
                                _cache_sizes(fields92[name]) == _cache_sizes(fields95[name])
                                for name in ("primary_cache", "secondary_cache")
                            )
                            else "relaxed_cache_differs_or_unclear"
                        )
                    ),
                    "review_status": "accepted_configuration_near" if decision else "candidate_unreviewed",
                    "architecture": decision["architecture"] if decision else _architecture(record92.processor),
                    "vendor": decision["vendor"] if decision else "",
                }
            )
    if found_reviewed != set(reviewed):
        raise ValueError(f"reviewed pairs missing from source candidates: {len(set(reviewed) - found_reviewed)}")
    if not pair_rows:
        raise ValueError("no CPU92–CPU95 overlap candidates found")

    output_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = output_dir / "cpu92-cpu95-candidates.csv"
    with candidates_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PAIR_FIELDS)
        writer.writeheader()
        writer.writerows(sorted(pair_rows, key=lambda row: (row["system"], row["cpu92_source_url"], row["cpu95_source_url"])))
    figure_paths = write_overlap_scatter(pair_rows, figure_dir)
    accepted = [row for row in pair_rows if row["review_status"] == "accepted_configuration_near"]

    def stats(rows: list[dict[str, object]], ratio_field: str = "cpu92_per_cpu95") -> dict[str, float | int]:
        values = [float(row[ratio_field]) for row in rows]
        return {
            "pairs": len(values),
            "geometric_mean": math.exp(statistics.mean(math.log(value) for value in values)),
            "minimum": min(values),
            "maximum": max(values),
        }

    by_architecture = {
        name: stats([row for row in accepted if row["architecture"] == name])
        for name in sorted({row["architecture"] for row in accepted})
    }
    by_vendor = {
        name: stats([row for row in accepted if row["vendor"] == name]) for name in sorted({row["vendor"] for row in accepted})
    }
    summary = {
        "metric_pair": "SPECint92 / SPECint95 (peak integer speed)",
        "status": "provisional; no universal cross-generation conversion established",
        "candidate_pairs": len(pair_rows),
        "candidate_cpu95_disclosures": detail_count,
        "reviewed_pairs": len(accepted),
        "all_reviewed": stats(accepted),
        "by_architecture": by_architecture,
        "base_sensitivity_by_architecture": {
            name: stats([row for row in accepted if row["architecture"] == name], "cpu92_base_per_cpu95_base")
            for name in sorted({row["architecture"] for row in accepted})
        },
        "by_vendor": by_vendor,
        "review_manifest": str(review_path),
        "candidate_records": str(candidates_path),
        "scatter_pairings": len(pair_rows),
        "distinct_system_cpu_keys": len(
            {(_normalize(str(row["system"])), _normalize(str(row["processor"])), int(row["cpu_count"])) for row in pair_rows}
        ),
        "scatter_tiers": {
            tier: sum(row["plot_tier"] == tier for row in pair_rows)
            for tier in ("reviewed", "relaxed_cache_agrees", "relaxed_cache_differs_or_unclear")
        },
        "scatter_figure": figure_paths,
    }
    summary_path = output_dir / "cpu92-cpu95-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


@click.group()
def bridge() -> None:
    """Audit same-system overlaps between benchmark generations."""


@bridge.command("cpu92-cpu95")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option(
    "--manifest",
    "manifest_path",
    type=click.Path(path_type=Path),
    default=Path("data/derived/spec/result-links.jsonl"),
    show_default=True,
)
@click.option(
    "--review", "review_path", type=click.Path(path_type=Path), default=Path("research/cpu92-cpu95-reviewed.csv"), show_default=True
)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec"), show_default=True)
@click.option("--figure-dir", type=click.Path(path_type=Path), default=Path("data/derived/figures"), show_default=True)
@click.option("--fetch-missing", is_flag=True, help="Download uncached CPU95 overlap disclosures.")
@click.option(
    "--delay", type=click.FloatRange(min=0), default=0.5, show_default=True, help="Seconds after each downloaded disclosure."
)
def cpu92_cpu95_command(
    raw_dir: Path, manifest_path: Path, review_path: Path, output_dir: Path, figure_dir: Path, fetch_missing: bool, delay: float
) -> None:
    """Validate curated CPU92/CPU95 pairs and report their ratio spread."""
    try:
        result = analyze_cpu92_cpu95(raw_dir, manifest_path, review_path, output_dir, figure_dir, fetch_missing, delay)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))


bridge.add_command(fit_generations_command)
bridge.add_command(match_coverage_command)
