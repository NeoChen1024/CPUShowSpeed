"""Speed-only, rate-only and joint speed+rate predictors of the older suite's integer rate, from the built database.

At each adjacent boundary (older, newer) a tuple is one older-rate target with a
newer-suite speed and a newer-suite rate result of the same hardware: the target
pairs with both inputs, and the two inputs pair with each other, at the
`hardware_near` tier over resolved identity (`spec_overlap._automatic_pairs`).
The CPU92 boundary admits only reviewed-accepted CPU92/CPU95 rate pairs, as the
rate anchor does. All three predictors fit the same tuples, so their held-out
errors compare input availability on identical hardware.

A predictor's VAXen coefficient is its local older-rate factor times the saved
`same_os` rate chain of the older suite; their bootstrap draws are combined
assuming the cohorts are independent, which is checked as disjoint configurations.
"""

import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
import numpy as np
from cpushowspeed.calibration import error_summary
from cpushowspeed.curated import DATABASE
from cpushowspeed.observation_store import (
    MODES,
    connect,
    inputs_digest,
    result_pair_reviews,
    spec_results,
)
from cpushowspeed.rate_convert import convert_rate
from cpushowspeed.research_io import code_hashes, write_csv
from cpushowspeed.spec_overlap import _automatic_pairs
from cpushowspeed.spec_rate_chain import GENERATIONS

METHOD_VERSION = "spec-speed-rate-predictors-v5-resolved-identity"
EDGES = tuple(zip(GENERATIONS, GENERATIONS[1:]))
METHODS = {"speed_only": 1.0, "rate_only": 0.0, "equal_geometric": 0.5}
MIN_MODELS = 3
DRAWS = 10000
SEED = 20261002
SCENARIO = "same_os"
CALIBRATION = Path("research/data/spec/fitting")
CHAIN_DRAWS = Path("data/derived/spec/fitting/integer-rate-chain-bootstrap.npz")
CHAIN_CONFIGS = Path("data/derived/spec/fitting/integer-rate-chain-configuration-logs.csv")
DERIVED = Path("data/derived/spec/speed-predictors")
RESEARCH = Path("research/data/spec/speed-predictors")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _near(pairs):
    return {(p["old_result_id"], p["new_result_id"]): p for p in pairs if p["match_tier"] == "hardware_near"}


def triangles(targets, speeds, rates, reviews=None):
    """Complete (target, speed, rate) tuples per mode, and the reason each other candidate was dropped.

    `reviews` maps (target id, rate id) to a decision; when given, only accepted
    target/rate pairs qualify (the CPU92 boundary).
    """
    older, newer = targets[0].generation if targets else "", rates[0].generation if rates else ""
    by_id = {("target", r.result_id): r for r in targets}
    by_id.update({("speed", r.result_id): r for r in speeds})
    by_id.update({("rate", r.result_id): r for r in rates})
    target_rate = _automatic_pairs({"t": targets, "r": rates}, "t", "r")
    if reviews is not None:
        target_rate = [
            dict(p, match_tier="hardware_near")
            for p in target_rate
            if reviews.get(p["old_result_id"], {}).get(p["new_result_id"]) == "accept"
        ]
    target_rate = _near(target_rate)
    target_speed = defaultdict(list)
    for (t, s), p in _near(_automatic_pairs({"t": targets, "s": speeds}, "t", "s")).items():
        target_speed[t].append(s)
    within = _near(_automatic_pairs({"r": rates, "s": speeds}, "r", "s"))
    rows, rejected = [], []
    for (t_id, r_id), tr in sorted(target_rate.items()):
        for s_id in sorted(target_speed.get(t_id, [])):
            t, s, r = by_id["target", t_id], by_id["speed", s_id], by_id["rate", r_id]
            common = dict(
                old_generation=older,
                new_generation=newer,
                model_key=tr["processor_key"],
                system_key=tr["system_key"],
                chips=t.chips,
                clock_mhz=t.clock_mhz,
                target_id=t_id,
                speed_id=s_id,
                rate_id=r_id,
                target_url=t.source_url,
                speed_url=s.source_url,
                rate_url=r.source_url,
                target_system=t.system,
                speed_system=s.system,
                rate_system=r.system,
            )
            if (r_id, s_id) not in within:
                rejected.append(dict(common, mode="", reason="speed_rate_inputs_not_hardware_near"))
                continue
            for mode in MODES:
                values = (getattr(t, mode), getattr(s, mode), getattr(r, mode))
                if tr[mode + "_execution_status"] == "confirmed_count_conflict":
                    rejected.append(dict(common, mode=mode, reason="target_rate_copies_conflict"))
                elif any(v is None for v in values):
                    rejected.append(dict(common, mode=mode, reason="incomplete_positive_score_triplet"))
                else:
                    rows.append(
                        dict(
                            common,
                            mode=mode,
                            target_rate=values[0],
                            speed_score=values[1],
                            rate_score=values[2],
                            rate_execution_status=tr[mode + "_execution_status"],
                        )
                    )
    return rows, rejected, within


def predictor_log(row, method):
    """Log predictor of one tuple; a single-input method never reads the other input."""
    w = METHODS[method]
    if w == 1:
        return math.log(row["speed_score"])
    if w == 0:
        return math.log(row["rate_score"])
    return w * math.log(row["speed_score"]) + (1 - w) * math.log(row["rate_score"])


def configuration_logs(rows, method):
    """(processor, chips, clock) -> median over its systems of the system-median log(target / predictor)."""
    systems = defaultdict(list)
    for row in rows:
        key = (row["model_key"], int(row["chips"]), round(float(row["clock_mhz"]), 1))
        systems[(row["system_key"], *key)].append(math.log(row["target_rate"]) - predictor_log(row, method))
    configs = defaultdict(list)
    for key, values in systems.items():
        configs[key[1:]].append(statistics.median(values))
    return {key: statistics.median(values) for key, values in sorted(configs.items())}


def log_factor(logs, exclude=None, minimum=MIN_MODELS):
    selected = [v for k, v in logs.items() if k[0] != exclude]
    if len({k[0] for k in logs if k[0] != exclude}) < minimum:
        return None
    return statistics.mean(selected)


def holdouts(rows, method, logs):
    """Whole-processor-model holdouts of the local factor against the observed older rate."""
    predictions, centers = [], []
    for model in sorted({k[0] for k in logs}):
        fold = log_factor(logs, model, minimum=MIN_MODELS - 1)
        centers.extend(dict(model_key=model, log_error=fold - v) for k, v in logs.items() if k[0] == model)
        for row in rows:
            if row["model_key"] == model:
                predicted = fold + predictor_log(row, method)
                predictions.append(
                    dict(
                        row,
                        method=method,
                        predicted_older_rate=math.exp(predicted),
                        log_error=predicted - math.log(row["target_rate"]),
                    )
                )
    return predictions, centers


def bootstrap_logs(logs, weights, index):
    """Model-cluster bootstrap of the configuration mean; NaN where a draw keeps no model."""
    w = weights[:, [index[k[0]] for k in logs]]
    total = w.sum(axis=1)
    return np.divide(w @ np.asarray(list(logs.values())), total, out=np.full(len(weights), np.nan), where=total > 0)


def chain(mode, generation):
    """Central VAXen per older-rate score and its saved bootstrap draws (same_os)."""
    central = convert_rate(generation, mode, 1.0, SCENARIO, CALIBRATION)["vaxen"]
    with np.load(CHAIN_DRAWS) as saved:
        scenarios, modes, generations = (list(map(str, saved[k])) for k in ("scenarios", "modes", "generations"))
        draws = saved["vaxen_per_rate_score"][scenarios.index(SCENARIO), modes.index(mode), :, generations.index(generation)]
    return central, np.asarray(draws)


def chain_configurations(older):
    """Configuration keys of the saved rate-chain cohorts that the older suite's factor depends on."""
    depends = set(EDGES[: GENERATIONS.index(older)])
    with CHAIN_CONFIGS.open(newline="", encoding="utf-8") as stream:
        return {
            (r["processor_key"], int(r["chips"]), round(float(r["clock_mhz"]), 1))
            for r in csv.DictReader(stream)
            if r["scenario"] == SCENARIO and (r["old_generation"], r["new_generation"]) in depends
        }


def fit_edge(rows, older, newer, mode, weights, index):
    """Summary rows (one per method), held-out predictions, configuration logs and VAXen draws for one boundary/mode."""
    summaries, predictions, centers, draws = [], [], [], {}
    selected = [r for r in rows if r["mode"] == mode]
    prefix = chain(mode, older)
    shared = sorted({k for k in configuration_logs(selected, "rate_only")} & chain_configurations(older)) if selected else []
    for method in METHODS:
        logs = configuration_logs(selected, method) if selected else {}
        models = {k[0] for k in logs}
        summary = dict(
            method_version=METHOD_VERSION,
            old_generation=older,
            new_generation=newer,
            mode=mode,
            method=method,
            speed_weight=METHODS[method],
            tuples=len(selected),
            processor_configs=len(logs),
            models=len(models),
            status="insufficient_models",
        )
        if len(models) >= MIN_MODELS:
            point = log_factor(logs)
            held, config_errors = holdouts(selected, method, logs)
            local = bootstrap_logs(logs, weights, index)
            valid = np.isfinite(local)
            vaxen = np.exp(local[valid]) * prefix[1][valid]
            summary.update(
                status="conditional_fit",
                coefficient_older_rate=math.exp(point),
                local_ci95_low=float(np.quantile(np.exp(local[valid]), 0.025)),
                local_ci95_high=float(np.quantile(np.exp(local[valid]), 0.975)),
                coefficient_vaxen=math.exp(point) * prefix[0],
                vaxen_ci95_low=float(np.quantile(vaxen, 0.025)),
                vaxen_ci95_high=float(np.quantile(vaxen, 0.975)),
                valid_draws=int(valid.sum()),
                chain_shared_configurations=len(shared),
                **error_summary(held),
            )
            summary["model_center_p95_percent"] = error_summary(config_errors)["model_center_p95_percent"]
            predictions.extend(
                dict(
                    p,
                    observed_target_vaxen=p["target_rate"] * prefix[0] if older == "cpu92" else "",
                    predicted_vaxen=p["predicted_older_rate"] * prefix[0],
                )
                for p in held
            )
            draws[f"{newer}__{mode}__{method}"] = np.where(valid, local + np.log(prefix[1]), np.nan)
        centers.extend(
            dict(
                old_generation=older,
                new_generation=newer,
                mode=mode,
                method=method,
                processor_key=k[0],
                chips=k[1],
                clock_mhz=k[2],
                log_ratio=v,
            )
            for k, v in logs.items()
        )
        summaries.append(summary)
    return summaries, predictions, centers, draws


def plot(summaries, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from cpushowspeed.research_plot import save_figure

    colors = {"speed_only": "#17628a", "rate_only": "#b76520", "equal_geometric": "#38844b"}
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True, sharey=True)
    for ax, mode in zip(axes, MODES):
        for j, (method, color) in enumerate(colors.items()):
            for i, (older, newer) in enumerate(EDGES):
                row = next(r for r in summaries if (r["new_generation"], r["mode"], r["method"]) == (newer, mode, method))
                y = i + (j - 1) * 0.18
                if row["status"] == "conditional_fit":
                    x = row["model_center_p95_percent"]
                    ax.scatter(x, y, color=color, label=method if i == 0 else None)
                    ax.annotate(f"{x:.1f}%", (x, y), xytext=(5, 0), textcoords="offset points", va="center", fontsize=8)
                elif j == 1:
                    ax.text(
                        0.98,
                        i,
                        f"insufficient: {row['models']} model(s)",
                        ha="right",
                        va="center",
                        transform=ax.get_yaxis_transform(),
                        fontsize=8,
                    )
        ax.set_yticks(range(len(EDGES)), [f"{n.upper()} → {o.upper()} rate" for o, n in EDGES])
        ax.set(title=mode, xlabel="Held-out CPU-model center P95 error (%)", xlim=(0, None))
        ax.grid(alpha=0.2)
        ax.legend(loc="upper right", fontsize=8)
    axes[0].invert_yaxis()
    fig.suptitle(
        "Speed/rate predictors of the older suite's rate\nSame hardware-near tuples for all three predictors; errors are against observed older rate"
    )
    save_figure(fig, output, "predictor-holdouts")
    plt.close(fig)


def analyze(database, output, research, draws=DRAWS, seed=SEED):
    with connect(database) as db:
        rates = {g: spec_results(db, g, "rate") for g in GENERATIONS}
        speeds = {g: spec_results(db, g, "speed") for g in GENERATIONS[1:]}
        reviewed = defaultdict(dict)
        for (left, right), (_, decision) in result_pair_reviews(db, "spec:cpu92:rate:", "spec:cpu95:rate:").items():
            reviewed[left][right] = decision
        digest = inputs_digest(db)
    tuples, rejected, inputs, coverage = [], [], [], []
    for older, newer in EDGES:
        rows, rejects, within = triangles(rates[older], speeds[newer], rates[newer], reviewed if older == "cpu92" else None)
        tuples.extend(rows)
        rejected.extend(rejects)
        inputs.extend(
            dict(
                generation=newer,
                rate_id=r,
                speed_id=s,
                system_key=p["system_key"],
                processor_key=p["processor_key"],
                **{m + "_execution_status": p[m + "_execution_status"] for m in MODES},
            )
            for (r, s), p in sorted(within.items())
        )
        coverage.append(
            dict(
                old_generation=older,
                new_generation=newer,
                hardware_near_speed_rate_pairs=len(within),
                tuples=len(rows),
                rejected=len(rejects),
            )
        )
    models = sorted({r["model_key"] for r in tuples})
    index = {k: i for i, k in enumerate(models)}
    rng = np.random.default_rng(seed)
    summaries, predictions, centers, arrays = [], [], [], {}
    for older, newer in EDGES:
        rows = [r for r in tuples if r["new_generation"] == newer]
        for mode in MODES:
            # One weight matrix per boundary/mode, shared by its three predictors.
            weights = (
                rng.multinomial(len(models), np.full(len(models), 1 / len(models)), size=draws) if models else np.zeros((draws, 0))
            )
            s, p, c, a = fit_edge(rows, older, newer, mode, weights, index)
            summaries.extend(s)
            predictions.extend(p)
            centers.extend(c)
            arrays.update(a)
    shared = sum(r.get("chain_shared_configurations", 0) for r in summaries)
    if shared:
        raise ValueError("predictor tuples share configurations with the rate chain they rely on; the draws are not independent")
    output.mkdir(parents=True, exist_ok=True)
    research.mkdir(parents=True, exist_ok=True)
    for path, rows in (
        (output / "tuples.csv", tuples),
        (output / "rejections.csv", rejected),
        (output / "speed-rate-pairs.csv", inputs),
        (output / "holdout-predictions.csv", predictions),
        (output / "configuration-logs.csv", centers),
        (research / "summary.csv", summaries),
        (research / "coverage.csv", coverage),
    ):
        write_csv(path, rows)
    np.savez_compressed(output / "log-vaxen-draws.npz", **arrays)
    plot(summaries, output)
    audit = dict(
        method_version=METHOD_VERSION,
        database_inputs_sha256=digest,
        pairing="hardware_near over resolved system, processor, chips, clock, memory, cores and threads; CPU92 target/rate pairs must be review-accepted",
        predictors=METHODS,
        minimum_models=MIN_MODELS,
        bootstrap="processor-model clusters, one multinomial weight matrix per boundary and mode",
        bootstrap_draws=draws,
        seed=seed,
        rate_chain=dict(
            scenario=SCENARIO,
            draws_sha256=_sha(CHAIN_DRAWS),
            configuration_logs_sha256=_sha(CHAIN_CONFIGS),
            intervals_sha256=_sha(CALIBRATION / "integer-rate-chain-intervals.csv"),
        ),
        independence="predictor configurations are disjoint from the rate-chain cohorts of the older suite (checked)",
        files_sha256={
            str(p): _sha(p) for p in (research / "summary.csv", output / "speed-rate-pairs.csv", output / "log-vaxen-draws.npz")
        },
        code_sha256=code_hashes(Path(__file__)),
        limitations=[
            "Only the CPU92 boundary has VAXen-valued targets; later boundaries validate the local older-rate factor",
            "Transfer of a predictor beyond its overlap hardware is unvalidated",
            "Speed threads, rate copies and software equivalence of a tuple are not verified",
            "CI95 covers coefficient sampling, not individual prediction error",
        ],
    )
    (research / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    return dict(
        summary=str(research / "summary.csv"),
        tuples=len(tuples),
        fitted=sum(r["status"] == "conditional_fit" for r in summaries),
        insufficient=sum(r["status"] != "conditional_fit" for r in summaries),
    )


@click.command("fit-speed-predictors")
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), default=DERIVED, show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=RESEARCH, show_default=True)
@click.option("--bootstrap", "draws", type=click.IntRange(min=100), default=DRAWS, show_default=True)
@click.option("--seed", type=int, default=SEED, show_default=True)
def fit_speed_predictors(database, output_dir, research_dir, draws, seed):
    """Fit speed-only, rate-only and joint predictors of the older suite's rate over resolved hardware."""
    try:
        result = analyze(database, output_dir, research_dir, draws, seed)
    except (OSError, KeyError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, sort_keys=True))
