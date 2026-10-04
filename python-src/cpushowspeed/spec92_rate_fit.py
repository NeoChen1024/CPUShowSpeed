"""Source-linked CPU92-to-CPU95 integer-rate fit and VAX throughput scale."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import click
from cpushowspeed.curated import DATABASE
from cpushowspeed.observation_store import connect, inputs_digest, result_pair_reviews, spec_results
from cpushowspeed.spec_overlap import (
    INTERVAL_FIELDS,
    PAIR_FIELDS,
    automatic_pairs,
    normalized,
    ratio_statistics,
)
from cpushowspeed.spec_rate_fit import GENERATIONS, collect_rate

METHOD_VERSION = "cpu92-cpu95-rate-fit-v6-reviewed-pairs"
VAX_RATE92_REFERENCE = 604800 / 25500
FACTOR_FIELDS = (
    "method_version",
    "scenario",
    "mode",
    "candidate_pairings",
    "unreviewed_hardware_near_pairings",
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
    "inputs_sha256",
    "pair_export_sha256",
    *INTERVAL_FIELDS,
)

FACTOR_FIELDS = (*FACTOR_FIELDS, "model_center_p95_percent")
CPU92_PAIR_FIELDS = (*PAIR_FIELDS, "review_id", "review_decision")


def _software_near(pair: dict[str, object]) -> bool:
    old, new = normalized(str(pair["old_os"])), normalized(str(pair["new_os"]))
    return old == new or (old == "unixware20" and new == "unixware20sdk")


def selected_pairs(pairs: list[dict[str, object]], scenario: str) -> list[dict[str, object]]:
    """Reviewed-accepted pairs (hardware_near), optionally restricted to a matching OS (same_os)."""
    accepted = [row for row in pairs if row["review_decision"] == "accept"]
    return accepted if scenario == "hardware_near" else [row for row in accepted if _software_near(row)]


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


def analyze_cpu92_rate_fit(database: Path, output_dir: Path, research_dir: Path) -> dict[str, object]:
    with connect(database) as db:
        results = collect_rate(db)
        results["cpu92"] = spec_results(db, "cpu92", "rate")
        digest = inputs_digest(db)
        reviews = result_pair_reviews(db, "spec:cpu92:rate:", "spec:cpu95:rate:")
    pairs = automatic_pairs(results, "cpu92", "cpu95")
    for pair in pairs:
        pair["source_check"] = "netlib_detail_and_summary_hash_checked__cpu95_bulk_hash_checked"
        review_id, decision = reviews.get((pair["old_result_id"], pair["new_result_id"]), ("", "unreviewed"))
        pair["review_id"], pair["review_decision"] = review_id, decision
    unreviewed = sum(1 for row in pairs if row["match_tier"] == "hardware_near" and row["review_decision"] == "unreviewed")
    if unreviewed:
        click.echo(f"warning: {unreviewed} hardware-near CPU92/CPU95 rate pairs lack a review and are not fitted", err=True)
    pairs.sort(key=lambda row: (str(row["old_source_url"]), str(row["new_source_url"])))
    output_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)
    pair_path = output_dir / "cpu92-cpu95-rate-pairs.csv"
    with pair_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CPU92_PAIR_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(pairs)
    fits = {}
    factor_path = research_dir / "cpu92-cpu95-rate-direct-factors.csv"
    with factor_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FACTOR_FIELDS, lineterminator="\n")
        writer.writeheader()
        for scenario in ("hardware_near", "same_os"):
            selected = selected_pairs(pairs, scenario)
            for mode in ("base", "peak"):
                fit_rows = [{**row, "match_tier": "hardware_near"} for row in selected]
                fit = ratio_statistics(fit_rows, mode, {"hardware_near"})
                fits[scenario, mode] = fit
                writer.writerow(
                    {
                        "method_version": METHOD_VERSION,
                        "scenario": scenario,
                        "mode": mode,
                        "candidate_pairings": len(pairs),
                        "unreviewed_hardware_near_pairings": unreviewed,
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
                        "inputs_sha256": digest,
                        "pair_export_sha256": hashlib.sha256(pair_path.read_bytes()).hexdigest(),
                    }
                )
    chain_path = research_dir / "integer-rate-cpu92-vaxen-chain.csv"
    old_chain_path = research_dir / "integer-rate-cpu95-relative-chain.csv"
    downstream_factors = research_dir / "integer-rate-factors.csv"
    with downstream_factors.open(newline="") as stream:
        prior_rows = list(csv.DictReader(stream))
    if any(row["inputs_sha256"] != digest for row in prior_rows):
        raise ValueError("downstream rate factors were fitted on another database; rerun fit-rate-generations")
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
    summary = {
        "method_version": METHOD_VERSION,
        "cpu92_records": len(results["cpu92"]),
        "cpu95_records": len(results["cpu95"]),
        "candidate_pairings": len(pairs),
        "unreviewed_hardware_near_pairings": unreviewed,
        "factor_csv": str(factor_path),
        "edge_intervals_csv": str(interval_path),
        "pair_csv": str(pair_path),
        "chain_csv": str(chain_path),
        "vax_rate92_reference": VAX_RATE92_REFERENCE,
        "fits": {scenario: {mode: fits[scenario, mode] for mode in ("base", "peak")} for scenario in ("hardware_near", "same_os")},
        "limitations": [
            "Fitted pairs are reviewed for hardware configuration; OS, compiler, tuning and copy counts may differ and are recorded in each review.",
            "The VAX reference is CPU92 integer throughput, not CPU92 single-task speed.",
            "Downstream chain factors and their errors remain separate; no universal error band is implied.",
        ],
    }
    summary_path = output_dir / "cpu92-cpu95-rate-fit.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    summary["summary_file"] = str(summary_path)
    return summary


@click.command("fit-cpu92-rate-anchor")
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec/fitting"), show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=Path("research/data/spec/fitting"), show_default=True)
def fit_cpu92_rate_anchor_command(database: Path, output_dir: Path, research_dir: Path) -> None:
    """Fit CPU92 and CPU95 integer rate from the built database, then extend the exploratory rate chain."""
    try:
        summary = analyze_cpu92_rate_fit(database, output_dir, research_dir)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        json.dumps({key: summary[key] for key in ("summary_file", "candidate_pairings", "vax_rate92_reference")}, sort_keys=True)
    )
