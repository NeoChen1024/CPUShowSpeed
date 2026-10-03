"""Sparse joint classical calibration and availability-masked holdouts, from the built database.

Nodes are SPEC targets in speed-VAXen (observed SPECint92 peak, or SPECint89 carried
through the int89_to_int92 bridge) with the classical scores of their paired results,
plus unanchored classical configurations whose co-measured scores constrain
relative benchmark scales. Each exponent group (a benchmark family, but each Whetstone
precision alone) has one power-law exponent, and every
metric passes through the VAX-11/780's own measured score at 1 speed-VAXen
(`classic_network_model`). Folds and bootstrap clusters are resolved systems.
"""

import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

import click
import numpy as np
from cpushowspeed.calibration import error_summary
from cpushowspeed.classic_network_model import (
    bootstrap,
    bridge_log,
    estimates,
    exponent_group,
    metric_weights,
    train,
)
from cpushowspeed.classic_predict import write_prediction_manifest
from cpushowspeed.classical_fit import DERIVED, RESEARCH, bridge_evidence, speed_edges
from cpushowspeed.classical_store import (
    BRIDGE_SCOPE,
    SCOPES,
    VAX780,
    family,
    pairings,
    recovered_int89,
    results,
    target_value,
)
from cpushowspeed.curated import DATABASE
from cpushowspeed.observation_store import connect, inputs_digest
from cpushowspeed.parallel import jobs_option, pmap
from cpushowspeed.research_io import code_hashes, write_csv
from cpushowspeed.research_plot import save_figure


def ci95(log_draws, chunk=1000):
    """Percentile CI95 of exp(draws) for each row of draws, computed in row blocks."""
    out = []
    for i in range(0, len(log_draws), chunk):
        q = np.quantile(np.exp(np.array(log_draws[i : i + chunk])), [0.025, 0.975], axis=1)
        out.extend(zip(q[0].tolist(), q[1].tolist()))
    return out


def vax780_anchor(rows):
    """The 780's median log score per metric, and the standard error of that median's run sample.

    Run-to-run spread is the pooled variance of distinct classical results of one system at one
    reported clock (compiler, OS and option differences included); the anchor's standard error
    is that spread over the 780's run count.
    """
    runs, groups = defaultdict(list), defaultdict(lambda: defaultdict(list))
    for r in rows:
        if not r.classical or r.cpu_count not in (None, 1) or not r.system_id:
            continue
        for metric, score in r.classical.items():
            groups[metric][r.system_id, r.clock_mhz].append(math.log(score))
            if r.system_id == VAX780:
                runs[metric].append(math.log(score))
    anchor, sd, audit = {}, {}, []
    for metric, logs in sorted(runs.items()):
        ss, df = 0.0, 0
        for values in groups[metric].values():
            if len(values) > 1:
                mean = statistics.fmean(values)
                ss += sum((v - mean) ** 2 for v in values)
                df += len(values) - 1
        variance = ss / df if df else 0.0
        anchor[metric] = statistics.median(logs)
        sd[metric] = math.sqrt(variance / len(logs))
        audit.append(
            dict(
                metric=metric,
                vax780_runs=len(logs),
                vax780_median_score=math.exp(anchor[metric]),
                vax780_run_scores=";".join(f"{math.exp(v):.4g}" for v in sorted(logs)),
                run_log_variance=variance,
                run_variance_df=df,
                anchor_log_sd=sd[metric],
            )
        )
    return anchor, sd, audit


def build(rows, scaling):
    """Anchored target nodes, unanchored classical configurations, their observations and the pairing audit."""
    nodes, observations, audit = {}, [], []
    anchored_results = set()

    def add(node, classical, metric, score, adjusted, target_clock, policy):
        row = dict(
            node_id=node["node_id"],
            model_key=node["model_key"],
            metric=metric,
            observation_id=classical.observation_ids[metric],
            classical_result_id=classical.result_id,
            original_score=score,
            adjusted_score=adjusted,
            multiplier=adjusted / score,
            measured_clock_mhz=classical.clock_mhz,
            target_clock_mhz=target_clock,
            clock_policy=policy,
            source_url=classical.source_url,
        )
        observations.append(row)
        node["observations"].append(row)

    for p in pairings(rows, scaling):
        t, c = p["target"], p["classical"]
        speed = target_value(t, "SPECint92")
        old = recovered_int89(t)
        if not speed and not old:
            continue
        audit.append(
            dict(target_result_id=t.result_id, classical_result_id=c.result_id, status=p["status"], included=bool(p["scores"]))
        )
        if not p["scores"]:
            continue
        node = nodes.setdefault(
            t.result_id,
            dict(
                node_id=t.result_id,
                model_key=t.system_id,
                system=t.system,
                target_kind="observed_speed" if speed else "estimated_89",
                target=speed or old,
                observations=[],
            ),
        )
        for metric, adjusted in p["scores"].items():
            add(node, c, metric, c.values[metric], adjusted, t.clock_mhz, p["status"])
        anchored_results.add(c.result_id)
    # Co-measured classical configurations without a target still relate benchmark scales.
    # Clocks are never scaled here, and results already attached to a target are not reused.
    for c in rows:
        if not c.classical or c.result_id in anchored_results or c.cpu_count not in (None, 1):
            continue
        raw = c.raw.get("raw_record") if isinstance(c.raw.get("raw_record"), dict) else c.raw
        text = (c.system + " " + str(raw.get("configuration_raw") or c.raw.get("configuration_raw") or "")).lower()
        options = ";".join(sorted(set(re.findall(r"\b(?:nof|fpa|fpu|fpp)\b", text))))
        key = c.system_id or "result:" + c.result_id
        node_id = f"classical:{key}:{c.clock_mhz}:{options}"
        node = nodes.setdefault(
            node_id, dict(node_id=node_id, model_key=key, system=c.system, target_kind="unanchored", target=None, observations=[])
        )
        for metric, score in c.classical.items():
            add(node, c, metric, score, score, c.clock_mhz, "reported")
    out = []
    for node in nodes.values():
        groups = defaultdict(list)
        for r in node["observations"]:
            groups[r["metric"]].append(math.log(r["adjusted_score"]))
        node["log_scores"] = {m: statistics.median(v) for m, v in groups.items()}
        if node["log_scores"]:
            out.append(node)
    return out, observations, audit


def frequency_checks(rows):
    """Conditional same-label frequency sweeps within one source; not proof of equal software or hardware."""
    grouped = defaultdict(lambda: defaultdict(list))
    members = defaultdict(list)
    for r in rows:
        if not r.clock_mhz:
            continue
        raw = r.raw
        for metric, score in r.classical.items():
            if family(metric) not in ("Dhrystone", "Whetstone"):
                continue
            key = (
                r.scope,
                r.system_id or r.system,
                metric,
                raw.get("processor_raw", ""),
                raw.get("os_raw", ""),
                raw.get("language_raw", ""),
                raw.get("configuration_raw", ""),
            )
            grouped[key][r.clock_mhz].append(math.log(score))
            members[key].append(r.result_id)
    out = []
    for key, frequencies in sorted(grouped.items()):
        if len(frequencies) < 2:
            continue
        first = min(frequencies)
        base = statistics.median(frequencies[first])
        for f, scores in sorted(frequencies.items()):
            if f == first:
                continue
            z = statistics.median(scores) - base
            out.append(
                dict(
                    scope=key[0],
                    system=key[1],
                    metric=key[2],
                    processor_raw=key[3],
                    os_raw=key[4],
                    language_raw=key[5],
                    configuration_raw=key[6],
                    reference_clock=first,
                    target_clock=f,
                    reference_score=math.exp(base),
                    target_score=math.exp(statistics.median(scores)),
                    observed_score_ratio=math.exp(z),
                    clock_ratio=f / first,
                    normalized_ratio=math.exp(z) / (f / first),
                    scaling_signed_error_percent=100 * math.expm1(math.log(f / first) - z),
                    loglog_exponent=z / math.log(f / first),
                    result_ids=json.dumps(members[key]),
                    qualification="same_source_and_labels;missing_configuration_fields_not_verification",
                )
            )
    return out


METHODS = ("network", "anchored_only", "free_intercept")


def evaluate(nodes, edges, enabled, anchor, methods=METHODS):
    models = sorted(
        {n["model_key"] for n in nodes if n["target_kind"] == "observed_speed" or (enabled and n["target_kind"] == "estimated_89")}
    )
    predictions = []
    coverage = []
    cache = {}
    for model in models:
        for method, latent, tie in [("network", True, anchor), ("anchored_only", False, anchor), ("free_intercept", True, {})]:
            if method not in methods:
                continue
            calib, _ = train(nodes, edges, enabled, tie, exclude=model, latent=latent, cache=cache)
            b = bridge_log(edges, exclude=model) if enabled else 0.0
            for n in nodes:
                if n["model_key"] != model or n["target"] is None:
                    continue
                if n["target_kind"] == "estimated_89" and not enabled:
                    continue
                y = math.log(n["target"]) + (b if n["target_kind"] == "estimated_89" else 0)
                rows = estimates(n, calib)
                coverage.append(
                    dict(
                        model_key=model,
                        node_id=n["node_id"],
                        method=method,
                        target_kind=n["target_kind"],
                        available_metrics=len(n["log_scores"]),
                        calibrated_metrics=sum(m in calib for m in n["log_scores"]),
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
            and r["target_kind"] == "observed_speed"
            and r["scope"] == "complete_family_nodes"
            and (r["subset"].startswith("single:") or r["subset"].startswith("two_families:") or r["subset"] == "all_available")
        ]
        subsets = sorted({r["subset"] for r in rows})
        for j, method in enumerate(("anchored_only", "network", "free_intercept")):
            selected = {r["subset"]: r for r in rows if r["method"] == method}
            ax.scatter(
                [selected[s]["model_center_p95_percent"] for s in subsets if s in selected],
                [i + (j - 1) * 0.18 for i, s in enumerate(subsets) if s in selected],
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
        "Sparse classical calibration — observed-SPECint92 holdouts\nComplete-family nodes for availability comparisons; SPEC89 targets are estimated, not observed SPECint92"
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save_figure(fig, output, "availability-comparison")
    plt.close(fig)


def fit_run(task):
    """One scenario/cohort fit: coefficients, holdouts, hardware estimates and bootstrap arrays."""
    rows, edges, anchor, anchor_sd, scaling, enabled, draws, seed = task
    scenario = "linear_clock" if scaling else "reported_clock"
    cohort = "with_spec89" if enabled else "spec92_only"
    nodes, _, _ = build(rows, scaling)
    coefficients, summary, predictions, coverage, hardware, bootstrap_arrays = [], [], [], [], [], {}
    context = dict(scenario=scenario, cohort=cohort)
    click.echo("Fitting " + scenario + " / " + cohort, err=True)
    calib, grouped = train(nodes, edges, enabled, anchor)
    metrics, intercepts, exponents = bootstrap(nodes, edges, enabled, anchor, anchor_sd, draws, seed)
    bootstrap_arrays[scenario + "__" + cohort + "__intercept"] = intercepts
    bootstrap_arrays[scenario + "__" + cohort + "__exponent"] = exponents
    for i, m in enumerate(metrics):
        coefficients.append(
            dict(
                context,
                metric=m,
                family=family(m),
                exponent_group=exponent_group(m),
                score_unit="DMIPS" if family(m) == "Dhrystone" else "MWIPS" if family(m) == "Whetstone" else "MFLOPS",
                exponent=calib[m][1],
                exponent_ci95_low=float(np.quantile(exponents[:, i], 0.025)),
                exponent_ci95_high=float(np.quantile(exponents[:, i], 0.975)),
                vaxen_at_unit_score=math.exp(calib[m][0]),
                unit_score_ci95_low=float(np.exp(np.quantile(intercepts[:, i], 0.025))),
                unit_score_ci95_high=float(np.exp(np.quantile(intercepts[:, i], 0.975))),
                vax780_anchor_score=math.exp(anchor[m]) if m in anchor else "",
                valid_bootstrap_draws=len(intercepts),
                informative_models=len(grouped),
            )
        )
    sm, pr, cv = evaluate(nodes, edges, enabled, anchor)
    summary.extend(dict(context, **r) for r in sm)
    predictions.extend(dict(context, **r) for r in pr)
    coverage.extend(dict(context, **r) for r in cv)
    estimate_rows, boots = [], []
    for n in nodes:
        for estimate in estimates(n, calib):
            members = estimate["metrics"].split(";")
            w = metric_weights(members)
            boots.append(
                sum(w[m] * (intercepts[:, metrics.index(m)] + exponents[:, metrics.index(m)] * n["log_scores"][m]) for m in members)
            )
            estimate_rows.append(
                dict(
                    context,
                    node_id=n["node_id"],
                    model_key=n["model_key"],
                    system=n["system"],
                    target_kind=n["target_kind"],
                    subset=estimate["subset"],
                    metrics=estimate["metrics"],
                    estimated_vaxen=math.exp(estimate["predicted_log"]),
                    calibration_ci95_low=None,
                    calibration_ci95_high=None,
                    evidence_class="fitted_estimate_not_spec_measurement",
                )
            )
    for row, (low, high) in zip(estimate_rows, ci95(boots)):
        hardware.append(dict(row, calibration_ci95_low=low, calibration_ci95_high=high))
    run = dict(
        context,
        nodes=len(nodes),
        informative_models=len(grouped),
        calibrated_metrics=metrics,
        anchored_nodes=sum(n["target_kind"] == "observed_speed" or (enabled and n["target_kind"] == "estimated_89") for n in nodes),
        unknown_target_nodes=sum(n["target_kind"] == "unanchored" for n in nodes),
    )
    return dict(
        coefficients=coefficients,
        summary=summary,
        predictions=predictions,
        coverage=coverage,
        hardware=hardware,
        arrays=bootstrap_arrays,
        run=run,
    )


@click.command("network-fit")
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
@click.option("--output", type=click.Path(path_type=Path), default=DERIVED / "network-fit", show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=RESEARCH, show_default=True)
@click.option("--bootstrap", "draws", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260927, show_default=True)
@jobs_option
def network_fit(database, output, research_dir, draws, seed, jobs):
    """Calibrate per-family power laws through the VAX-11/780 jointly with missing measurements."""
    with connect(database) as db:
        rows = results(db, SCOPES + (BRIDGE_SCOPE,))
        digest = inputs_digest(db)
    edges = speed_edges(bridge_evidence(rows))
    output.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)
    clock_checks = frequency_checks(rows)
    write_csv(output / "frequency-checks.csv", clock_checks)
    anchor, anchor_sd, anchor_rows = vax780_anchor(rows)
    write_csv(output / "vax780-anchor.csv", anchor_rows)
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
        nodes, observations, audit = build(rows, scaling)
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
    # The four scenario/cohort fits are independent; run them in parallel and merge in order.
    tasks = [
        (rows, edges, anchor, anchor_sd, scaling, enabled, draws, seed) for scaling in (False, True) for enabled in (False, True)
    ]
    for result in pmap(fit_run, tasks, jobs):
        coefficients.extend(result["coefficients"])
        summary.extend(result["summary"])
        predictions.extend(result["predictions"])
        coverage.extend(result["coverage"])
        hardware.extend(result["hardware"])
        bootstrap_arrays.update(result["arrays"])
        runs.append(result["run"])
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
    write_csv(research_dir / "network-coefficients.csv", coefficients)
    write_csv(research_dir / "network-summary.csv", summary)
    write_csv(research_dir / "network-frequency-checks.csv", clock_checks)
    audit = dict(
        method="sparse-family-balanced-log-network-v6-two-stage-power-law-vax780",
        bootstrap=draws,
        seed=seed,
        runs=runs,
        frequency_check_rows=len(clock_checks),
        target="speed-VAXen: SPECint92 peak (VAX-11/780 = 1); SPECint89 through the int89_to_int92 bridge",
        pairing="same resolved system_id; reported clocks agree within 1% or one is unknown; reviewed result_pair rejections drop a pairing and acceptances admit it unscaled",
        clock_assumption="linear_clock scales Dhrystone/Whetstone to the target clock only when both results resolve to one processor; unknown clocks unscaled; LINPACK never scaled",
        model="log speed-VAXen = a_m + b_g log score_m; one exponent b_g per group (Dhrystone versions share one, each Whetstone precision has its own, LINPACK one); a_m = -b_g log c_m where c_m is the VAX-11/780's median measured score",
        vax780_anchor=anchor_rows,
        fit="family/variant/node/model balanced log least squares; unanchored node values eliminated analytically; exponents from anchored and multi-family unanchored nodes, then free intercepts from all nodes with exponents fixed",
        uncertainty="model-cluster bootstrap with the 780 anchor redrawn per draw from its run-sample standard error",
        free_intercept="LOSO comparison only: the same exponent groups with free per-metric intercepts",
        qualification="hardware/clock/FPU/cache/software equivalence unverified across sources; intervals omit model discrepancy and clock-scaling exponent uncertainty; era drift of score versus SPEC is not modeled (see the power-law sensitivity report)",
        inputs_sha256=digest,
        shared_code_sha256=code_hashes(Path(__file__)),
    )
    for path in (output / "audit.json", research_dir / "network-audit.json"):
        path.write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), runs=runs, coefficients=len(coefficients), comparisons=len(summary))))
