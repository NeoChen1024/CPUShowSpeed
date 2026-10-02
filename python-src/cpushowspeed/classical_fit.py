"""Classical composites fitted to speed-VAXen (SPECint92 = 1), directly and through SPECint89, from the built database.

VAX-11/780 is the SPEC92 reference machine, so one SPECint92 speed point is one
speed-VAXen and SPECint92 targets need no conversion. SPECint89 reaches it through
the one-edge int89_to_int92 bridge. The SPECint92 → SPEC92 rate pairs are kept as a
diagnostic edge only; rate never enters a speed fit.
"""

import itertools
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
from cpushowspeed.calibration import ANCHOR, fit, quantile
from cpushowspeed.calibration_edges import bridge_log, coefficient, joint_bootstrap
from cpushowspeed.classical_store import (
    BRIDGE_SCOPE,
    SCOPES,
    family,
    node_scores,
    pairings,
    results,
    target_value,
)
from cpushowspeed.curated import DATABASE
from cpushowspeed.observation_store import connect, inputs_digest
from cpushowspeed.research_io import code_hashes, write_csv
from cpushowspeed.research_plot import save_figure

SPEED_TARGETS = ("SPECbase_int92", "SPECint92")
SPEED_EDGE = "int89_to_int92"
DIAGNOSTIC_EDGE = "int92_to_rate92"
COHORTS = ("same_result", "same_system")
FAMILY_ORDER = {"Dhrystone": 0, "Whetstone": 1, "LINPACK": 2}
DERIVED = Path("data/derived/classic")
RESEARCH = Path("research/data/classic")


def accepted_pairings(rows, scaling=False):
    index = defaultdict(list)
    for p in pairings(rows, scaling):
        if p["scores"]:
            index[p["target"].result_id].append(p)
    return index


def composite_rows(rows, targets, cohorts=COHORTS, scaling=False):
    """One row per target result, target metric, cohort and pattern of two or three benchmark families.

    Each metric's value is the median over the target's accepted pairings, so repeated
    classical rows of one system do not multiply into separate tuples. A result that
    reports SPECint92 is not also used through its SPECint89 estimate.
    """
    index = accepted_pairings(rows, scaling)
    out = []
    for t in rows:
        for metric in targets:
            value = target_value(t, metric)
            if not value or t.result_id not in index:
                continue
            if metric == "SPECint89" and "SPECint92" in targets and t.values.get("SPECint92"):
                continue
            for cohort in cohorts:
                paired = [p for p in index[t.result_id] if cohort == "same_system" or p["status"] == "same_result"]
                if not paired:
                    continue
                logs = node_scores(paired)
                members = {m: sorted({p["classical"].result_id for p in paired if m in p["scores"]}) for m in logs}
                ordered = sorted(logs, key=lambda m: (FAMILY_ORDER[family(m)], m))
                for size in (2, 3):
                    for combo in itertools.combinations(ordered, size):
                        if len({family(m) for m in combo}) != size:
                            continue
                        out.append(
                            dict(
                                cohort=cohort,
                                target=metric,
                                pattern="+".join(combo),
                                model_key=t.system_id,
                                system=t.system,
                                spec_id=t.result_id,
                                target_scope=t.scope,
                                pairing_status=";".join(sorted({p["status"] for p in paired})),
                                member_ids=json.dumps([members[m] for m in combo]),
                                member_values=json.dumps([math.exp(logs[m]) for m in combo]),
                                x=math.exp(statistics.mean(logs[m] for m in combo)),
                                y=value,
                                generation="89" if metric == "SPECint89" else "92",
                                source_url=t.source_url,
                            )
                        )
    return out


def _load(database):
    with connect(database) as db:
        return results(db, SCOPES + (BRIDGE_SCOPE,)), inputs_digest(db)


def _audit(path, **content):
    path.write_text(json.dumps(dict(content, shared_code_sha256=code_hashes(Path(__file__))), indent=2) + "\n")


def _predictor_rows(data, pattern, predictor):
    for r in data:
        x = r["x"] if predictor == "equal_weight" else json.loads(r["member_values"])[pattern.split("+").index(predictor)]
        yield dict(r, x=x)


def composite_calculate(rows, bootstrap, seed):
    groups = defaultdict(list)
    for r in rows:
        groups[r["cohort"], r["target"], r["pattern"]].append(r)
    summaries, predictions = [], []
    for (cohort, target, pattern), data in sorted(groups.items()):
        for predictor in ["equal_weight"] + pattern.split("+"):
            prepared = list(_predictor_rows(data, pattern, predictor))
            context = dict(
                cohort=cohort,
                target=target,
                variant="base" if target == SPEED_TARGETS[0] else "peak",
                pattern=pattern,
                predictor=predictor,
                target_unit="speed-VAXen (SPECint92 = 1)",
            )
            summaries.append(dict(context, **fit(prepared, bootstrap, seed)))
            by_model = defaultdict(list)
            for r in prepared:
                by_model[r["model_key"]].append(r)
            centers = {k: statistics.median(math.log(r["y_vaxen"] / r["x"]) for r in group) for k, group in by_model.items()}
            if len(centers) < 2:
                continue
            for model, group in sorted(by_model.items()):
                k = math.exp(statistics.mean(v for key, v in centers.items() if key != model))
                for r in group:
                    predictions.append(
                        dict(
                            context,
                            model_key=model,
                            spec_id=r["spec_id"],
                            member_ids=r["member_ids"],
                            observed_vaxen=r["y_vaxen"],
                            predicted_vaxen=k * r["x"],
                            training_factor=k,
                            signed_error_percent=100 * (k * r["x"] / r["y_vaxen"] - 1),
                        )
                    )
    return summaries, predictions


def composite_plot(output, rows, summaries):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter

    for target in SPEED_TARGETS:
        selected = [r for r in rows if r["cohort"] == "same_system" and r["target"] == target]
        patterns = sorted({r["pattern"] for r in selected})
        if not patterns:
            continue
        fig, axes = plt.subplots(math.ceil(len(patterns) / 3), 3, figsize=(17, 4 * math.ceil(len(patterns) / 3)), squeeze=False)
        for ax, pattern in zip(axes.flat, patterns):
            data = [r for r in selected if r["pattern"] == pattern]
            result = next(
                r
                for r in summaries
                if r["cohort"] == "same_system"
                and r["target"] == target
                and r["pattern"] == pattern
                and r["predictor"] == "equal_weight"
            )
            same = [r for r in data if r["pairing_status"] == "same_result"]
            other = [r for r in data if r["pairing_status"] != "same_result"]
            for group, color, label in ((same, "#167eaf", "same report column"), (other, "#d67c24", "same system, other source")):
                if group:
                    ax.scatter([r["x"] for r in group], [r["y_vaxen"] for r in group], s=18, alpha=0.55, label=label, color=color)
            if "factor" in result:
                xx = [min(r["x"] for r in data) * 0.85, max(r["x"] for r in data) * 1.15]
                ax.plot(xx, [x * result["factor"] for x in xx], color="black")
                ax.fill_between(
                    xx,
                    [x * result["factor_ci95_low"] for x in xx],
                    [x * result["factor_ci95_high"] for x in xx],
                    color="gray",
                    alpha=0.2,
                )
            title = pattern.replace("Dhrystone:", "D ").replace("Whetstone:", "W ").replace("LINPACK:", "L ").replace("+", " +\n")
            ax.set(
                xscale="log",
                yscale="log",
                title=title,
                xlabel="Equal-weight geometric composite",
                ylabel="speed-VAXen (SPECint92)",
            )
            ax.xaxis.set_minor_formatter(NullFormatter())
            ax.yaxis.set_minor_formatter(NullFormatter())
            ax.text(
                0.03, 0.96, f"{result['models']} systems / {result['pairs']} targets", transform=ax.transAxes, va="top", fontsize=8
            )
            ax.legend(fontsize=7, loc="lower right")
            ax.grid(alpha=0.2)
        for ax in list(axes.flat)[len(patterns) :]:
            ax.axis("off")
        variant = "base" if target == SPEED_TARGETS[0] else "peak"
        fig.suptitle(
            f"Classical composites → SPECint92 speed — {variant}\n"
            "Paired by resolved system; shading: factor CI95, not prediction interval"
        )
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        save_figure(fig, output, f"composite-{variant}")
        plt.close(fig)


@click.command("composite-fit")
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
@click.option("--output", type=click.Path(path_type=Path), default=DERIVED / "composite-fit", show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=RESEARCH, show_default=True)
@click.option("--bootstrap", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260926, show_default=True)
def composite_fit(database, output, research_dir, bootstrap, seed):
    """Fit two/three classical families directly to speed-VAXen (SPECint92), base and peak separately."""
    rows_, digest = _load(database)
    rows = composite_rows(rows_, SPEED_TARGETS)
    for r in rows:
        r["y_vaxen"] = r.pop("y")
        r["variant"] = "base" if r["target"] == SPEED_TARGETS[0] else "peak"
    summaries, predictions = composite_calculate(rows, bootstrap, seed)
    coverage = [
        dict(
            cohort=cohort,
            target=target,
            target_results=len({r["spec_id"] for r in rows if r["cohort"] == cohort and r["target"] == target}),
            systems=len({r["model_key"] for r in rows if r["cohort"] == cohort and r["target"] == target}),
        )
        for cohort in COHORTS
        for target in SPEED_TARGETS
    ]
    output.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)
    for name, data in [("observations", rows), ("summary", summaries), ("predictions", predictions), ("target-coverage", coverage)]:
        write_csv(output / (name + ".csv"), data)
    write_csv(research_dir / "composite-summary.csv", summaries)
    write_csv(research_dir / "composite-target-coverage.csv", coverage)
    composite_plot(output, rows, summaries)
    _audit(
        research_dir / "composite-audit.json",
        method="classic-direct-speed-composites-v3-resolved-systems",
        bootstrap=bootstrap,
        seed=seed,
        primary_cohort="same_system",
        comparison_cohort="same_result",
        target_unit="speed-VAXen: one SPECint92 speed point (VAX-11/780 = 1)",
        pairing="same resolved system_id; reported clocks must agree within 1% when both are known; no clock scaling; reviewed result_pair rejections drop a pairing and acceptances admit it",
        inputs_sha256=digest,
        target_rows=len(rows),
        comparisons=len(summaries),
        uncertainty="system-cluster bootstrap; conditional on sources, system resolution, configurations and unit interpretation",
    )
    click.echo(json.dumps(dict(output=str(output), comparisons=len(summaries), rows=len(rows))))


def bridge_evidence(rows):
    """Same-result SPEC suite pairs: SPECint89 with SPECint92 (the speed bridge), and SPECint92 with
    SPEC92 integer rate in rate-VAXen (a diagnostic of the two quantities; never chained)."""
    evidence = []
    for r in rows:
        v = r.values
        if not r.system_id or r.reference:
            continue
        if r.scope == BRIDGE_SCOPE and v.get("SPECint89") and v.get("SPECint92"):
            x, y, edge = v["SPECint89"], v["SPECint92"], SPEED_EDGE
        elif r.scope != BRIDGE_SCOPE and v.get("SPECint92") and target_value(r, "SPECrate_int92"):
            x, y, edge = v["SPECint92"], v["SPECrate_int92"] * ANCHOR, DIAGNOSTIC_EDGE
        else:
            continue
        evidence.append(
            dict(
                edge=edge,
                model_key=r.system_id,
                system=r.system,
                result_id=r.result_id,
                x=x,
                y_vaxen=y,
                log_ratio=math.log(y / x),
                os=r.os,
                source_url=r.source_url,
            )
        )
    return evidence


def centers(evidence):
    groups = defaultdict(lambda: defaultdict(list))
    for r in evidence:
        groups[r["edge"]][r["model_key"]].append(float(r["log_ratio"]))
    return {edge: {k: statistics.median(v) for k, v in models.items()} for edge, models in sorted(groups.items())}


def speed_edges(evidence):
    """The SPECint89 → speed-VAXen bridge: the int89_to_int92 edge's model centers alone."""
    edges = centers(evidence)
    if SPEED_EDGE not in edges:
        raise ValueError("no SPECint89/SPECint92 bridge evidence")
    return {SPEED_EDGE: edges[SPEED_EDGE]}


def evaluate(rows, edges, draws, seed):
    models = sorted({r["model_key"] for r in rows})
    result = dict(
        models=len(models),
        observations=len(rows),
        models89=len({r["model_key"] for r in rows if r["generation"] == "89"}),
        models92=len({r["model_key"] for r in rows if r["generation"] == "92"}),
        status="insufficient_models",
    )
    if len(models) < 2:
        return result, []
    k, b = coefficient(rows, edges)
    samples, _ = joint_bootstrap(rows, edges, draws, seed)
    predictions = []
    errors = defaultdict(lambda: defaultdict(list))
    for model in models:
        fk, fb = coefficient(rows, edges, exclude=model)
        for r in rows:
            if r["model_key"] != model:
                continue
            y = r["raw_target"] * math.exp(fb if r["generation"] == "89" else 0)
            pred = r["x"] * math.exp(fk)
            kind = "estimated_89_target" if r["generation"] == "89" else "observed_speed_target"
            errors[kind][model].append(math.log(pred / y))
            predictions.append(
                dict(
                    model_key=model,
                    spec_id=r["spec_id"],
                    member_ids=r["member_ids"],
                    target_kind=kind,
                    evaluation_target_vaxen=y,
                    predicted_vaxen=pred,
                    training_bridge_factor=math.exp(fb),
                    training_factor=math.exp(fk),
                    signed_error_percent=100 * math.expm1(math.log(pred / y)),
                )
            )
    result.update(
        status="conditional_one_edge_bridge",
        factor=math.exp(k),
        bridge_factor=math.exp(b),
        factor_ci95_low=quantile(samples, 0.025),
        factor_ci95_high=quantile(samples, 0.975),
        valid_bootstrap_draws=len(samples),
    )
    for kind, groups in errors.items():
        result[kind + "_models"] = len(groups)
        result[kind + "_p95_percent"] = quantile([100 * abs(math.expm1(statistics.median(v))) for v in groups.values()], 0.95)
        result[kind + "_within_model_p95_max_percent"] = max(
            quantile([100 * abs(math.expm1(e)) for e in v], 0.95) for v in groups.values()
        )
    return result, predictions


def spec89_plot(output, rows, summary, b):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    patterns = sorted({r["pattern"] for r in rows if r["generation"] == "89"})
    if not patterns:
        return
    fig, axes = plt.subplots(math.ceil(len(patterns) / 2), 2, figsize=(13, 4 * math.ceil(len(patterns) / 2)), squeeze=False)
    for ax, p in zip(axes.flat, patterns):
        group = [r for r in rows if r["pattern"] == p]
        for gen, color, label in [("92", "#167eaf", "Observed SPECint92"), ("89", "#d67c24", "SPECint89-derived estimate")]:
            selected = [r for r in group if r["generation"] == gen]
            if selected:
                ax.scatter(
                    [r["x"] for r in selected],
                    [r["raw_target"] * (math.exp(b) if gen == "89" else 1) for r in selected],
                    s=20,
                    alpha=0.5,
                    label=label,
                    color=color,
                    marker="o" if gen == "92" else "^",
                )
        for cohort, color in [("spec92_only", "#167eaf"), ("joint", "#222222")]:
            result = next(r for r in summary if r["pattern"] == p and r["cohort"] == cohort and r["predictor"] == "equal_weight")
            if "factor" not in result:
                continue
            xx = [min(r["x"] for r in group) * 0.9, max(r["x"] for r in group) * 1.1]
            ax.plot(xx, [x * result["factor"] for x in xx], color=color, label=cohort)
            if cohort == "joint":
                ax.fill_between(
                    xx,
                    [x * result["factor_ci95_low"] for x in xx],
                    [x * result["factor_ci95_high"] for x in xx],
                    color=color,
                    alpha=0.12,
                )
        ax.set(
            xscale="log",
            yscale="log",
            xlabel="Equal-weight composite",
            ylabel="speed-VAXen (SPECint92)",
            title=p.replace("Dhrystone:", "D ").replace("Whetstone:", "W ").replace("LINPACK:", "L ").replace("+", " +\n"),
        )
        ax.legend(fontsize=8)
        ax.grid(alpha=0.2)
    for ax in list(axes.flat)[len(patterns) :]:
        ax.axis("off")
    fig.suptitle(
        "SPECint89 bridge + direct SPECint92: joint classical fits\n"
        "Triangles are estimated targets; shading is factor CI95, not prediction interval"
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save_figure(fig, output, "joint-scatter")
    plt.close(fig)


@click.command("spec89-fit")
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
@click.option("--output", type=click.Path(path_type=Path), default=DERIVED / "spec89-fit", show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=RESEARCH, show_default=True)
@click.option("--bootstrap", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260926, show_default=True)
def spec89_fit(database, output, research_dir, bootstrap, seed):
    """Estimate the SPECint89→SPECint92 speed bridge and test joint composites in speed-VAXen."""
    rows_, digest = _load(database)
    ev = bridge_evidence(rows_)
    try:
        edges = speed_edges(ev)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    b = bridge_log(edges)
    _, bridge_samples = joint_bootstrap([], edges, bootstrap, seed)
    # The rate edge is reported beside the bridge as a diagnostic of speed versus rate.
    bridge_results = [
        dict(edge=edge, role="speed_bridge" if edge == SPEED_EDGE else "diagnostic_not_chained", **fit(group, bootstrap, seed))
        for edge in sorted({r["edge"] for r in ev})
        for group in [[r for r in ev if r["edge"] == edge]]
    ]
    low, high = quantile(bridge_samples, 0.025), quantile(bridge_samples, 0.975)
    rows = composite_rows(rows_, ("SPECint89", "SPECint92"), cohorts=("same_system",))
    for r in rows:
        r["raw_target"] = r.pop("y")
        r["z"] = math.log(r["raw_target"] / r["x"])
    summaries, predictions = [], []
    for p in sorted({r["pattern"] for r in rows}):
        for cohort in ("spec92_only", "89_only", "joint"):
            selected = [
                r
                for r in rows
                if r["pattern"] == p and (cohort == "joint" or r["generation"] == ("89" if cohort == "89_only" else "92"))
            ]
            for predictor in ["equal_weight"] + p.split("+"):
                prepared = [dict(r, z=math.log(r["raw_target"] / r["x"])) for r in _predictor_rows(selected, p, predictor)]
                context = dict(pattern=p, cohort=cohort, predictor=predictor)
                result, heldout = evaluate(prepared, edges, bootstrap, seed)
                summaries.append(dict(context, **result))
                predictions.extend(dict(context, **r) for r in heldout)
    for r in rows:
        r["target_kind"] = "estimated_89_target" if r["generation"] == "89" else "observed_speed_target"
        r["assigned_target_vaxen"] = r["raw_target"] * (math.exp(b) if r["generation"] == "89" else 1)
    estimates = [
        dict(
            spec_id=r.result_id,
            system=r.system,
            system_id=r.system_id,
            raw_specint89=r.values["SPECint89"],
            estimated_speed_vaxen=r.values["SPECint89"] * math.exp(b),
            factor_ci95_target_low=r.values["SPECint89"] * low,
            factor_ci95_target_high=r.values["SPECint89"] * high,
            evidence_class="one_edge_estimate",
            source_url=r.source_url,
        )
        for r in rows_
        if r.scope == "historical-spec:spec89" and r.values.get("SPECint89") and not r.reference
    ]
    old = {r.system_id for r in rows_ if r.system_id and r.values.get("SPECint89") and not r.reference}
    new = {r.system_id for r in rows_ if r.system_id and r.values.get("SPECint92") and r.scope != BRIDGE_SCOPE}
    output.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)
    for name, data in [
        ("bridge-evidence", ev),
        ("bridge-summary", bridge_results),
        ("observations", rows),
        ("summary", summaries),
        ("predictions", predictions),
        ("spec89-estimates", estimates),
    ]:
        write_csv(output / (name + ".csv"), data)
    for name, data in [
        ("spec89-bridge-evidence", ev),
        ("spec89-bridge-summary", bridge_results),
        ("spec89-summary", summaries),
        ("spec89-estimates", estimates),
    ]:
        write_csv(research_dir / (name + ".csv"), data)
    spec89_plot(output, rows, summaries, b)
    _audit(
        research_dir / "spec89-audit.json",
        method="spec89-one-edge-speed-joint-v3-resolved-systems",
        bootstrap=bootstrap,
        seed=seed,
        route=["SPECint89", "SPECint92 = speed-VAXen"],
        edge_sources=dict(int89_to_int92=BRIDGE_SCOPE),
        diagnostic_edges=dict(int92_to_rate92="results reporting both values (DEC N3909 columns); reported, never chained"),
        bridge_factor=math.exp(b),
        bridge_factor_ci95=[low, high],
        direct_overlap=dict(systems_with_specint89_and_specint92=sorted(old & new), count=len(old & new)),
        target_variant="peak",
        estimate_records=len(estimates),
        estimate_systems=len({r["system_id"] for r in estimates}),
        comparisons=len(summaries),
        inputs_sha256=digest,
        uncertainty="joint system-cluster bootstrap across the bridge edge and classical fit; estimates are not observed SPECint92 scores",
    )
    click.echo(json.dumps(dict(output=str(output), bridge=bridge_results, estimates=len(estimates))))
