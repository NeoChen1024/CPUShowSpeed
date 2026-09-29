"""Source-linked CPU92-to-CPU95 integer-rate fit and VAX throughput scale."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import click
from cpushowspeed.calibration import absolute_error_percent, quantile
from cpushowspeed.spec_inputs import collect_cpu92_rate
from cpushowspeed.spec_overlap import (
    INTERVAL_FIELDS,
    PAIR_FIELDS,
    Result,
    _automatic_pairs,
    _frequency,
    _normalized,
    _processor_key,
    _statistics,
)
from cpushowspeed.spec_rate_fit import GENERATIONS, collect_rate

METHOD_VERSION = "cpu92-cpu95-rate-fit-v4-relative-error"
VAX_RATE92_REFERENCE = 604800 / 25500
FACTOR_FIELDS = (
    "method_version",
    "scenario",
    "mode",
    "candidate_pairings",
    "fit_pairings",
    "system_groups",
    "processor_configs",
    "factor_cpu92_per_cpu95",
    "vaxen_per_cpu95_rate_score",
    "heldout_p95_absolute_pct_error",
    "heldout_median_absolute_pct_error",
    "cluster_bootstrap_95_low",
    "cluster_bootstrap_95_high",
    "config_ratio_min",
    "config_ratio_max",
    "cpu92_records_sha256",
    "cpu95_bulk_sha256",
    "pair_export_sha256",
    *INTERVAL_FIELDS,
)

FACTOR_FIELDS = (*FACTOR_FIELDS, "model_center_p95_percent")


def _software_near(pair: dict[str, object]) -> bool:
    old, new = _normalized(str(pair["old_os"])), _normalized(str(pair["new_os"]))
    return old == new or (old == "unixware20" and new == "unixware20sdk")


def _selected(pairs: list[dict[str, object]], scenario: str) -> list[dict[str, object]]:
    hardware = [row for row in pairs if row["match_tier"] == "hardware_near"]
    return hardware if scenario == "hardware_near" else [row for row in hardware if _software_near(row)]


def _heldout_p95(pairs: list[dict[str, object]], mode: str) -> float | None:
    """Leave-one-processor-configuration-out error, after system/config medians."""
    systems: dict[tuple[str, str, int, float], list[float]] = defaultdict(list)
    for row in pairs:
        ratio = row[f"{mode}_ratio"]
        if ratio != "":
            key = (str(row["system_key"]), str(row["processor_key"]), int(row["chips"]), round(float(row["old_clock_mhz"]), 1))
            systems[key].append(math.log(float(ratio)))
    configs: dict[tuple[str, int, float], list[float]] = defaultdict(list)
    for key, values in systems.items():
        configs[key[1:]].append(statistics.median(values))
    logs = [statistics.median(values) for values in configs.values()]
    if len(logs) < 3:
        return None
    errors = sorted(absolute_error_percent((sum(logs) - value) / (len(logs) - 1) - value) / 100 for value in logs)
    return quantile(errors, 0.95)


def _plot(pairs: list[dict[str, object]], fits: dict[tuple[str, str], dict | None], output_dir: Path) -> dict[str, str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6), constrained_layout=True)
    for axis, mode in zip(axes, ("base", "peak")):
        available = [row for row in pairs if row[f"{mode}_ratio"] != ""]
        for scenario, color, marker, size in (
            ("name_only", "#a5afb8", "o", 15),
            ("hardware_near", "#17628a", "o", 28),
            ("same_os", "#d27136", "x", 38),
        ):
            if scenario == "name_only":
                subset = [row for row in available if row["match_tier"] != "hardware_near"]
            elif scenario == "same_os":
                subset = _selected(available, "same_os")
            else:
                subset = _selected(available, "hardware_near")
            if subset:
                axis.scatter(
                    [row[f"new_{mode}"] for row in subset],
                    [row[f"old_{mode}"] for row in subset],
                    color=color,
                    marker=marker,
                    s=size,
                    alpha=0.57,
                    label=scenario.replace("_", " "),
                )
        xs = [float(row[f"new_{mode}"]) for row in available]
        if xs:
            for scenario, color, style in (("hardware_near", "#17628a", "--"), ("same_os", "#a7461c", "-")):
                fit = fits[scenario, mode]
                if fit:
                    axis.plot(
                        [min(xs), max(xs)],
                        [min(xs) * fit["factor_old_per_new"], max(xs) * fit["factor_old_per_new"]],
                        color=color,
                        linestyle=style,
                        label=f"{scenario.replace('_', ' ')} fit",
                    )
        axis.set(
            xscale="log",
            yscale="log",
            xlabel=f"CPU95 {mode} integer rate",
            ylabel=f"CPU92 {mode} integer rate",
            title=f"CPU92 → CPU95 {mode}",
        )
        axis.grid(which="both", alpha=0.2)
    axes[1].legend(loc="lower right", fontsize=8)
    paths = {}
    for extension in ("png", "svg"):
        path = output_dir / f"cpu92-cpu95-rate-overlap.{extension}"
        fig.savefig(path, dpi=170 if extension == "png" else None)
        paths[extension] = str(path)
    plt.close(fig)
    return paths


def _write_edge_intervals(research_dir: Path) -> Path:
    """Collect all edge CIs without treating them as a joint chain interval."""
    rows = []
    for name in ("cpu92-cpu95-rate-direct-factors.csv", "integer-rate-factors.csv"):
        source = research_dir / name
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        with source.open(newline="") as stream:
            for raw in csv.DictReader(stream):
                rows.append(
                    {
                        "old_generation": raw.get("old_generation", "cpu92"),
                        "new_generation": raw.get("new_generation", "cpu95"),
                        "scenario": raw["scenario"],
                        "mode": raw["mode"],
                        "factor_old_per_new": raw.get("factor_old_per_new", raw.get("factor_cpu92_per_cpu95")),
                        **{
                            key: raw[key]
                            for key in (
                                "fit_pairings",
                                "processor_configs",
                                "cluster_bootstrap_95_low",
                                "cluster_bootstrap_95_high",
                                "heldout_p95_absolute_pct_error",
                                *INTERVAL_FIELDS,
                            )
                        },
                        "scope": "conditional_edge_mean_factor_not_prediction_or_full_chain_interval",
                        "factor_method_version": raw["method_version"],
                        "factor_table": name,
                        "factor_table_sha256": digest,
                        "pair_export_sha256": raw["pair_export_sha256"],
                    }
                )
    path = research_dir / "integer-rate-edge-intervals.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def analyze_cpu92_rate_fit(records_path: Path, raw_dir: Path, output_dir: Path, research_dir: Path) -> dict[str, object]:
    results = collect_rate(raw_dir)
    results["cpu92"] = collect_cpu92_rate(records_path, raw_dir)
    pairs = _automatic_pairs(results, "cpu92", "cpu95")
    for pair in pairs:
        pair["source_check"] = "netlib_detail_and_summary_hash_checked__cpu95_bulk_hash_checked"
    pairs.sort(key=lambda row: (str(row["old_source_url"]), str(row["new_source_url"])))
    output_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)
    pair_path = output_dir / "cpu92-cpu95-rate-pairs.csv"
    with pair_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PAIR_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(pairs)
    fits = {}
    factor_path = research_dir / "cpu92-cpu95-rate-direct-factors.csv"
    with factor_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FACTOR_FIELDS, lineterminator="\n")
        writer.writeheader()
        for scenario in ("hardware_near", "same_os"):
            selected = _selected(pairs, scenario)
            for mode in ("base", "peak"):
                fit_rows = [{**row, "match_tier": "hardware_near"} for row in selected]
                fit = _statistics(fit_rows, mode, {"hardware_near"})
                fits[scenario, mode] = fit
                writer.writerow(
                    {
                        "method_version": METHOD_VERSION,
                        "scenario": scenario,
                        "mode": mode,
                        "candidate_pairings": len(pairs),
                        "fit_pairings": fit["candidate_pairings_used"] if fit else 0,
                        "system_groups": fit["system_groups"] if fit else 0,
                        "processor_configs": fit["processor_configs"] if fit else 0,
                        "factor_cpu92_per_cpu95": fit["factor_old_per_new"] if fit else "",
                        "vaxen_per_cpu95_rate_score": fit["factor_old_per_new"] / VAX_RATE92_REFERENCE if fit else "",
                        "heldout_p95_absolute_pct_error": fit["heldout_p95_absolute_pct_error"] if fit else "",
                        "model_center_p95_percent": fit["model_center_p95_percent"] if fit else "",
                        **{name: fit.get(name, "") if fit else "" for name in INTERVAL_FIELDS},
                        "heldout_median_absolute_pct_error": fit["heldout_median_absolute_pct_error"] if fit else "",
                        "cluster_bootstrap_95_low": fit["cluster_bootstrap_95_low"] if fit else "",
                        "cluster_bootstrap_95_high": fit["cluster_bootstrap_95_high"] if fit else "",
                        "config_ratio_min": fit["config_ratio_min"] if fit else "",
                        "config_ratio_max": fit["config_ratio_max"] if fit else "",
                        "cpu92_records_sha256": hashlib.sha256(records_path.read_bytes()).hexdigest(),
                        "cpu95_bulk_sha256": hashlib.sha256((raw_dir / "cpu95" / "bulk.csv").read_bytes()).hexdigest(),
                        "pair_export_sha256": hashlib.sha256(pair_path.read_bytes()).hexdigest(),
                    }
                )
    chain_path = research_dir / "integer-rate-cpu92-vaxen-chain.csv"
    old_chain_path = research_dir / "integer-rate-cpu95-relative-chain.csv"
    downstream_factors = research_dir / "integer-rate-factors.csv"
    with downstream_factors.open(newline="") as stream:
        prior_rows = list(csv.DictReader(stream))
    for generation in GENERATIONS:
        expected = next(
            (row["old_input_sha256"] for row in prior_rows if row["scenario"] == "strict" and row["old_generation"] == generation),
            None,
        )
        if expected is None:
            expected = next(
                row["new_input_sha256"] for row in prior_rows if row["scenario"] == "strict" and row["new_generation"] == generation
            )
        actual = hashlib.sha256((raw_dir / generation / "bulk.csv").read_bytes()).hexdigest()
        if expected != actual:
            raise ValueError(f"downstream rate factors are stale for {generation}; rerun fit-rate-generations")
    with old_chain_path.open(newline="") as stream:
        old_chain = {(row["scenario"], row["mode"], row["generation"]): row for row in csv.DictReader(stream)}
    with chain_path.open("w", newline="", encoding="utf-8") as stream:
        fields = ("method_version", "scenario", "mode", "generation", "vaxen_per_rate_score", "cpu92_rate_reference", "status")
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for scenario in ("hardware_near", "same_os"):
            for mode in ("base", "peak"):
                fit = fits[scenario, mode]
                if fit is None:
                    continue
                writer.writerow(
                    dict(
                        zip(
                            fields,
                            (
                                METHOD_VERSION,
                                scenario,
                                mode,
                                "cpu92",
                                1 / VAX_RATE92_REFERENCE,
                                VAX_RATE92_REFERENCE,
                                "exploratory_chain",
                            ),
                        )
                    )
                )
                for generation in GENERATIONS:
                    upstream = old_chain["strict", mode, generation]
                    factor = float(upstream["cpu95_rate_equivalent_per_score"])
                    writer.writerow(
                        dict(
                            zip(
                                fields,
                                (
                                    METHOD_VERSION,
                                    scenario,
                                    mode,
                                    generation,
                                    factor * float(fit["factor_old_per_new"]) / VAX_RATE92_REFERENCE,
                                    VAX_RATE92_REFERENCE,
                                    "exploratory_chain",
                                ),
                            )
                        )
                    )
    interval_path = _write_edge_intervals(research_dir)
    figures = _plot(pairs, fits, output_dir)
    summary = {
        "method_version": METHOD_VERSION,
        "cpu92_records": len(results["cpu92"]),
        "cpu95_records": len(results["cpu95"]),
        "candidate_pairings": len(pairs),
        "factor_csv": str(factor_path),
        "edge_intervals_csv": str(interval_path),
        "pair_csv": str(pair_path),
        "chain_csv": str(chain_path),
        "figures": figures,
        "vax_rate92_reference": VAX_RATE92_REFERENCE,
        "fits": {scenario: {mode: fits[scenario, mode] for mode in ("base", "peak")} for scenario in ("hardware_near", "same_os")},
        "limitations": [
            "Hardware-near rows are automatic matches, not a complete per-pair compiler/tuning review.",
            "The VAX reference is CPU92 integer throughput, not CPU92 single-task speed.",
            "Downstream chain factors and their errors remain separate; no universal error band is implied.",
        ],
    }
    summary_path = output_dir / "cpu92-cpu95-rate-fit.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    summary["summary_file"] = str(summary_path)
    return summary


@click.command("fit-rate92-anchor")
@click.option(
    "--records",
    type=click.Path(path_type=Path),
    default=Path("data/derived/spec/cpu92-rate/cpu92-rate-records.csv"),
    show_default=True,
)
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec/fitting"), show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=Path("research/data/spec/fitting"), show_default=True)
def fit_rate92_anchor_command(records: Path, raw_dir: Path, output_dir: Path, research_dir: Path) -> None:
    """Fit CPU92 and CPU95 integer rate, then extend the exploratory rate chain."""
    try:
        summary = analyze_cpu92_rate_fit(records, raw_dir, output_dir, research_dir)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        json.dumps({key: summary[key] for key in ("summary_file", "candidate_pairings", "vax_rate92_reference")}, sort_keys=True)
    )
