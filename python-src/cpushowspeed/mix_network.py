"""Instruction-mix ratings joined to the sparse classical network over resolved systems, from the built database.

A Gibson or ADP rating attaches to every network node of its resolved system
(`resolved_system`), or additionally of systems a review leaves linked as
`needs_review` (`plus_pending_links`). Nodes sharing one attached rating form one
bootstrap/holdout cluster. Gibson and ADP share one family weight and one power-law
exponent. The fit is the classical network's (`classic_network_model.train`), whose
classical families pass through the VAX-11/780; the 780 has no mix rating, so each mix
keeps a free intercept. Mix calibrations are therefore conditional on the classical
calibration and on unapproved system links.
"""

import copy
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
import numpy as np
from cpushowspeed.calibration import error_summary
from cpushowspeed.classic_network import build, evaluate, vax780_anchor
from cpushowspeed.classic_network_model import (
    bootstrap,
    bridge_log,
    metric_weights,
    train,
)
from cpushowspeed.classical_fit import DERIVED, RESEARCH, bridge_evidence, speed_edges
from cpushowspeed.classical_store import BRIDGE_SCOPE, SCOPES, family, results
from cpushowspeed.curated import DATABASE
from cpushowspeed.mix_bridge import MIX_SCOPE, _rows, pending_links
from cpushowspeed.observation_store import connect, inputs_digest
from cpushowspeed.research_io import code_hashes, write_csv

METHOD_VERSION = "instruction-mix-joint-network-v4-family-power-law"
MIX_METRICS = ("InstructionMix:Gibson_KIPS", "InstructionMix:ADP_KIPS")
LINKS = ("resolved_system", "plus_pending_links")
TIMELINE_RUN = dict(links="plus_pending_links", scenario="linear_clock", cohort="with_spec89")
OUTPUT = DERIVED / "mix-network-fit"


def mix_results(db):
    """Every positive mix rating with its resolved system and the source table row it shares with its sibling rating."""
    out = []
    for rid, system, system_id, metric, value, url in _rows(db, MIX_SCOPE):
        if metric in MIX_METRICS and value > 0:
            out.append(
                dict(
                    result_id=rid,
                    row_id=rid.rsplit(":", 1)[0],
                    system=system,
                    system_id=system_id or "",
                    metric=metric,
                    kips=value,
                    source_url=url,
                )
            )
    return out


def attach(nodes, edges, mixes, links, tier):
    """Copies of the nodes and bridge edges with mix scores attached and linked model keys merged, plus the audit."""
    by_model = defaultdict(list)
    for n in nodes:
        by_model[n["model_key"]].append(n)
    parent = {}

    def find(k):
        parent.setdefault(k, k)
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    additions, audit = defaultdict(lambda: defaultdict(list)), []
    for m in mixes:
        systems = {m["system_id"]} if m["system_id"] else set()
        if tier == "plus_pending_links":
            systems |= links.get(m["system_id"], set())
        matched = [n for s in sorted(systems) for n in by_model.get(s, [])]
        for n in matched:
            additions[n["node_id"]][m["metric"]].append(math.log(m["kips"]))
        keys = sorted({n["model_key"] for n in matched})
        for k in keys[1:]:
            a, b = find(keys[0]), find(k)
            if a != b:
                parent[max(a, b)] = min(a, b)
        audit.append(
            dict(
                links=tier,
                mix_result_id=m["result_id"],
                metric=m["metric"],
                system_id=m["system_id"],
                linked_systems=";".join(sorted(systems - {m["system_id"]})),
                attached_nodes=len(matched),
                node_ids=";".join(n["node_id"] for n in matched),
                status="attached" if matched else "no_classical_node",
            )
        )
    extended, baseline = copy.deepcopy(nodes), copy.deepcopy(nodes)
    for n in extended:
        n["mix_metrics"] = sorted(additions[n["node_id"]])
        for metric, logs in additions[n["node_id"]].items():
            n["log_scores"][metric] = statistics.median(logs)
    for n in extended + baseline:
        n["model_key"] = find(n["model_key"])
    merged = {}
    for e, models in edges.items():
        grouped = defaultdict(list)
        for k, v in models.items():
            grouped[find(k)].append(v)
        merged[e] = {k: statistics.median(v) for k, v in grouped.items()}
    return extended, baseline, merged, audit


def holdouts(nodes, edges, enabled, anchor, context):
    """Whole-cluster holdouts of mix-only predictions against the observed target and the classical proxy."""
    rows = []
    for model in sorted({n["model_key"] for n in nodes if n["mix_metrics"]}):
        held, _ = train(nodes, edges, enabled, anchor, exclude=model)
        b = bridge_log(edges, exclude=model) if enabled else 0.0
        for n in nodes:
            if n["model_key"] != model or not n["mix_metrics"]:
                continue
            mixes = {m: v for m, v in n["log_scores"].items() if m in MIX_METRICS and m in held}
            if not mixes:
                continue
            w = metric_weights(mixes)
            predicted = sum(w[m] * (held[m][0] + held[m][1] * v) for m, v in mixes.items())
            classical = {m: v for m, v in n["log_scores"].items() if family(m) != "InstructionMix" and m in held}
            references = []
            if classical:
                wc = metric_weights(classical)
                references.append(("classical_proxy", sum(wc[m] * (held[m][0] + held[m][1] * v) for m, v in classical.items())))
            if n["target_kind"] == "observed_speed" or (enabled and n["target_kind"] == "estimated_89"):
                references.append(("observed_target", math.log(n["target"]) + (b if n["target_kind"] == "estimated_89" else 0)))
            for reference, y in references:
                rows.append(
                    dict(
                        context,
                        model_key=model,
                        node_id=n["node_id"],
                        system=n["system"],
                        target_kind=n["target_kind"],
                        reference=reference,
                        mix_metrics=";".join(sorted(mixes)),
                        predicted_vaxen=math.exp(predicted),
                        reference_vaxen=math.exp(y),
                        log_error=predicted - y,
                    )
                )
    return rows


def estimates(mixes, calib, metrics, intercepts, exponents, context):
    """Each rating, and each source row's available-mix combination, with CI95 from aligned coefficient draws."""
    single, rows = [], defaultdict(list)

    def point_log(m):
        a, b = calib[m["metric"]]
        return a + b * math.log(m["kips"])

    for m in mixes:
        if m["metric"] not in calib:
            continue
        i = metrics.index(m["metric"])
        logs = intercepts[:, i] + exponents[:, i] * math.log(m["kips"])
        rows[m["row_id"]].append((m, logs))
        single.append(dict(context, kind="single", record_id=m["result_id"], **_value(math.exp(point_log(m)), logs, [m])))
    combined = []
    for row_id, members in sorted(rows.items()):
        point = statistics.mean(point_log(m) for m, _ in members)
        logs = np.mean([v for _, v in members], axis=0)
        combined.append(dict(context, kind="combined", record_id=row_id, **_value(math.exp(point), logs, [m for m, _ in members])))
    return single + combined


def _value(vaxen, logs, members):
    return dict(
        result_ids=json.dumps([m["result_id"] for m in members]),
        system=members[0]["system"],
        system_id=members[0]["system_id"],
        scores=json.dumps({m["metric"]: m["kips"] for m in members}, sort_keys=True),
        source_url=members[0]["source_url"],
        estimated_vaxen=vaxen,
        ci95_low=float(np.exp(np.quantile(logs, 0.025))),
        ci95_high=float(np.exp(np.quantile(logs, 0.975))),
        combination="equal_log_weight" if len(members) > 1 else "single_available",
    )


@click.command("mix-network-fit")
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
@click.option("--output", type=click.Path(path_type=Path), default=OUTPUT, show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=RESEARCH, show_default=True)
@click.option("--bootstrap", "draws", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260928, show_default=True)
def mix_network_fit(database, output, research_dir, draws, seed):
    """Jointly calibrate Gibson/ADP ratings with the classical network to speed-VAXen (SPECint92 = 1)."""
    with connect(database) as db:
        rows = results(db, SCOPES + (BRIDGE_SCOPE,))
        mixes = mix_results(db)
        links = pending_links(db)
        digest = inputs_digest(db)
    edges = speed_edges(bridge_evidence(rows))
    anchor, anchor_sd, _ = vax780_anchor(rows)
    coefficients, summary, held_rows, attach_rows, anchors, predictions, runs, arrays = [], [], [], [], [], [], [], {}
    for scaling in (False, True):
        scenario = "linear_clock" if scaling else "reported_clock"
        nodes, _, _ = build(rows, scaling)
        for tier in LINKS:
            extended, baseline, merged, audit = attach(nodes, edges, mixes, links, tier)
            if scaling:
                attach_rows.extend(audit)
            for enabled in (False, True):
                cohort = "with_spec89" if enabled else "spec92_only"
                context = dict(links=tier, scenario=scenario, cohort=cohort)
                click.echo(f"Fitting {tier} / {scenario} / {cohort}", err=True)
                calib, grouped = train(extended, merged, enabled, anchor)
                base, _ = train(baseline, merged, enabled, anchor)
                metrics, intercepts, exponents = bootstrap(extended, merged, enabled, anchor, anchor_sd, draws, seed)
                key = "__".join((tier, scenario, cohort))
                arrays[key + "__intercept"] = intercepts
                arrays[key + "__exponent"] = exponents
                for i, metric in enumerate(metrics):
                    coefficients.append(
                        dict(
                            context,
                            metric=metric,
                            exponent=calib[metric][1],
                            exponent_ci95_low=float(np.quantile(exponents[:, i], 0.025)),
                            exponent_ci95_high=float(np.quantile(exponents[:, i], 0.975)),
                            vaxen_at_unit_score=math.exp(calib[metric][0]),
                            unit_score_ci95_low=float(np.exp(np.quantile(intercepts[:, i], 0.025))),
                            unit_score_ci95_high=float(np.exp(np.quantile(intercepts[:, i], 0.975))),
                            vax780_anchored=metric in anchor,
                            valid_draws=len(intercepts),
                            classical_only_exponent=base[metric][1] if metric in base else "",
                            classical_only_vaxen_at_unit_score=math.exp(base[metric][0]) if metric in base else "",
                        )
                    )
                held = holdouts(extended, merged, enabled, anchor, context)
                held_rows.extend(held)
                for reference in ("observed_target", "classical_proxy"):
                    selected = [r for r in held if r["reference"] == reference]
                    summary.append(
                        dict(
                            context,
                            reference=reference,
                            models=len({r["model_key"] for r in selected}),
                            nodes=len(selected),
                            **error_summary(selected),
                        )
                    )
                for name, ns in (("classical_only", baseline), ("with_mixes", extended)):
                    s, _, _ = evaluate(ns, merged, enabled, anchor, methods=("network",))
                    anchors.extend(
                        dict(context, experiment=name, **r)
                        for r in s
                        if r["method"] == "network" and r["subset"] == "all_available" and r["scope"] == "all_available_nodes"
                    )
                predictions.extend(estimates(mixes, calib, metrics, intercepts, exponents, context))
                runs.append(
                    dict(
                        context,
                        draw_key=key,
                        metrics=metrics,
                        valid_draws=len(intercepts),
                        informative_models=len(grouped),
                        mix_nodes=sum(bool(n["mix_metrics"]) for n in extended),
                        mix_models=len({n["model_key"] for n in extended if n["mix_metrics"]}),
                        mix_nodes_with_observed_speed=sum(
                            bool(n["mix_metrics"]) and n["target_kind"] == "observed_speed" for n in extended
                        ),
                        attached_ratings=sum(r["status"] == "attached" for r in audit),
                    )
                )
    output.mkdir(parents=True, exist_ok=True)
    for name, data in (
        ("coefficients", coefficients),
        ("holdout-summary", summary),
        ("holdouts", held_rows),
        ("attachment-audit", attach_rows),
        ("anchor-comparison", anchors),
        ("mix-estimates", predictions),
    ):
        write_csv(output / (name + ".csv"), data)
    np.savez_compressed(output / "coefficient-log-draws.npz", **arrays)
    write_csv(research_dir / "mix-network-coefficients.csv", coefficients)
    write_csv(research_dir / "mix-network-holdout-summary.csv", summary)
    write_csv(research_dir / "mix-network-anchor-comparison.csv", anchors)
    audit = dict(
        method=METHOD_VERSION,
        draws=draws,
        seed=seed,
        runs=runs,
        timeline_run=TIMELINE_RUN,
        fit="classical network (family power laws through the VAX-11/780; family/variant/node/model balanced sparse log least squares) with Gibson/ADP sharing the InstructionMix family weight and exponent; mix intercepts free (the 780 has no mix rating)",
        attachment="a rating attaches to every node of its resolved system, or also of needs_review linked systems; nodes sharing a rating form one cluster",
        target="speed-VAXen: SPECint92 peak (VAX-11/780 = 1); SPECint89 through the int89_to_int92 bridge",
        qualification="all system links unapproved; observed-target holdouts exist only where a mix system has a SPEC target; CI95 omits model discrepancy; no mix clock scaling",
        inputs_sha256=digest,
        code_sha256=code_hashes(Path(__file__)),
    )
    for path in (output / "audit.json", research_dir / "mix-network-audit.json"):
        path.write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(runs=runs, coefficients=len(coefficients), estimates=len(predictions))))
