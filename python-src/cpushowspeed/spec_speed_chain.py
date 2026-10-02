"""Integer-speed chain from CPU2026 to SPECint92 speed: speed-VAXen, parallel to the rate chain.

VAX-11/780 is the SPEC92 reference machine, so its SPECint92 speed is 1 by
definition: one speed-VAXen is one SPECint92 point. Each later suite is chained to
it through adjacent-suite speed overlaps, fitted exactly as the rate chain's
edges: automatic `hardware_near` pairs over resolved identity, system medians,
then processor-configuration medians, then the mean over configurations.

Speed and rate stay separate quantities. Rate counts every enabled copy; speed
is one job (CPU2017 speed may run threads). Nothing here is fitted against rate.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import click
import numpy as np
from cpushowspeed.curated import DATABASE
from cpushowspeed.observation_store import MODES, connect, inputs_digest, spec_results
from cpushowspeed.research_io import code_hashes
from cpushowspeed.spec_overlap import INTERVAL_FIELDS, PAIR_FIELDS, _automatic_pairs, _statistics
from cpushowspeed.spec_rate_chain import config_key, configuration_logs

METHOD_VERSION = "integer-speed-chain-v1"
GENERATIONS = ("cpu92", "cpu95", "cpu2000", "cpu2006", "cpu2017", "cpu2026")
EDGES = tuple(zip(GENERATIONS, GENERATIONS[1:]))
REPLICATES = 10000
SEED = 20261003
RESEARCH = Path("research/data/spec/fitting")
DERIVED = Path("data/derived/spec/fitting")
INTERVALS = RESEARCH / "integer-speed-chain-intervals.csv"
FACTORS = RESEARCH / "integer-speed-factors.csv"
DRAWS = DERIVED / "integer-speed-chain-bootstrap.npz"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, rows: list[dict], fields=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fields or rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _bootstrap(logs: dict, stream: str) -> np.ndarray:
    """Configuration-cluster bootstrap of one edge's mean log factor, from its own reproducible stream."""
    digest = hashlib.sha256(f"{SEED}:{stream}".encode()).digest()
    rng = np.random.Generator(np.random.PCG64(int.from_bytes(digest[:16], "big")))
    values = np.asarray([logs[key] for key in sorted(logs)], dtype=np.float64)
    return values[rng.integers(0, len(values), size=(REPLICATES, len(values)))].mean(axis=1)


def analyze(database: Path, research_dir: Path = RESEARCH, fit_dir: Path = DERIVED) -> dict:
    with connect(database) as db:
        results = {g: spec_results(db, g, "speed") for g in GENERATIONS}
        digest = inputs_digest(db)
    pairs, cohorts = [], []
    for old, new in EDGES:
        rows = _automatic_pairs(results, old, new)
        pairs.extend(rows)
        cohorts.append([r for r in rows if r["match_tier"] == "hardware_near"])
    overlap = []
    for i, j in combinations(range(len(EDGES)), 2):
        configs = {config_key(r) for r in cohorts[i]} & {config_key(r) for r in cohorts[j]}
        urls = {r[f] for r in cohorts[i] for f in ("old_source_url", "new_source_url")}
        urls &= {r[f] for r in cohorts[j] for f in ("old_source_url", "new_source_url")}
        if configs or urls:
            overlap.append(dict(edges=["-".join(EDGES[i]), "-".join(EDGES[j])], configurations=len(configs), urls=len(urls)))
    if overlap:
        raise ValueError(f"speed chain edges share configurations or submissions; independent edges cannot be assumed: {overlap}")

    factors, intervals, config_rows = [], [], []
    samples = np.empty((len(MODES), REPLICATES, len(GENERATIONS)))
    for m, mode in enumerate(MODES):
        point, draws = [0.0], [np.zeros(REPLICATES)]
        for (old, new), cohort in zip(EDGES, cohorts):
            stats = _statistics(cohort, mode, {"hardware_near"})
            logs = configuration_logs(cohort, mode)
            if stats is None:
                raise ValueError(f"too few configurations for the {old}-{new} {mode} speed edge")
            if not math.isclose(stats["log_factor"], statistics.mean(logs.values()), rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"edge statistic disagrees with the configuration estimator: {old}-{new} {mode}")
            point.append(point[-1] + stats["log_factor"])
            draws.append(draws[-1] + _bootstrap(logs, f"speed:{mode}:{old}-{new}"))
            models = {r["processor_key"] for r in cohort if r[f"{mode}_ratio"] != ""}
            factors.append(
                dict(
                    method_version=METHOD_VERSION,
                    old_generation=old,
                    new_generation=new,
                    mode=mode,
                    candidate_pairings=sum((r["old_generation"], r["new_generation"]) == (old, new) for r in pairs),
                    fit_pairings=stats["candidate_pairings_used"],
                    system_groups=stats["system_groups"],
                    processor_configs=stats["processor_configs"],
                    processor_models=len(models),
                    factor_old_per_new=stats["factor_old_per_new"],
                    cluster_bootstrap_95_low=stats["cluster_bootstrap_95_low"],
                    cluster_bootstrap_95_high=stats["cluster_bootstrap_95_high"],
                    config_ratio_min=stats["config_ratio_min"],
                    config_ratio_max=stats["config_ratio_max"],
                    heldout_median_absolute_pct_error=stats["heldout_median_absolute_pct_error"],
                    heldout_p95_absolute_pct_error=stats["heldout_p95_absolute_pct_error"],
                    model_center_p95_percent=stats["model_center_p95_percent"],
                    loglog_slope_diagnostic=stats["loglog_slope_diagnostic"],
                    execution_status=json.dumps(dict(Counter(r[f"{mode}_execution_status"] for r in cohort)), sort_keys=True),
                    **{k: stats[k] for k in INTERVAL_FIELDS},
                    inputs_sha256=digest,
                )
            )
            config_rows.extend(
                dict(mode=mode, old_generation=old, new_generation=new, processor_key=k[0], chips=k[1], clock_mhz=k[2], log_ratio=v)
                for k, v in logs.items()
            )
        chain = np.exp(np.column_stack(draws))
        samples[m] = chain
        for g, generation in enumerate(GENERATIONS):
            low, high = np.quantile(chain[:, g], [0.025, 0.975], method="linear")
            central = math.exp(point[g])
            intervals.append(
                dict(
                    method_version=METHOD_VERSION,
                    mode=mode,
                    generation=generation,
                    speed_vaxen_per_score=central,
                    bootstrap_95_low=float(low),
                    bootstrap_95_high=float(high),
                    relative_low=float(low / central),
                    relative_high=float(high / central),
                    confidence_level=0.95,
                    bootstrap_replicates=REPLICATES,
                    bootstrap_seed=SEED,
                    scope="defined_reference" if generation == "cpu92" else "conditional_chain_mean_scale_pointwise_ci",
                    edge_dependence_assumption="independent_disjoint_observed_configuration_cohorts",
                )
            )
    fit_dir.mkdir(parents=True, exist_ok=True)
    pair_path = fit_dir / "integer-speed-generation-pairs.csv"
    config_path = fit_dir / "integer-speed-chain-configuration-logs.csv"
    _write(pair_path, pairs, PAIR_FIELDS)
    _write(config_path, config_rows)
    _write(research_dir / FACTORS.name, factors)
    _write(research_dir / INTERVALS.name, intervals)
    draws_path = fit_dir / DRAWS.name
    np.savez_compressed(
        draws_path,
        speed_vaxen_per_score=samples,
        modes=np.asarray(MODES),
        generations=np.asarray(GENERATIONS),
        seed=SEED,
        method_version=METHOD_VERSION,
    )
    audit = dict(
        method_version=METHOD_VERSION,
        unit="speed-VAXen: VAX-11/780 = 1 = one SPECint92 speed point (SPEC92 reference machine)",
        database_inputs_sha256=digest,
        pairing="automatic hardware_near over resolved system, processor, chips, clock (1%), memory, cores and threads",
        estimator="system median, processor-configuration median, mean over configurations (log scale)",
        bootstrap=dict(unit="processor configuration", replicates=REPLICATES, seed=SEED, edges="independent; overlap checked"),
        source_records={g: len(results[g]) for g in GENERATIONS},
        files_sha256={
            str(p): _hash(p) for p in (research_dir / INTERVALS.name, research_dir / FACTORS.name, draws_path, pair_path)
        },
        code_sha256=code_hashes(Path(__file__)),
        limitations=[
            "Speed counts one job, not throughput; CPU2017 speed may use several threads",
            "CPU92/CPU95 speed pairs are automatic hardware_near matches, not individually reviewed like the rate anchor",
            "Edge independence of disjoint cohorts is an assumption; shared compiler or workload biases remain unmodeled",
            "CI95 covers mean scale factors, not individual-machine prediction error",
        ],
    )
    (fit_dir / "integer-speed-chain.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    return dict(
        edges={f"{f['old_generation']}-{f['new_generation']}/{f['mode']}": round(f["factor_old_per_new"], 6) for f in factors},
        intervals=str(research_dir / INTERVALS.name),
    )


@lru_cache(None)
def _intervals(path: Path = INTERVALS) -> dict:
    with path.open(newline="", encoding="utf-8") as stream:
        return {(r["generation"], r["mode"]): r for r in csv.DictReader(stream)}


def convert_speed(generation: str, mode: str, score: float) -> dict:
    """Speed-VAXen and chain CI95 of one reported integer speed score."""
    row = _intervals().get((generation, mode))
    if row is None:
        raise ValueError(f"no speed chain factor for {generation}/{mode}")
    values = [score * float(row[k]) for k in ("speed_vaxen_per_score", "bootstrap_95_low", "bootstrap_95_high")]
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError("converted speed score is outside the finite positive numeric range")
    return dict(vaxen=values[0], ci95=dict(low=values[1], high=values[2]), scope=row["scope"])


@click.command("fit-speed-chain")
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=RESEARCH, show_default=True)
@click.option("--fit-dir", type=click.Path(path_type=Path), default=DERIVED, show_default=True)
def fit_speed_chain_command(database: Path, research_dir: Path, fit_dir: Path) -> None:
    """Fit the CPU92–CPU2026 integer-speed chain (speed-VAXen, SPECint92 = 1) with a whole-chain bootstrap."""
    try:
        result = analyze(database, research_dir, fit_dir)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
