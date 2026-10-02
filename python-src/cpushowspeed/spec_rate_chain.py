"""Conditional whole-chain rate bootstrap with explicit edge-overlap audit."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import click
import numpy as np
from cpushowspeed.curated import DATABASE
from cpushowspeed.observation_store import connect, inputs_digest
from cpushowspeed.spec92_rate_fit import VAX_RATE92_REFERENCE, _selected
from cpushowspeed.spec_rate_fit import GENERATIONS as LATER_GENERATIONS
from cpushowspeed.spec_rate_inputs import MODES, SCENARIOS, read_rate_factors

METHOD_VERSION = "integer-rate-chain-bootstrap-v1"
GENERATIONS = ("cpu92", *LATER_GENERATIONS)
EDGES = tuple(zip(GENERATIONS, GENERATIONS[1:]))
REPLICATES = 10000
SEED = 892026


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_key(row: dict) -> tuple[str, int, float]:
    return str(row["processor_key"]), int(row["chips"]), round(float(row["old_clock_mhz"]), 1)


def configuration_logs(rows: list[dict], mode: str) -> dict[tuple[str, int, float], float]:
    systems = defaultdict(list)
    for row in rows:
        if row[f"{mode}_ratio"] != "":
            systems[(str(row["system_key"]), *config_key(row))].append(math.log(float(row[f"{mode}_ratio"])))
    configs = defaultdict(list)
    for key, values in systems.items():
        configs[key[1:]].append(statistics.median(values))
    return {key: statistics.median(configs[key]) for key in sorted(configs)}


def audit_overlap(cohorts: list[list[dict]]) -> list[dict]:
    """Audit the broad hardware-near cohorts, including both modes/scenarios."""
    audit = []
    for i, j in combinations(range(len(cohorts)), 2):
        shared_configs = {config_key(row) for row in cohorts[i]} & {config_key(row) for row in cohorts[j]}
        left = {row[field] for row in cohorts[i] for field in ("old_source_url", "new_source_url")}
        right = {row[field] for row in cohorts[j] for field in ("old_source_url", "new_source_url")}
        audit.append(
            {
                "edge_a": "-".join(EDGES[i]),
                "edge_b": "-".join(EDGES[j]),
                "shared_configurations": sorted(shared_configs),
                "shared_submission_urls": sorted(left & right),
            }
        )
    return audit


def bootstrap_log_means(logs: dict, stream: str, replicates: int = REPLICATES) -> np.ndarray:
    if len(logs) < 3:
        raise ValueError(f"too few configuration clusters for {stream}")
    # Independent, reproducible streams across edges and modes. Do not align
    # the identical seeds used in separate marginal CI calculations.
    digest = hashlib.sha256(f"{SEED}:{stream}".encode()).digest()
    rng = np.random.Generator(np.random.PCG64(int.from_bytes(digest[:16], "big")))
    values = np.asarray([logs[key] for key in sorted(logs)], dtype=np.float64)
    indices = rng.integers(0, len(values), size=(replicates, len(values)))
    return values[indices].mean(axis=1)


def propagate(edge_logs: np.ndarray) -> np.ndarray:
    """Rows are coherent bootstrap replicates; columns are chronological edges."""
    if edge_logs.ndim != 2 or edge_logs.shape[1] != len(EDGES):
        raise ValueError("expected one column per chronological rate edge")
    reference = -math.log(VAX_RATE92_REFERENCE)
    return np.exp(np.column_stack((np.full(len(edge_logs), reference), reference + np.cumsum(edge_logs, axis=1))))


def analyze_chain(database: Path, research_dir: Path, fit_dir: Path) -> dict:
    with connect(database) as db:
        digest = inputs_digest(db)
    centers = read_rate_factors(digest, research_dir, fit_dir)
    paths = [fit_dir / "cpu92-cpu95-rate-pairs.csv", fit_dir / "integer-rate-generation-pairs.csv"]
    pairs = _read(paths[0]) + _read(paths[1])
    # The CPU92 anchor fits reviewed-accepted pairs; later edges fit automatic hardware-near pairs.
    cohorts = [
        [
            row
            for row in pairs
            if (row["old_generation"], row["new_generation"]) == edge
            and (row["review_decision"] == "accept" if index == 0 else row["match_tier"] == "hardware_near")
        ]
        for index, edge in enumerate(EDGES)
    ]
    audit = audit_overlap(cohorts)
    if any(row["shared_configurations"] or row["shared_submission_urls"] for row in audit):
        raise ValueError("edges share configurations or submissions; independent-edge bootstrap requires a joint cluster model")
    samples = np.empty((len(SCENARIOS), len(MODES), REPLICATES, len(GENERATIONS)))
    all_edge_samples = np.empty((len(SCENARIOS), len(MODES), REPLICATES, len(EDGES)))
    intervals, config_rows, covariance = [], [], {}
    for mode_index, mode in enumerate(MODES):
        # Later edges are identical between the two anchor scenarios; reuse
        # draws so a scenario comparison changes only its anchor edge.
        downstream = []
        for index in range(1, len(EDGES)):
            logs = configuration_logs(cohorts[index], mode)
            downstream.append(bootstrap_log_means(logs, f"{mode}:{'-'.join(EDGES[index])}:strict"))
        for scenario_index, scenario in enumerate(SCENARIOS):
            active = [_selected(cohorts[0], scenario), *cohorts[1:]]
            config_logs = [configuration_logs(rows, mode) for rows in active]
            point_edges = np.asarray([statistics.mean(list(logs.values())) for logs in config_logs])
            point_chain = propagate(point_edges[None, :])[0]
            for generation, value in zip(GENERATIONS, point_chain):
                if not math.isclose(float(value), centers[scenario, mode, generation], rel_tol=1e-12):
                    raise ValueError(f"configuration estimator disagrees with saved point factor: {scenario}/{mode}/{generation}")
            anchor = bootstrap_log_means(config_logs[0], f"{mode}:cpu92-cpu95:{scenario}")
            draws = np.column_stack((anchor, *downstream))
            chain = propagate(draws)
            all_edge_samples[scenario_index, mode_index] = draws
            samples[scenario_index, mode_index] = chain
            for index, logs in enumerate(config_logs):
                for key, value in logs.items():
                    config_rows.append(
                        {
                            "scenario": scenario,
                            "mode": mode,
                            "old_generation": EDGES[index][0],
                            "new_generation": EDGES[index][1],
                            "processor_key": key[0],
                            "chips": key[1],
                            "clock_mhz": key[2],
                            "configuration_log_ratio": value,
                        }
                    )
            for generation_index, generation in enumerate(GENERATIONS):
                low, high = np.quantile(chain[:, generation_index], [0.025, 0.975], method="linear")
                central = centers[scenario, mode, generation]
                intervals.append(
                    {
                        "method_version": METHOD_VERSION,
                        "scenario": scenario,
                        "mode": mode,
                        "generation": generation,
                        "vaxen_per_rate_score": central,
                        "bootstrap_95_low": float(low),
                        "bootstrap_95_high": float(high),
                        "relative_low": float(low / central),
                        "relative_high": float(high / central),
                        "confidence_level": 0.95,
                        "bootstrap_replicates": REPLICATES,
                        "bootstrap_seed": SEED,
                        "scope": "defined_reference" if generation == "cpu92" else "conditional_chain_mean_scale_pointwise_ci",
                        "edge_dependence_assumption": "independent_disjoint_observed_configuration_cohorts",
                        "factor_chain_sha256": _hash(research_dir / "integer-rate-cpu92-vaxen-chain.csv"),
                    }
                )
            covariance[f"{scenario}/{mode}"] = {
                "generations": list(GENERATIONS[1:]),
                "log_scale_covariance": np.cov(np.log(chain[:, 1:]), rowvar=False).tolist(),
            }
    # Reuse complete rows of these arrays for downstream charts. Sampling a
    # separate multiplier for each submission would lose the shared error.
    draws_path = fit_dir / "integer-rate-chain-bootstrap.npz"
    np.savez_compressed(
        draws_path,
        vaxen_per_rate_score=samples,
        edge_log_factors=all_edge_samples,
        scenarios=np.asarray(SCENARIOS),
        modes=np.asarray(MODES),
        generations=np.asarray(GENERATIONS),
        edges=np.asarray(["-".join(edge) for edge in EDGES]),
        seed=SEED,
        method_version=METHOD_VERSION,
    )
    interval_path = research_dir / "integer-rate-chain-intervals.csv"
    config_path = fit_dir / "integer-rate-chain-configuration-logs.csv"
    for path, rows in ((interval_path, intervals), (config_path, config_rows)):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    summary = {
        "method_version": METHOD_VERSION,
        "replicates": REPLICATES,
        "seed": SEED,
        "generator": "numpy.PCG64; SHA256-derived per-mode/edge stream seeds",
        "numpy_version": np.__version__,
        "interval_csv": str(interval_path),
        "bootstrap_draws": str(draws_path),
        "draws_sha256": _hash(draws_path),
        "configuration_logs_csv": str(config_path),
        "database_inputs_sha256": digest,
        "inputs_sha256": {
            str(path): _hash(path)
            for path in [
                *paths,
                research_dir / "cpu92-cpu95-rate-direct-factors.csv",
                research_dir / "integer-rate-factors.csv",
                research_dir / "integer-rate-cpu92-vaxen-chain.csv",
            ]
        },
        "cross_edge_overlap_audit": audit,
        "within_chain_log_covariance": covariance,
        "limitations": [
            "Independence of disjoint observed cohorts is an assumption; shared workload/compiler biases remain unmodeled",
            "Configurations are resolved processor entity, chips and clock from the built database; family-level entities are coarser than SKUs",
            "Base and peak are separately simulated; no joint base-peak or joint anchor-scenario inference is supplied",
            "Percentile intervals are pointwise for mean scale factors, not simultaneous bands or individual-machine prediction intervals",
        ],
    }
    summary_path = fit_dir / "integer-rate-chain-bootstrap.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return {"summary_file": str(summary_path), "interval_csv": str(interval_path), "bootstrap_draws": str(draws_path)}


@click.command("bootstrap-rate-chain")
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=Path("research/data/spec/fitting"), show_default=True)
@click.option("--fit-dir", type=click.Path(path_type=Path), default=Path("data/derived/spec/fitting"), show_default=True)
def bootstrap_rate_chain_command(database: Path, research_dir: Path, fit_dir: Path) -> None:
    """Bootstrap complete rate chains after checking cross-edge cluster overlap."""
    try:
        result = analyze_chain(database, research_dir, fit_dir)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
