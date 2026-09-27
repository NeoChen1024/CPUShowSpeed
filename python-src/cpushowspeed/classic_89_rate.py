"""Audited two-edge SPECint89-to-rate bridge and joint classical validation."""

import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
from cpushowspeed.calibration import ANCHOR, fit, quantile
from cpushowspeed.calibration_edges import bridge_log, coefficient, joint_bootstrap
from cpushowspeed.classic_bridge_data import bridge_rows
from cpushowspeed.classic_overlap import model_key, relaxed_key
from cpushowspeed.classic_vectors import composites
from cpushowspeed.research_io import code_hashes, read_csv, write_csv
from cpushowspeed.research_plot import save_figure


def evidence(specs, vectors, native_bridge):
    rows = [dict(r, edge="int89_to_int92", x=float(r["SPECint89"]), y_vaxen=float(r["SPECint92"])) for r in native_bridge]
    for v in vectors:
        t = v["targets"]
        if t.get("SPECint92") and t.get("SPECrate_int92"):
            x, y = t["SPECint92"], t["SPECrate_int92"] * ANCHOR
            rows.append(
                dict(
                    edge="int92_to_rate92",
                    model_key=v["model_key"],
                    x=x,
                    y_vaxen=y,
                    log_ratio=math.log(y / x),
                    source_url=v["source_url"],
                    pdf_page=v["pdf_page"],
                    vector_id=v["id"],
                    speed_id=v["observation_ids"]["SPECint92"],
                    rate_id=v["observation_ids"]["SPECrate_int92"],
                    raw_rate=t["SPECrate_int92"],
                    os=v["os"],
                    qualification=v["qualification"],
                )
            )
    old = [r for r in specs if r["metrics_raw"].get("SPECint89")]
    rate = [r for r in specs if r["metrics_raw"].get("SPECrate_int92")]
    # Inventory audit also includes DEC columns, even when CPU/copy counts are unknown.
    rate += [dict(system=v["machine"], clock_mhz=None) for v in vectors if v["targets"].get("SPECrate_int92")]
    counts = {}
    for label, key in [
        ("normalized_model", lambda r: model_key(r["system"])),
        ("clock_supported_relaxation", lambda r: relaxed_key(r["system"], r["clock_mhz"])),
    ]:
        a = {key(r) for r in old}
        b = {key(r) for r in rate}
        counts[label] = dict(common_models=sorted(a & b), model_count=len(a & b))
    return rows, counts


def centers(evidence_rows):
    groups = defaultdict(lambda: defaultdict(list))
    for r in evidence_rows:
        groups[r["edge"]][r["model_key"]].append(float(r["log_ratio"]))
    return {edge: {k: statistics.median(v) for k, v in models.items()} for edge, models in groups.items()}


def evaluate(rows, edges, draws, seed):
    models = sorted({r["model_key"] for r in rows})
    result = dict(
        models=len(models),
        observations=len(rows),
        models89=len({r["model_key"] for r in rows if r["generation"] == "89"}),
        models_rate=len({r["model_key"] for r in rows if r["generation"] == "92"}),
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
            residual = math.log(pred / y)
            kind = "estimated_89_target" if r["generation"] == "89" else "observed_rate_target"
            errors[kind][model].append(residual)
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
                    signed_error_percent=100 * math.expm1(residual),
                )
            )
    result.update(
        status="conditional_two_edge_bridge",
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


def plot(output, rows, summary, b):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # All patterns genuinely gaining an 89 observation; other patterns remain in CSV.
    patterns = sorted({r["pattern"] for r in rows if r["generation"] == "89"})
    fig, axes = plt.subplots(math.ceil(len(patterns) / 2), 2, figsize=(13, 4 * math.ceil(len(patterns) / 2)), squeeze=False)
    for ax, p in zip(axes.flat, patterns):
        group = [r for r in rows if r["pattern"] == p]
        for gen, color, label in [("92", "#167eaf", "Observed SPEC92 rate"), ("89", "#d67c24", "SPECint89-derived estimate")]:
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
        for cohort, color in [("rate_only", "#167eaf"), ("joint", "#222222")]:
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
            ylabel="SPEC92 integer-rate VAXen",
            title=p.replace("Dhrystone:", "D ").replace("Whetstone:", "W ").replace("LINPACK:", "L ").replace("+", " +\n"),
        )
        ax.legend(fontsize=8)
        ax.grid(alpha=0.2)
    for ax in list(axes.flat)[len(patterns) :]:
        ax.axis("off")
    fig.suptitle(
        "SPECint89 bridge + direct SPEC92 rate: joint classical fits\nTriangles are estimated targets; shading is factor CI95, not prediction interval"
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save_figure(fig, output, "joint-scatter")
    plt.close(fig)


@click.command("spec89-rate-fit")
@click.option(
    "--input-root",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/source-pair-fit"),
    show_default=True,
)
@click.option(
    "--spec-records",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/overlap-spec/spec-records.jsonl"),
    show_default=True,
)
@click.option(
    "--native-bridge",
    type=click.Path(path_type=Path, exists=True),
    default=Path("research/data/spec89/v2.0.0/csv/bridges89_92.csv"),
    show_default=True,
)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/spec89-rate-fit"), show_default=True)
@click.option("--bootstrap", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260926, show_default=True)
def spec89_rate_fit(input_root, spec_records, native_bridge, output, bootstrap, seed):
    """Estimate the two-edge SPECint89→SPECint92→rate bridge and test joint composites."""
    specs = [json.loads(x) for x in spec_records.read_text().splitlines()]
    vectors = [json.loads(x) for x in (input_root / "vectors.jsonl").read_text().splitlines()]
    ev, direct = evidence(specs, vectors, bridge_rows(native_bridge))
    edges = centers(ev)
    b = bridge_log(edges)
    _, bridge_samples = joint_bootstrap([], edges, bootstrap, seed)
    bridge_results = []
    for edge in edges:
        selected = [r for r in ev if r["edge"] == edge]
        bridge_results.append(dict(edge=edge, **fit(selected, bootstrap, seed)))
    bridge_results.append(
        dict(
            edge="int89_to_rate92_chained",
            factor=math.exp(b),
            factor_ci95_low=quantile(bridge_samples, 0.025),
            factor_ci95_high=quantile(bridge_samples, 0.975),
            pairs=0,
            status="two_edge_estimate_no_direct_pairs",
        )
    )
    rows = composites(read_csv(input_root / "pairs.csv"), "plus_cross_source_unscaled", targets=("SPECint89", "SPECrate_int92"))
    summaries, predictions = [], []
    for p in sorted({r["pattern"] for r in rows}):
        for cohort in ("rate_only", "89_only", "joint"):
            selected = [
                r
                for r in rows
                if r["pattern"] == p and (cohort == "joint" or r["generation"] == ("89" if cohort == "89_only" else "92"))
            ]
            for predictor in ["equal_weight"] + p.split("+"):
                prepared = []
                for r in selected:
                    x = r["x"] if predictor == "equal_weight" else json.loads(r["member_values"])[p.split("+").index(predictor)]
                    prepared.append(dict(r, x=x, z=math.log(r["raw_target"] / x)))
                context = dict(pattern=p, cohort=cohort, predictor=predictor)
                result, heldout = evaluate(prepared, edges, bootstrap, seed)
                summaries.append(dict(context, **result))
                predictions.extend(dict(context, **r) for r in heldout)
    for r in rows:
        r["target_kind"] = "estimated_89_target" if r["generation"] == "89" else "observed_rate_target"
        r["assigned_target_vaxen"] = r["raw_target"] * (math.exp(b) if r["generation"] == "89" else 1)
    estimates = []
    for r in specs:
        score = r["metrics_raw"].get("SPECint89")
        raw = r["raw_record"]
        if (
            not score
            or raw.get("measurement_type") == "reference_definition"
            or "reference_definition" in raw.get("review_flags", "")
        ):
            continue
        estimates.append(
            dict(
                spec_id=r["id"],
                system=r["system"],
                raw_specint89=float(score),
                estimated_rate_vaxen=float(score) * math.exp(b),
                factor_ci95_target_low=float(score) * quantile(bridge_samples, 0.025),
                factor_ci95_target_high=float(score) * quantile(bridge_samples, 0.975),
                evidence_class="two_edge_estimate",
                source_url=r["source_url"],
                provenance=json.dumps(raw, sort_keys=True),
            )
        )
    output.mkdir(parents=True, exist_ok=True)
    for name, data in [
        ("bridge-evidence", ev),
        ("bridge-summary", bridge_results),
        ("observations", rows),
        ("summary", summaries),
        ("predictions", predictions),
        ("spec89-estimates", estimates),
    ]:
        write_csv(output / (name + ".csv"), data)
    plot(output, rows, summaries, b)
    paths = [input_root / "pairs.csv", input_root / "vectors.jsonl", spec_records, native_bridge]
    audit = dict(
        method="spec89-two-edge-rate-joint-v1",
        date="2026-09-27",
        bootstrap=bootstrap,
        seed=seed,
        direct_overlap=direct,
        route=["SPECint89", "SPECint92", "SPECrate_int92 * 25500 / 604800"],
        rate_variant="peak",
        base_status="no_same_column_base_rate_bridge",
        estimate_records=len(estimates),
        estimate_models=len({model_key(r["system"]) for r in estimates}),
        comparisons=len(summaries),
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        code_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__)]
            + [
                Path(__file__).with_name(n)
                for n in ("classic_pooled.py", "classic_source_fit.py", "classic_fit.py", "classic_overlap.py")
            ]
        },
        uncertainty="joint model-cluster bootstrap across both bridge edges and classical fit; estimates not observed rate scores",
    )
    audit["shared_code_sha256"] = code_hashes(Path(__file__))
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), bridge=bridge_results, estimates=len(estimates))))
