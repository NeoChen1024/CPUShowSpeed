"""Extend the classical sparse calibration with candidate instruction-mix observations."""

import copy
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
import numpy as np
from cpushowspeed.calibration import ANCHOR, error_summary
from cpushowspeed.classic_89_rate import centers, evidence
from cpushowspeed.classic_bridge_data import bridge_rows
from cpushowspeed.classic_network import evaluate
from cpushowspeed.classic_network_data import build
from cpushowspeed.classic_network_model import bootstrap, metric_weights, train
from cpushowspeed.research_io import code_hashes, read_csv, write_csv

MIX_METRICS = {"Gibson Mix": "InstructionMix:Gibson_KIPS", "ADP Mix": "InstructionMix:ADP_KIPS"}
ROOT = Path("data/derived/classic")


def attach(nodes, pairs, observations):
    """Join by original observation ID; never use historical predicted VAXen."""
    by_config = defaultdict(set)
    for r in observations:
        by_config[r["configuration_id"]].add((r["observation_id"], r["metric"]))
    index = defaultdict(list)
    for n in nodes:
        for r in n["observations"]:
            index[r["observation_id"], r["metric"]].append(n["node_id"])
    by_id = {n["node_id"]: n for n in nodes}
    additions = defaultdict(dict)
    audit = []
    for p in pairs:
        matches = set()
        for oid, metric in by_config[p["classical_configuration_id"]]:
            if metric == p["metric"]:
                matches.update(index[oid, metric])
        for nid in sorted(matches):
            metric = MIX_METRICS[p["mix"]]
            additions[nid][p["mix_id"]] = (metric, float(p["mix_kips"]))
        audit.append(
            dict(
                p,
                node_ids=";".join(sorted(matches)),
                attached_nodes=len(matches),
                status="candidate_attached" if matches else "no_eligible_classical_node",
            )
        )
    # Any reused mix observation must leave with all linked hardware nodes.
    parent = {n["model_key"]: n["model_key"] for n in nodes}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)

    groups = defaultdict(list)
    for nid, values in additions.items():
        for oid in values:
            groups[oid].append(by_id[nid]["model_key"])
    for keys in groups.values():
        for k in keys[1:]:
            union(keys[0], k)
    extended = copy.deepcopy(nodes)
    for n in extended:
        n["model_key"] = find(n["model_key"])
        values = defaultdict(list)
        for oid, (metric, value) in additions[n["node_id"]].items():
            values[metric].append(math.log(value))
        n["mix_ids"] = sorted(additions[n["node_id"]])
        for metric, logs in values.items():
            n["log_scores"][metric] = statistics.median(logs)
    baseline = copy.deepcopy(nodes)
    for n in baseline:
        n["model_key"] = find(n["model_key"])
    return extended, baseline, audit, {k: find(k) for k in parent}


@click.command("mix-network-fit")
@click.option("--output", type=click.Path(path_type=Path), default=ROOT / "mix-network-fit", show_default=True)
@click.option("--bootstrap", "draws", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260928, show_default=True)
def mix_network_fit(output, draws, seed):
    """Jointly calibrate candidate Gibson/ADP links to SPEC92 integer-rate VAXen."""
    paths = [ROOT / "overlap-spec" / n for n in ["classical-records.jsonl", "spec-records.jsonl", "candidate-pairs.csv"]]
    paths += [
        ROOT / "source-pair-fit/vectors.jsonl",
        ROOT / "source-pair-fit/matching-review.csv",
        Path("research/data/spec89/v2.0.0/csv/bridges89_92.csv"),
        ROOT / "netlib-linpack-report.txt",
        ROOT / "mix-study/candidate-pairs.csv",
        ROOT / "historical-timeline/observations.csv",
        ROOT / "mix-study/mix-records.csv",
    ]
    classical, specs = [{r["id"]: r for r in map(json.loads, p.read_text().splitlines())} for p in paths[:2]]
    vectors = [json.loads(l) for l in paths[3].read_text().splitlines()]
    ev, _ = evidence(list(specs.values()), vectors, bridge_rows(paths[5]))
    pairs = read_csv(paths[7])
    observations = read_csv(paths[8])
    mixes = read_csv(paths[9])
    for p, digest in json.loads((ROOT / "mix-study/audit.json").read_text())["input_sha256"].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest:
            raise click.ClickException("Stale mix inventory: " + p)
    output.mkdir(parents=True, exist_ok=True)
    coeffs = []
    diagnostics = []
    holdouts = []
    link_audit = []
    node_export = []
    anchor_summary = []
    predictions = []
    runs = []
    arrays = {}
    for scaling in [False, True]:
        scenario = "linear_clock" if scaling else "reported_clock"
        nodes, _, _, aliases = build(
            classical, specs, read_csv(paths[2]), vectors, read_csv(paths[4]), paths[6].read_text().split("\f"), scaling
        )
        extended, baseline, links, closure = attach(nodes, pairs, observations)
        edges = centers(
            [
                dict(
                    r,
                    model_key=closure.get(aliases.get(r["model_key"], r["model_key"]), aliases.get(r["model_key"], r["model_key"])),
                )
                for r in ev
            ]
        )
        link_audit.extend(dict(r, scenario=scenario) for r in links)
        for n in extended:
            if n["mix_ids"]:
                node_export.append(
                    dict(
                        scenario=scenario,
                        node_id=n["node_id"],
                        model_key=n["model_key"],
                        target_kind=n["target_kind"],
                        target=n["target"],
                        log_scores=json.dumps(n["log_scores"]),
                        mix_ids=json.dumps(n["mix_ids"]),
                    )
                )
        for enabled in [False, True]:
            cohort = "with_spec89" if enabled else "rate_only"
            context = dict(scenario=scenario, cohort=cohort)
            click.echo(f"Joint fitting {scenario} / {cohort}", err=True)
            alpha, grouped = train(extended, edges, enabled)
            base_alpha, _ = train(baseline, edges, enabled)
            metrics, samples = bootstrap(extended, edges, enabled, draws, seed)
            arrays[scenario + "__" + cohort] = samples
            for metric in metrics:
                values = np.exp(samples[:, metrics.index(metric)])
                k = math.exp(alpha[metric])
                coeffs.append(
                    dict(
                        **context,
                        metric=metric,
                        coefficient_vaxen_per_score=k,
                        coefficient_rate_per_score=k / ANCHOR,
                        ci95_vaxen_low=float(np.quantile(values, 0.025)),
                        ci95_vaxen_high=float(np.quantile(values, 0.975)),
                        valid_draws=len(samples),
                        baseline_vaxen_per_score=math.exp(base_alpha[metric]) if metric in base_alpha else "",
                        change_percent=100 * math.expm1(alpha[metric] - base_alpha[metric]) if metric in base_alpha else "",
                        score_unit=(
                            "KIPS"
                            if metric in MIX_METRICS.values()
                            else (
                                "DMIPS"
                                if metric.startswith("Dhrystone")
                                else "MWIPS" if metric.startswith("Whetstone") else "MFLOPS"
                            )
                        ),
                    )
                )
            mix_models = sorted({n["model_key"] for n in extended if n["mix_ids"]})
            for model in mix_models:
                held, _ = train(extended, edges, enabled, exclude=model)
                for n in extended:
                    if n["model_key"] != model or not n["mix_ids"]:
                        continue
                    cs = {m: v for m, v in n["log_scores"].items() if m not in MIX_METRICS.values() and m in held}
                    if not cs:
                        continue
                    w = metric_weights(cs)
                    proxy = sum(w[m] * (v + held[m]) for m, v in cs.items())
                    for metric in MIX_METRICS.values():
                        if metric not in n["log_scores"] or metric not in held:
                            continue
                        pred = n["log_scores"][metric] + held[metric]
                        holdouts.append(
                            dict(
                                **context,
                                model_key=model,
                                node_id=n["node_id"],
                                metric=metric,
                                mix_score=math.exp(n["log_scores"][metric]),
                                predicted_vaxen=math.exp(pred),
                                classical_proxy_vaxen=math.exp(proxy),
                                log_error=pred - proxy,
                                target_kind="heldout_classical_proxy_not_observed_rate",
                            )
                        )
            for metric in MIX_METRICS.values():
                selected = [r for r in holdouts if r["scenario"] == scenario and r["cohort"] == cohort and r["metric"] == metric]
                diagnostics.append(
                    dict(
                        **context,
                        metric=metric,
                        models=len({r["model_key"] for r in selected}),
                        nodes=len(selected),
                        **error_summary(selected),
                    )
                )
            # Same measured anchor population, before/after adding the mix constraints.
            for name, ns in [("baseline", baseline), ("with_mixes", extended)]:
                summary, _, _ = evaluate(ns, edges, enabled)
                anchor_summary.extend(
                    dict(**context, experiment=name, **r)
                    for r in summary
                    if r["method"] == "network" and r["subset"] == "all_available"
                )
            for r in mixes:
                metric = MIX_METRICS[r["mix"]]
                if not r["kips"] or metric not in alpha:
                    continue
                score = float(r["kips"])
                vs = np.exp(samples[:, metrics.index(metric)]) * score
                predictions.append(
                    dict(
                        **context,
                        mix_id=r["mix_id"],
                        system=r["system"],
                        metric=metric,
                        kips=score,
                        estimated_vaxen=score * math.exp(alpha[metric]),
                        estimated_rate=score * math.exp(alpha[metric]) / ANCHOR,
                        ci95_low=float(np.quantile(vs, 0.025)),
                        ci95_high=float(np.quantile(vs, 0.975)),
                        source_url=r["source_url"],
                        source_locator=r["source_locator"],
                        evidence_class="conditional_mix_model_prediction_not_SPEC_measurement",
                    )
                )
            runs.append(
                dict(
                    **context,
                    metrics=metrics,
                    valid_draws=len(samples),
                    informative_models=len(grouped),
                    mix_nodes=sum(bool(n["mix_ids"]) for n in extended),
                    mix_model_groups=len(mix_models),
                    mix_nodes_with_observed_target=sum(bool(n["mix_ids"]) and n["target_kind"] != "unanchored" for n in extended),
                )
            )
    for name, rows in [
        ("coefficients", coeffs),
        ("proxy-holdout-summary", diagnostics),
        ("proxy-holdouts", holdouts),
        ("pair-attachment-audit", link_audit),
        ("mix-nodes", node_export),
        ("anchor-comparison", anchor_summary),
        ("mix-estimates", predictions),
    ]:
        write_csv(output / (name + ".csv"), rows)
    np.savez_compressed(output / "coefficient-log-draws.npz", **arrays)
    audit = dict(
        method="instruction-mix-joint-network-v1",
        reviewed_on="2026-09-28",
        draws=draws,
        seed=seed,
        runs=runs,
        fit="Existing family/node/model-balanced sparse log least squares; original classical scores retained; InstructionMix family shares Gibson/ADP weight.",
        target="SPECrate_int92 peak * 25500/604800",
        qualification="All candidate links conditional; proxy residuals are not direct SPEC prediction errors; CI95 omits model discrepancy; no mix clock scaling; extra vendor mix variants not pooled.",
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        code_sha256=code_hashes(__file__),
    )
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    plot(output, holdouts)
    click.echo(json.dumps(dict(runs=runs, coefficients=len(coeffs), predictions=len(predictions))))


def plot(output, rows):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 2, figsize=(12, 5))
    for ax, metric in zip(axs, MIX_METRICS.values()):
        sub = [r for r in rows if r["scenario"] == "linear_clock" and r["cohort"] == "with_spec89" and r["metric"] == metric]
        x = [r["classical_proxy_vaxen"] for r in sub]
        y = [r["predicted_vaxen"] for r in sub]
        ax.scatter(x, y, alpha=0.65)
        lo = min(x + y) * 0.7
        hi = max(x + y) * 1.4
        ax.plot([lo, hi], [lo, hi], color="gray", ls="--")
        ax.set(
            xscale="log",
            yscale="log",
            title=metric,
            xlabel="Held-out classical proxy (estimated VAXen)",
            ylabel="Held-out mix prediction (estimated VAXen)",
        )
        ax.grid(alpha=0.2)
    fig.suptitle("Whole-model holdouts — reference is a classical proxy, not measured SPEC")
    fig.tight_layout()
    for ext in ["png", "svg"]:
        fig.savefig(output / ("mix-proxy-holdouts." + ext), dpi=160)
    plt.close(fig)
