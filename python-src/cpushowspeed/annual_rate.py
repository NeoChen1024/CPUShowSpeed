"""Annual, source-linked SPEC integer-rate VAXen distributions and leaders."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import click
import numpy as np
from cpushowspeed.spec92_rate_fit import collect_cpu92_rate
from cpushowspeed.spec_overlap import _checked_bulk, _source_url
from cpushowspeed.spec_rate_fit import GENERATIONS, collect_rate
from cpushowspeed.spec_rate_inputs import read_rate_factors

METHOD_VERSION = "annual-integer-rate-v1"
MODES = ("base", "peak")
SCENARIOS = ("same_os", "hardware_near")
RECORD_FIELDS = (
    "method_version",
    "generation",
    "result_id",
    "mode",
    "benchmark_id",
    "reported_score",
    "system",
    "processor",
    "chips",
    "hardware_availability_raw",
    "hardware_availability_month",
    "year",
    "test_month",
    "publication_month",
    "source_url",
    "source_container_sha256",
    "vaxen_same_os",
    "vaxen_hardware_near",
    "date_status",
    "reported_score_evidence_class",
    "vaxen_evidence_class",
)
LEADER_FIELDS = (
    "method_version",
    "mode",
    "year",
    "year_submission_count",
    "tie_count",
    "generation",
    "result_id",
    "benchmark_id",
    "reported_score",
    "vaxen",
    "alternate_vaxen",
    "system",
    "processor",
    "chips",
    "hardware_availability_month",
    "test_month",
    "publication_month",
    "source_url",
    "source_container_sha256",
    "calibration_scenario",
    "reported_score_evidence_class",
    "vaxen_evidence_class",
)
STAT_FIELDS = (
    "method_version",
    "mode",
    "year",
    "submission_count",
    "minimum_vaxen",
    "q1_vaxen",
    "median_vaxen",
    "q3_vaxen",
    "maximum_vaxen",
    "leader_source_url",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _month(value: str) -> str:
    """Keep the source's month precision and refuse guessed dates."""
    value = value.strip()
    if not value:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}", value):
        datetime.strptime(value, "%Y-%m")
        return value
    return datetime.strptime(value, "%b-%Y").strftime("%Y-%m")


def _record(
    *,
    generation: str,
    result_id: str,
    mode: str,
    benchmark_id: str,
    score: float,
    system: str,
    processor: str,
    chips: int,
    hw_raw: str,
    test_raw: str,
    publication_raw: str,
    source_url: str,
    source_hash: str,
    factors: dict[tuple[str, str, str], float],
) -> dict[str, object]:
    hw_month = _month(hw_raw)
    return {
        "method_version": METHOD_VERSION,
        "generation": generation,
        "result_id": result_id,
        "mode": mode,
        "benchmark_id": benchmark_id,
        "reported_score": score,
        "system": system,
        "processor": processor,
        "chips": chips,
        "hardware_availability_raw": hw_raw,
        "hardware_availability_month": hw_month,
        "year": hw_month[:4] if hw_month else "",
        "test_month": _month(test_raw),
        "publication_month": _month(publication_raw),
        "source_url": source_url,
        "source_container_sha256": source_hash,
        "vaxen_same_os": score * factors["same_os", mode, generation],
        "vaxen_hardware_near": score * factors["hardware_near", mode, generation],
        "date_status": "reported_hardware_availability" if hw_month else "missing_hardware_availability",
        "reported_score_evidence_class": "reported_measurement",
        "vaxen_evidence_class": "normalized_estimate",
    }


def collect_annual_records(
    raw_dir: Path, cpu92_records: Path, research_dir: Path, fit_dir: Path
) -> tuple[list[dict[str, object]], dict[str, object]]:
    factors = read_rate_factors(raw_dir, cpu92_records, research_dir, fit_dir)
    official = collect_rate(raw_dir)
    old = collect_cpu92_rate(cpu92_records, raw_dir)
    old_by_url = {item.source_url: item for item in old}
    records = []
    with cpu92_records.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            item = old_by_url[row["source_url"]]
            for mode in MODES:
                score = item.base if mode == "base" else item.peak
                if score is None:
                    continue
                records.append(
                    _record(
                        generation="cpu92",
                        result_id=item.result_id,
                        mode=mode,
                        benchmark_id=row[f"{mode}_metric"],
                        score=score,
                        system=item.system,
                        processor=item.processor,
                        chips=item.chips,
                        hw_raw=row["hardware_availability_month"],
                        test_raw=row["test_month"],
                        publication_raw=row["publication_month"],
                        source_url=item.source_url,
                        source_hash=item.source_container_sha256,
                        factors=factors,
                    )
                )
    raw_hashes = {"cpu92_records": _sha256(cpu92_records)}
    for generation in GENERATIONS:
        rows, digest = _checked_bulk(raw_dir / generation / "bulk.csv")
        raw_hashes[generation] = digest
        selected = {item.source_url: item for item in official[generation]}
        seen = set()
        for row in rows:
            if row["Benchmark"] != "CINT" + generation[3:] + "rate":
                continue
            source_url = _source_url(row["Disclosure"])
            item = selected.get(source_url)
            if item is None:
                continue
            if source_url in seen:
                raise ValueError(f"duplicate selected rate disclosure: {source_url}")
            seen.add(source_url)
            for mode in MODES:
                score = item.base if mode == "base" else item.peak
                if score is None:
                    continue
                records.append(
                    _record(
                        generation=generation,
                        result_id=item.result_id,
                        mode=mode,
                        benchmark_id=row["Benchmark"],
                        score=score,
                        system=item.system,
                        processor=item.processor,
                        chips=item.chips,
                        hw_raw=row["HW Avail"],
                        test_raw=row["Test Date"],
                        publication_raw=row["Published"],
                        source_url=source_url,
                        source_hash=digest,
                        factors=factors,
                    )
                )
        if seen != selected.keys():
            raise ValueError(f"rate disclosure join is incomplete for {generation}")
    records.sort(key=lambda row: (str(row["mode"]), str(row["year"]), str(row["generation"]), str(row["source_url"])))
    if len({(row["mode"], row["source_url"]) for row in records}) != len(records):
        raise ValueError("duplicate annual rate source/mode record")
    return records, {
        "raw_input_sha256": raw_hashes,
        "factor_chain_sha256": _sha256(research_dir / "integer-rate-cpu92-vaxen-chain.csv"),
    }


def _annual(rows: list[dict[str, object]], scenario: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    key = "vaxen_" + scenario
    groups: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        if row["year"]:
            groups[str(row["mode"]), int(str(row["year"]))].append(row)
    leaders, stats = [], []
    for (mode, year), cohort in sorted(groups.items()):
        scores = np.asarray([float(row[key]) for row in cohort], dtype=float)
        maximum = float(np.max(scores))
        tied = [row for row in cohort if math.isclose(float(row[key]), maximum, rel_tol=1e-12)]
        chosen = min(tied, key=lambda row: str(row["source_url"]))
        leaders.append(
            {
                "method_version": METHOD_VERSION,
                "mode": mode,
                "year": year,
                "year_submission_count": len(cohort),
                "tie_count": len(tied),
                "generation": chosen["generation"],
                "result_id": chosen["result_id"],
                "benchmark_id": chosen["benchmark_id"],
                "reported_score": chosen["reported_score"],
                "vaxen": chosen[key],
                "alternate_vaxen": chosen["vaxen_hardware_near" if scenario == "same_os" else "vaxen_same_os"],
                "system": chosen["system"],
                "processor": chosen["processor"],
                "chips": chosen["chips"],
                "hardware_availability_month": chosen["hardware_availability_month"],
                "test_month": chosen["test_month"],
                "publication_month": chosen["publication_month"],
                "source_url": chosen["source_url"],
                "source_container_sha256": chosen["source_container_sha256"],
                "calibration_scenario": scenario,
                "reported_score_evidence_class": "reported_measurement",
                "vaxen_evidence_class": "normalized_estimate",
            }
        )
        stats.append(
            {
                "method_version": METHOD_VERSION,
                "mode": mode,
                "year": year,
                "submission_count": len(cohort),
                "minimum_vaxen": float(np.min(scores)),
                "q1_vaxen": float(np.percentile(scores, 25)),
                "median_vaxen": float(np.median(scores)),
                "q3_vaxen": float(np.percentile(scores, 75)),
                "maximum_vaxen": maximum,
                "leader_source_url": chosen["source_url"],
            }
        )
    return leaders, stats


def _short(value: str, limit: int = 62) -> str:
    clean = " ".join(value.split())
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def _si(value: float) -> str:
    for threshold, suffix in ((1e9, "G"), (1e6, "M"), (1e3, "k")):
        if abs(value) >= threshold:
            return f"{value / threshold:.3g}{suffix}"
    return f"{value:.3g}"


def _leader_plot(leaders: list[dict[str, object]], mode: str, output_dir: Path) -> dict[str, str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    cohort = sorted((row for row in leaders if row["mode"] == mode), key=lambda row: int(row["year"]))
    fig, (labels, plot) = plt.subplots(
        1,
        2,
        figsize=(15, max(8, len(cohort) * 0.5 + 1.5)),
        gridspec_kw={"width_ratios": [3.1, 1.9]},
        sharey=True,
        constrained_layout=True,
    )
    positions = list(range(len(cohort)))
    labels.set_xlim(0, 1)
    labels.set_ylim(len(cohort) - 0.3, -0.8)
    labels.axis("off")
    plot.set_xscale("log")
    plot.set_ylim(len(cohort) - 0.3, -0.8)
    values = [float(row["vaxen"]) for row in cohort]
    plot.set_xlim(min(values) / 1.6, max(values) * 2.4)
    plot.set_yticks(positions)
    plot.set_yticklabels([])
    plot.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: _si(x)))
    plot.set_xlabel("Estimated integer-rate throughput (VAXen; log scale)")
    plot.grid(axis="x", which="both", alpha=0.23)
    for y, row in zip(positions, cohort):
        url = str(row["source_url"])
        label = f"{row['year']} [{str(row['generation']).upper()}]  {_short(str(row['system']))}\n       CPU: {_short(str(row['processor']))}"
        artist = labels.text(0.01, y, label, va="center", fontsize=8.3, linespacing=1.12)
        artist.set_url(url)
        point = plot.scatter(float(row["vaxen"]), y, s=28, c="#17628a", zorder=3)
        point.set_url(url)
        score = plot.text(float(row["vaxen"]) * 1.07, y, _si(float(row["vaxen"])), va="center", fontsize=8)
        score.set_url(url)
        plot.axhline(y + 0.5, color="#e6eaed", linewidth=0.5)
    fig.suptitle(
        f"Annual representative SPEC integer-rate systems — {mode}\n"
        "Highest submission per reported hardware-availability year; estimates use same-OS CPU92 anchor",
        fontsize=12,
    )
    paths = {}
    for extension in ("png", "svg"):
        path = output_dir / f"annual-rate-leaders-{mode}.{extension}"
        fig.savefig(path, dpi=165 if extension == "png" else None)
        paths[extension] = str(path)
    plt.close(fig)
    return paths


def _distribution_plot(
    rows: list[dict[str, object]], leaders: list[dict[str, object]], mode: str, output_dir: Path
) -> dict[str, str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        if row["mode"] == mode and row["year"]:
            groups[int(str(row["year"]))].append(float(row["vaxen_same_os"]))
    years = sorted(groups)
    fig, (axis, count_axis) = plt.subplots(
        2, 1, figsize=(16, 8), sharex=True, gridspec_kw={"height_ratios": [4, 1]}, constrained_layout=True
    )
    axis.boxplot(
        [groups[year] for year in years],
        positions=years,
        widths=0.7,
        showfliers=False,
        patch_artist=True,
        boxprops={"facecolor": "#bcd8e5", "edgecolor": "#40718a"},
        medianprops={"color": "#ab442b"},
    )
    mode_leaders = sorted((row for row in leaders if row["mode"] == mode), key=lambda row: int(row["year"]))
    axis.plot(
        [int(row["year"]) for row in mode_leaders],
        [float(row["vaxen"]) for row in mode_leaders],
        marker="o",
        markersize=2.8,
        linewidth=1.1,
        color="#b34d2e",
        label="Annual highest submission",
    )
    axis.set_yscale("log")
    axis.set_ylabel("Estimated integer-rate throughput (VAXen; log scale)")
    axis.grid(axis="y", which="both", alpha=0.2)
    axis.legend(loc="upper left")
    count_axis.bar(years, [len(groups[year]) for year in years], color="#6e9bac", width=0.72)
    count_axis.set_ylabel("Submissions")
    count_axis.set_xlabel("Reported configuration hardware-availability year")
    count_axis.set_xticks(years[::2])
    count_axis.tick_params(axis="x", rotation=90)
    fig.suptitle(
        f"SPEC integer-rate submissions by hardware year — {mode}\n"
        "All positive, dated submissions; boxes show central 50%; line shows annual maximum",
        fontsize=12,
    )
    paths = {}
    for extension in ("png", "svg"):
        path = output_dir / f"annual-rate-distribution-{mode}.{extension}"
        fig.savefig(path, dpi=165 if extension == "png" else None)
        paths[extension] = str(path)
    plt.close(fig)
    return paths


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def analyze_annual_rate(
    raw_dir: Path, cpu92_records: Path, research_dir: Path, fit_dir: Path, output_dir: Path, summary_dir: Path
) -> dict[str, object]:
    records, provenance = collect_annual_records(raw_dir, cpu92_records, research_dir, fit_dir)
    leaders, stats = _annual(records, "same_os")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "annual-rate-records.csv", RECORD_FIELDS, records)
    _write_csv(summary_dir / "annual-rate-leaders.csv", LEADER_FIELDS, leaders)
    _write_csv(summary_dir / "annual-rate-statistics.csv", STAT_FIELDS, stats)
    undated = [row for row in records if not row["year"]]
    _write_csv(output_dir / "annual-rate-undated.csv", RECORD_FIELDS, undated)
    figures = {}
    for mode in MODES:
        figures[mode] = {
            "leaders": _leader_plot(leaders, mode, output_dir),
            "distribution": _distribution_plot(records, leaders, mode, output_dir),
        }
    summary = {
        "method_version": METHOD_VERSION,
        "calibration_scenario": "same_os",
        "year_event": "reported_configuration_hardware_availability",
        "population_rule": "all positive integer-rate scores with a parseable reported hardware-availability month",
        "per_mode_records": {mode: sum(row["mode"] == mode for row in records) for mode in MODES},
        "per_mode_dated": {mode: sum(row["mode"] == mode and bool(row["year"]) for row in records) for mode in MODES},
        "undated_records": len(undated),
        "leader_years": {mode: sum(row["mode"] == mode for row in leaders) for mode in MODES},
        "earliest_year": min(int(row["year"]) for row in records if row["year"]),
        "latest_year": max(int(row["year"]) for row in records if row["year"]),
        "leader_csv": str(summary_dir / "annual-rate-leaders.csv"),
        "annual_statistics_csv": str(summary_dir / "annual-rate-statistics.csv"),
        "source_records_csv": str(output_dir / "annual-rate-records.csv"),
        "undated_records_csv": str(output_dir / "annual-rate-undated.csv"),
        "figures": figures,
        **provenance,
        "limitations": [
            "All positive dated source submissions are included; reported HW Avail dates are not individually validated",
            "Each annual representative is the highest calibrated submission, not the median machine or first launch",
            "Calibration scenarios are sensitivity choices, not a full-chain confidence interval",
        ],
    }
    path = output_dir / "annual-rate-summary.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    summary["summary_file"] = str(path)
    return summary


@click.group()
def plot() -> None:
    """Render source-linked integer-rate research figures."""


@plot.command("annual-rate")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option(
    "--cpu92-records",
    type=click.Path(path_type=Path),
    default=Path("data/derived/spec/cpu92-rate/cpu92-rate-records.csv"),
    show_default=True,
)
@click.option("--research-dir", type=click.Path(path_type=Path), default=Path("research/data/spec/fitting"), show_default=True)
@click.option("--fit-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec/fitting"), show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/figures/annual-rate"), show_default=True)
@click.option("--summary-dir", type=click.Path(path_type=Path), default=Path("research/data/spec"), show_default=True)
def annual_rate_command(
    raw_dir: Path, cpu92_records: Path, research_dir: Path, fit_dir: Path, output_dir: Path, summary_dir: Path
) -> None:
    """Plot all dated rate submissions and each year's highest-scoring system."""
    try:
        summary = analyze_annual_rate(raw_dir, cpu92_records, research_dir, fit_dir, output_dir, summary_dir)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps({key: summary[key] for key in ("summary_file", "per_mode_dated", "leader_years")}, sort_keys=True))
