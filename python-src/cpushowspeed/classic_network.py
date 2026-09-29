"""Sparse joint classical calibration and availability-masked model holdouts."""

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import click
import numpy as np
from cpushowspeed.calibration import error_summary
from cpushowspeed.classic_89_rate import centers, evidence
from cpushowspeed.classic_bridge_data import bridge_rows
from cpushowspeed.classic_network_data import build, family, frequency_checks
from cpushowspeed.classic_network_model import (
    bootstrap,
    bridge_log,
    estimates,
    metric_weights,
    train,
)
from cpushowspeed.classic_predict import write_prediction_manifest
from cpushowspeed.input_context import ACTIVE_CATALOG, source_view
from cpushowspeed.research_io import code_hashes, read_csv, write_csv
from cpushowspeed.research_plot import save_figure


def evaluate(nodes, edges, enabled):
    models = sorted(
        {
            n["model_key"]
            for n in nodes
            if n["target_kind"] in {"observed_rate", "observed_speed"} or (enabled and n["target_kind"] == "estimated_89")
        }
    )
    predictions = []
    coverage = []
    for model in models:
        for method, latent in [("network", True), ("anchored_only", False)]:
            alpha, _ = train(nodes, edges, enabled, exclude=model, latent=latent)
            b = bridge_log(edges, exclude=model) if enabled else 0.0
            for n in nodes:
                if n["model_key"] != model or n["target"] is None:
                    continue
                if n["target_kind"] == "estimated_89" and not enabled:
                    continue
                y = math.log(n["target"]) + (b if n["target_kind"] == "estimated_89" else 0)
                rows = estimates(n, alpha)
                coverage.append(
                    dict(
                        model_key=model,
                        node_id=n["node_id"],
                        method=method,
                        target_kind=n["target_kind"],
                        available_metrics=len(n["log_scores"]),
                        calibrated_metrics=sum(m in alpha for m in n["log_scores"]),
                        subsets_evaluated=len(rows),
                    )
                )
                for r in rows:
                    predictions.append(
                        dict(
                            r,
                            method=method,
                            model_key=model,
                            node_id=n["node_id"],
                            target_kind=n["target_kind"],
                            target_vaxen=math.exp(y),
                            predicted_vaxen=math.exp(r["predicted_log"]),
                            log_error=r["predicted_log"] - y,
                            bridge_factor_used=math.exp(b),
                        )
                    )
    groups = defaultdict(list)
    for r in predictions:
        groups[r["method"], r["target_kind"], r["subset"]].append(r)
    summary = []
    for (method, kind, subset), rows in sorted(groups.items()):
        summary.append(
            dict(
                method=method,
                target_kind=kind,
                subset=subset,
                models=len({r["model_key"] for r in rows}),
                nodes=len(rows),
                **error_summary(rows),
            )
        )
    # Compare input availability on the SAME nodes having every family.
    complete = {n["node_id"] for n in nodes if {family(m) for m in n["log_scores"]} == {"Dhrystone", "Whetstone", "LINPACK"}}
    for (method, kind, subset), rows in sorted(groups.items()):
        selected = [r for r in rows if r["node_id"] in complete]
        if selected:
            summary.append(
                dict(
                    method=method,
                    target_kind=kind,
                    subset=subset,
                    scope="complete_family_nodes",
                    models=len({r["model_key"] for r in selected}),
                    nodes=len(selected),
                    **error_summary(selected),
                )
            )
    for r in summary:
        r.setdefault("scope", "all_available_nodes")
    return summary, predictions, coverage


def plot(output, summary):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    scenarios = sorted({r["scenario"] for r in summary})
    fig, axes = plt.subplots(1, len(scenarios), figsize=(18, 8), squeeze=False)
    for ax, scenario in zip(axes.flat, scenarios):
        rows = [
            r
            for r in summary
            if r["scenario"] == scenario
            and r["cohort"] == "with_spec89"
            and r["target_kind"] == "observed_rate"
            and r["scope"] == "complete_family_nodes"
            and (r["subset"].startswith("single:") or r["subset"].startswith("two_families:") or r["subset"] == "all_available")
        ]
        subsets = sorted({r["subset"] for r in rows})
        for j, method in enumerate(("anchored_only", "network")):
            selected = {r["subset"]: r for r in rows if r["method"] == method}
            ax.scatter(
                [selected[s]["model_center_p95_percent"] for s in subsets if s in selected],
                [i + (j - 0.5) * 0.18 for i, s in enumerate(subsets) if s in selected],
                label=method,
            )
        ax.set_yticks(
            range(len(subsets)),
            [
                s.replace("single:", "")
                .replace("two_families:", "")
                .replace("Dhrystone:", "D ")
                .replace("Whetstone:", "W ")
                .replace("LINPACK:", "L ")
                for s in subsets
            ],
        )
        ax.set_title(scenario)
        ax.invert_yaxis()
        ax.grid(alpha=0.2)
        ax.legend()
        ax.set_xlabel("Held-out model-center relative P95 (%)")
    fig.suptitle(
        "Sparse classical calibration — observed-rate holdouts\nComplete-family nodes for availability comparisons; SPEC89 targets are estimated, not observed rate"
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save_figure(fig, output, "availability-comparison")
    plt.close(fig)


@click.command("network-fit")
@click.option(
    "--input-root",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/overlap-spec"),
    show_default=True,
)
@click.option(
    "--source-root",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/source-pair-fit"),
    show_default=True,
)
@click.option(
    "--native-bridge",
    type=click.Path(path_type=Path, exists=True),
    default=Path("research/data/spec89/v2.0.0/csv/bridges89_92.csv"),
    show_default=True,
)
@click.option(
    "--linpack-text",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/netlib-linpack-report.txt"),
    show_default=True,
)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/network-fit"), show_default=True)
@click.option("--bootstrap", "draws", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260927, show_default=True)
def network_fit(input_root, source_root, native_bridge, linpack_text, output, draws, seed):
    """Calibrate individual benchmark coefficients jointly with missing measurements."""
    paths = [input_root / n for n in ("classical-records.jsonl", "spec-records.jsonl", "candidate-pairs.csv")]
    classical, specs = [{r["id"]: r for r in source_view(p, view)} for p, view in zip(paths[:2], ("classical", "historical-spec"))]
    vectors = source_view(source_root / "vectors.jsonl", "vectors")
    matching = read_csv(source_root / "matching-review.csv")
    pairs = read_csv(paths[2])
    pages = linpack_text.read_text().split("\f")
    ev, _ = evidence(list(specs.values()), vectors, bridge_rows(native_bridge))
    edges = centers(ev)
    output.mkdir(parents=True, exist_ok=True)
    clock_checks = frequency_checks(classical, pages)
    write_csv(output / "frequency-checks.csv", clock_checks)
    coefficients = []
    summary = []
    predictions = []
    coverage = []
    hardware = []
    node_rows = []
    obs_rows = []
    scaling_rows = []
    bootstrap_arrays = {}
    runs = []
    for scaling in (False, True):
        scenario = "linear_clock" if scaling else "reported_clock"
        nodes, observations, audit, aliases = build(classical, specs, pairs, vectors, matching, pages, scaling)
        aliased_evidence = [dict(r, model_key=aliases.get(r["model_key"], r["model_key"])) for r in ev]
        edges = centers(aliased_evidence)
        active = {(n["node_id"], r["metric"], r["observation_id"]) for n in nodes for r in n["observations"]}
        obs_rows.extend(
            dict(r, scenario=scenario, used_in_node_summary=(r["node_id"], r["metric"], r["observation_id"]) in active)
            for r in observations
        )
        scaling_rows.extend(dict(r, scenario=scenario) for r in audit)
        node_rows.extend(
            dict(
                scenario=scenario,
                node_id=n["node_id"],
                model_key=n["model_key"],
                system=n["system"],
                target_kind=n["target_kind"],
                raw_target=n["target"],
                log_scores=json.dumps(n["log_scores"], sort_keys=True),
                observation_count=len(n["observations"]),
            )
            for n in nodes
        )
        for enabled in (False, True):
            cohort = "with_spec89" if enabled else "rate_only"
            context = dict(scenario=scenario, cohort=cohort)
            click.echo("Fitting " + scenario + " / " + cohort, err=True)
            alpha, grouped = train(nodes, edges, enabled)
            metrics, samples = bootstrap(nodes, edges, enabled, draws, seed)
            bootstrap_arrays[scenario + "__" + cohort] = samples
            for i, m in enumerate(metrics):
                scores = np.exp(samples[:, i])
                coefficients.append(
                    dict(
                        context,
                        metric=m,
                        coefficient_vaxen_per_score=math.exp(alpha[m]),
                        factor_ci95_low=float(np.quantile(scores, 0.025)),
                        factor_ci95_high=float(np.quantile(scores, 0.975)),
                        valid_bootstrap_draws=len(samples),
                        informative_models=len(grouped),
                        score_unit="DMIPS" if family(m) == "Dhrystone" else "MWIPS" if family(m) == "Whetstone" else "MFLOPS",
                    )
                )
            sm, pr, cv = evaluate(nodes, edges, enabled)
            summary.extend(dict(context, **r) for r in sm)
            predictions.extend(dict(context, **r) for r in pr)
            coverage.extend(dict(context, **r) for r in cv)
            for n in nodes:
                for estimate in estimates(n, alpha):
                    members = estimate["metrics"].split(";")
                    w = metric_weights(members)
                    boot = sum(w[m] * (samples[:, metrics.index(m)] + n["log_scores"][m]) for m in members)
                    hardware.append(
                        dict(
                            context,
                            node_id=n["node_id"],
                            model_key=n["model_key"],
                            system=n["system"],
                            target_kind=n["target_kind"],
                            subset=estimate["subset"],
                            metrics=estimate["metrics"],
                            estimated_vaxen=math.exp(estimate["predicted_log"]),
                            calibration_ci95_low=float(np.quantile(np.exp(boot), 0.025)),
                            calibration_ci95_high=float(np.quantile(np.exp(boot), 0.975)),
                            evidence_class="fitted_estimate_not_rate_measurement",
                        )
                    )
            runs.append(
                dict(
                    context,
                    nodes=len(nodes),
                    informative_models=len(grouped),
                    calibrated_metrics=metrics,
                    anchored_nodes=sum(
                        n["target_kind"] in {"observed_rate", "observed_speed"} or (enabled and n["target_kind"] == "estimated_89")
                        for n in nodes
                    ),
                    unknown_target_nodes=sum(n["target_kind"] == "unanchored" for n in nodes),
                )
            )
    for name, data in [
        ("coefficients", coefficients),
        ("summary", summary),
        ("predictions", predictions),
        ("fold-coverage", coverage),
        ("hardware-estimates", hardware),
        ("nodes", node_rows),
        ("observations", obs_rows),
        ("clock-audit", scaling_rows),
    ]:
        write_csv(output / (name + ".csv"), data)
    np.savez_compressed(output / "coefficient-log-draws.npz", **bootstrap_arrays)
    write_prediction_manifest(output, runs)
    plot(output, summary)
    paths += [source_root / "vectors.jsonl", source_root / "matching-review.csv", native_bridge, linpack_text]
    audit = dict(
        method="sparse-family-balanced-log-network-v1",
        date="2026-09-27",
        bootstrap=draws,
        seed=seed,
        runs=runs,
        frequency_check_rows=len(clock_checks),
        target="SPEC92 integer-rate VAXen; peak only",
        clock_assumption="Dhrystone/Whetstone linear within existing model candidates with recognized compatible CPU identity; unknown clocks unscaled; unresolved/conflicting CPU clock conflicts excluded; LINPACK unscaled",
        fit="family/variant/node/model balanced log least squares; unanchored node values eliminated analytically",
        qualification="candidate hardware/clock/FPU/cache/software equivalence unverified; coefficient intervals omit model discrepancy and scaling exponent uncertainty",
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        shared_code_sha256=code_hashes(Path(__file__)),
    )
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), runs=runs, coefficients=len(coefficients), comparisons=len(summary))))
