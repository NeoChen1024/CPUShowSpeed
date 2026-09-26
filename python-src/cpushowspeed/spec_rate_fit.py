"""Exploratory adjacent-suite integer-rate fitting from official SPEC exports."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import click
from cpushowspeed.spec_overlap import (
    INTERVAL_FIELDS,
    PAIR_FIELDS,
    Result,
    _automatic_pairs,
    _checked_bulk,
    _frequency,
    _memory_mib,
    _normalized,
    _positive,
    _processor_key,
    _source_url,
    _statistics,
)

GENERATIONS = ("cpu95", "cpu2000", "cpu2006", "cpu2017", "cpu2026")
MODES = ("base", "peak")
METHOD_VERSION = "integer-rate-fit-v3"
POINT_FIELDS = (
    "mode",
    "old_generation",
    "new_generation",
    "tier",
    "old_result_id",
    "new_result_id",
    "old_source_url",
    "new_source_url",
    "old_system",
    "new_system",
    "old_processor",
    "new_processor",
    "chips",
    "old_score",
    "new_score",
    "old_per_new_ratio",
    "processor_key",
)
FACTOR_FIELDS = (
    "method_version",
    "scenario",
    "old_generation",
    "new_generation",
    "mode",
    "candidate_pairings",
    "fit_pairings",
    "system_groups",
    "processor_configs",
    "factor_old_per_new",
    "cluster_bootstrap_95_low",
    "cluster_bootstrap_95_high",
    "config_ratio_min",
    "config_ratio_max",
    "heldout_median_absolute_pct_error",
    "loglog_slope_diagnostic",
    "old_input_sha256",
    "new_input_sha256",
    "pair_export_sha256",
    "heldout_p95_absolute_pct_error",
    *INTERVAL_FIELDS,
)


def collect_rate(raw_dir: Path) -> dict[str, list[Result]]:
    results: dict[str, list[Result]] = {}
    for generation in GENERATIONS:
        rows, digest = _checked_bulk(raw_dir / generation / "bulk.csv")
        selected: list[Result] = []
        seen: set[str] = set()
        for raw in rows:
            if raw["Benchmark"] != "CINT" + generation[3:] + "rate":
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
                raise ValueError(f"duplicate {generation} integer-rate result: {result_id}")
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
                )
            )
        results[generation] = selected
    return results


def _fit_edges(results: dict[str, list[Result]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    pairs: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    for old, new in zip(GENERATIONS, GENERATIONS[1:]):
        cohort = _automatic_pairs(results, old, new)
        pairs.extend(cohort)
        edge = {"old_generation": old, "new_generation": new}
        for mode in MODES:
            edge["strict", mode] = _statistics(cohort, mode, {"hardware_near"})
        edges.append(edge)
    pairs.sort(key=lambda row: (str(row["old_generation"]), str(row["old_result_id"]), str(row["new_result_id"])))
    return pairs, edges


def _chain(edges: list[dict[str, object]], scenario: str, mode: str) -> dict[str, object]:
    factors = {GENERATIONS[0]: 1.0}
    for edge in edges:
        fit = edge[scenario, mode]
        if fit is None:
            return {"status": "disconnected", "relative_to": "CPU95 integer rate score", "factors": factors}
        factors[str(edge["new_generation"])] = factors[str(edge["old_generation"])] * float(fit["factor_old_per_new"])
    return {"status": "exploratory_chain_only", "relative_to": "CPU95 integer rate score", "factors": factors}


def _plot(points: list[dict[str, object]], edges: list[dict[str, object]], output_dir: Path, mode: str) -> dict[str, str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    fig.suptitle(f"SPEC integer rate: adjacent-generation {mode} scores\nEach mark is a submission pairing", fontsize=15)
    for axis, edge in zip(axes.flat, edges):
        old, new = str(edge["old_generation"]), str(edge["new_generation"])
        subset = [row for row in points if row["mode"] == mode and row["old_generation"] == old and row["new_generation"] == new]
        for tier, color, alpha, label in (
            ("name_cpu_chips_only", "#a5afb8", 0.28, "Name/CPU/chips candidate"),
            ("hardware_near", "#17628a", 0.55, "Hardware-near fit tier"),
        ):
            rows = [row for row in subset if row["tier"] == tier]
            if rows:
                axis.scatter(
                    [float(row["new_score"]) for row in rows],
                    [float(row["old_score"]) for row in rows],
                    s=14 if tier == "name_cpu_chips_only" else 22,
                    c=color,
                    alpha=alpha,
                    label=label,
                )
        fit = edge["strict", mode]
        if subset and fit is not None:
            xs = [float(row["new_score"]) for row in subset]
            low, high = min(xs), max(xs)
            if low == high:
                low *= 0.9
                high *= 1.1
            factor = float(fit["factor_old_per_new"])
            axis.plot(
                [low, high],
                [low * factor, high * factor],
                color="#20445f",
                linewidth=1.6,
                label="Configuration-geometric-mean factor",
            )
            counts = Counter(str(row["tier"]) for row in subset)
            axis.text(
                0.03,
                0.97,
                f"k={factor:.4g}; {fit['processor_configs']} configs\n{len(subset)} pairs; {counts['hardware_near']} fit-tier pairs",
                transform=axis.transAxes,
                va="top",
                fontsize=8,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 2},
            )
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_title(f"{old.upper()} → {new.upper()}")
        axis.set_xlabel(f"{new.upper()} reported integer rate {mode}")
        axis.set_ylabel(f"{old.upper()} reported integer rate {mode}")
        axis.grid(which="both", alpha=0.2)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=9)
    paths = {}
    for suffix in ("png", "svg"):
        path = output_dir / f"integer-rate-{mode}-overlaps.{suffix}"
        fig.savefig(path, dpi=170 if suffix == "png" else None)
        paths[suffix] = str(path)
    plt.close(fig)
    return paths


def analyze_rate_generations(raw_dir: Path, output_dir: Path, research_dir: Path) -> dict[str, object]:
    results = collect_rate(raw_dir)
    pairs, edges = _fit_edges(results)
    nonadjacent = []
    for old_index, old in enumerate(GENERATIONS):
        for new in GENERATIONS[old_index + 2 :]:
            candidates = _automatic_pairs(results, old, new)
            nonadjacent.append(
                {
                    "old_generation": old,
                    "new_generation": new,
                    "candidate_pairings": len(candidates),
                    "hardware_near_pairings": sum(row["match_tier"] == "hardware_near" for row in candidates),
                    "base": _statistics(candidates, "base"),
                    "peak": _statistics(candidates, "peak"),
                }
            )
    output_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "integer-rate-source-records.csv"
    with records_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(Result.__dataclass_fields__), lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(item) for generation in GENERATIONS for item in results[generation])
    pair_path = output_dir / "integer-rate-generation-pairs.csv"
    with pair_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PAIR_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(pairs)
    point_path = output_dir / "integer-rate-scatter-points.csv"
    points = []
    for mode in MODES:
        for pair in pairs:
            ratio = pair[f"{mode}_ratio"]
            if ratio == "":
                continue
            points.append(
                {
                    "mode": mode,
                    "old_generation": pair["old_generation"],
                    "new_generation": pair["new_generation"],
                    "tier": pair["match_tier"],
                    "old_result_id": pair["old_result_id"],
                    "new_result_id": pair["new_result_id"],
                    "old_source_url": pair["old_source_url"],
                    "new_source_url": pair["new_source_url"],
                    "old_system": pair["old_system"],
                    "new_system": pair["new_system"],
                    "old_processor": pair["old_processor"],
                    "new_processor": pair["new_processor"],
                    "chips": pair["chips"],
                    "old_score": pair[f"old_{mode}"],
                    "new_score": pair[f"new_{mode}"],
                    "old_per_new_ratio": ratio,
                    "processor_key": pair["processor_key"],
                }
            )
    with point_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=POINT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(points)
    input_hashes = {gen: hashlib.sha256((raw_dir / gen / "bulk.csv").read_bytes()).hexdigest() for gen in GENERATIONS}
    pair_hash = hashlib.sha256(pair_path.read_bytes()).hexdigest()
    factor_path = research_dir / "integer-rate-factors.csv"
    with factor_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FACTOR_FIELDS, lineterminator="\n")
        writer.writeheader()
        for edge in edges:
            old, new = str(edge["old_generation"]), str(edge["new_generation"])
            for mode in MODES:
                fit = edge["strict", mode] or {}
                writer.writerow(
                    {
                        "method_version": METHOD_VERSION,
                        "scenario": "strict",
                        "old_generation": old,
                        "new_generation": new,
                        "mode": mode,
                        "candidate_pairings": sum(
                            pair["old_generation"] == old and pair["new_generation"] == new for pair in pairs
                        ),
                        "fit_pairings": fit.get("candidate_pairings_used", 0),
                        "system_groups": fit.get("system_groups", 0),
                        "processor_configs": fit.get("processor_configs", 0),
                        **{name: fit.get(name, "") for name in FACTOR_FIELDS[9:16]},
                        **{name: fit.get(name, "") for name in ("heldout_p95_absolute_pct_error", *INTERVAL_FIELDS)},
                        "old_input_sha256": input_hashes[old],
                        "new_input_sha256": input_hashes[new],
                        "pair_export_sha256": pair_hash,
                    }
                )
    chain_path = research_dir / "integer-rate-cpu95-relative-chain.csv"
    with chain_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("method_version", "scenario", "mode", "generation", "cpu95_rate_equivalent_per_score", "status"),
            lineterminator="\n",
        )
        writer.writeheader()
        for mode in MODES:
            chain = _chain(edges, "strict", mode)
            for generation in GENERATIONS:
                writer.writerow(
                    {
                        "method_version": METHOD_VERSION,
                        "scenario": "strict",
                        "mode": mode,
                        "generation": generation,
                        "cpu95_rate_equivalent_per_score": chain["factors"].get(generation, ""),
                        "status": chain["status"],
                    }
                )
    figures = {mode: _plot(points, edges, output_dir, mode) for mode in MODES}
    summary = {
        "method_version": METHOD_VERSION,
        "scope": "integer rate, CPU95 through CPU2026; dependent submission pairings retained",
        "source_records": {generation: len(results[generation]) for generation in GENERATIONS},
        "input_sha256": input_hashes,
        "pair_records": str(pair_path),
        "source_record_export": str(records_path),
        "scatter_points": str(point_path),
        "factor_csv": str(factor_path),
        "chain_csv": str(chain_path),
        "figures": figures,
        "nonadjacent_diagnostics": nonadjacent,
        "edges": [
            {
                "old_generation": edge["old_generation"],
                "new_generation": edge["new_generation"],
                "fits": {mode: edge["strict", mode] for mode in MODES},
            }
            for edge in edges
        ],
        "limitations": [
            "CPU95 rate is an internal reference; the separate CPU92 rate fit supplies the VAX throughput anchor",
            "rate copy counts are absent from bulk CSV and have not been checked against every per-result disclosure",
            "hardware-near matches use bulk fields, not a full OS/compiler/tuning audit",
            "repeated submission pairings are dependent; processor-configuration medians limit their fit weight",
        ],
    }
    summary_path = output_dir / "integer-rate-generation-fit.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    summary["summary_file"] = str(summary_path)
    return summary


@click.command("fit-rate-generations")
@click.option("--raw-dir", type=click.Path(path_type=Path), default=Path("data/raw/spec"), show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec/fitting"), show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=Path("research/data/spec/fitting"), show_default=True)
def fit_rate_generations_command(raw_dir: Path, output_dir: Path, research_dir: Path) -> None:
    """Fit CPU95–CPU2026 integer-rate overlaps and draw paired-score scatters."""
    try:
        summary = analyze_rate_generations(raw_dir, output_dir, research_dir)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps({"summary_file": summary["summary_file"], "source_records": summary["source_records"]}, sort_keys=True))
