"""Pooled SPECint89/92 classical composites; no implicit rate conversion."""

import hashlib
import itertools
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
import numpy as np
from cpushowspeed.classic_fit import quantile, write_csv
from cpushowspeed.classic_overlap import model_key
from cpushowspeed.classic_source_fit import read_csv

TARGETS = ("SPECint89", "SPECint92")


def bridge_rows(path):
    # utf-8-sig preserves the archive's BOM without changing its bytes.
    import csv

    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return [
        dict(r, model_key=model_key(r["system"]), log_ratio=math.log(float(r["SPECint92"]) / float(r["SPECint89"])))
        for r in rows
        if r["SPECint89"] and r["SPECint92"]
    ]


def bridge_centers(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[r["model_key"]].append(float(r["log_ratio"]))
    return {k: statistics.median(v) for k, v in groups.items()}


def composites(pairs, stage, targets=TARGETS):
    rows = []
    groups = defaultdict(list)
    for r in pairs:
        if r["stage"] != stage or r["target"] not in targets:
            continue
        metrics = r["pattern"].split("+")
        members = tuple((m, r[key + "_id"], float(r[key])) for m, key in zip(metrics, ("first", "second")))
        item = dict(r, members=members)
        rows.append(item)
        groups[r["model_key"], r["spec_id"], r["target"], r["origin"], r["y"]].append(item)
    # A triple must have all three compatible pair edges for this exact target
    # and exact classical record/value identities. Joining is not replication.
    for group in groups.values():
        edges = {frozenset(r["members"]) for r in group}
        nodes = sorted(set(itertools.chain.from_iterable(edges)))
        for combo in itertools.combinations(nodes, 3):
            if len({n[0].split(":")[0] for n in combo}) != 3:
                continue
            if all(frozenset(edge) in edges for edge in itertools.combinations(combo, 2)):
                supporting = [r for r in group if set(r["members"]).issubset(combo)]
                rows.append(
                    dict(
                        group[0],
                        pattern="+".join(n[0] for n in combo),
                        members=combo,
                        provenance=json.dumps([r["provenance"] for r in supporting]),
                    )
                )
    for r in rows:
        r["member_ids"] = json.dumps([n[1] for n in r["members"]])
        r["member_values"] = json.dumps([n[2] for n in r["members"]])
        r["x"] = math.exp(statistics.mean(math.log(n[2]) for n in r["members"]))
        r["generation"] = "89" if r["target"] == "SPECint89" else "92"
        r["raw_target"] = float(r["y"])
        r["z"] = math.log(r["raw_target"] / r["x"])
        del r["members"]
    return rows


def log_factor(rows, bridge, exclude=None):
    available = [v for k, v in bridge.items() if k != exclude]
    if not available:
        raise ValueError("No training bridge models")
    b = statistics.mean(available)
    groups = defaultdict(list)
    for r in rows:
        if r["model_key"] != exclude:
            groups[r["model_key"]].append(r["z"] + (b if r["generation"] == "89" else 0))
    if not groups:
        raise ValueError("No training fitting models")
    return statistics.mean(statistics.median(v) for v in groups.values()), b


def bootstrap_factors(rows, bridge, draws, seed, identity=False):
    """Joint model-cluster bootstrap: shared models get the same draw weight."""
    keys = sorted({r["model_key"] for r in rows} | set(bridge))
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(len(keys), np.full(len(keys), 1 / len(keys)), size=draws)
    lookup = {k: i for i, k in enumerate(keys)}
    bi = [lookup[k] for k in bridge]
    denom = weights[:, bi].sum(axis=1)
    b = np.divide(weights[:, bi] @ np.array(list(bridge.values())), denom, out=np.zeros(draws), where=denom > 0)
    if identity:
        b[:] = 0
    numerator, total = np.zeros(draws), np.zeros(draws)
    for key in sorted({r["model_key"] for r in rows}):
        group = [r for r in rows if r["model_key"] == key]
        z = np.array([r["z"] for r in group])[:, None]
        mask = np.array([r["generation"] == "89" for r in group])[:, None]
        center = np.median(z + mask * b, axis=0)
        w = weights[:, lookup[key]]
        numerator += w * center
        total += w
    valid = (total > 0) & (denom > 0)
    return np.exp(numerator[valid] / total[valid]).tolist()


def evaluate(rows, bridge, draws, seed, identity=False):
    models = sorted({r["model_key"] for r in rows})
    summary = dict(
        models=len(models),
        observations=len(rows),
        models89=len({r["model_key"] for r in rows if r["generation"] == "89"}),
        models92=len({r["model_key"] for r in rows if r["generation"] == "92"}),
        status="insufficient_models",
    )
    if len(models) < 2:
        return summary, []
    used_bridge = {k: 0.0 if identity else v for k, v in bridge.items()}
    k, b = log_factor(rows, used_bridge)
    samples = bootstrap_factors(rows, used_bridge, draws, seed, identity)
    predictions, center_errors, within = [], [], []
    for model in models:
        fold_k, fold_b = log_factor(rows, used_bridge, exclude=model)
        selected = [r for r in rows if r["model_key"] == model]
        residuals = []
        for r in selected:
            y = r["raw_target"] * math.exp(fold_b if r["generation"] == "89" else 0)
            predicted = r["x"] * math.exp(fold_k)
            residuals.append(math.log(predicted / y))
            predictions.append(
                dict(
                    model_key=model,
                    target=r["target"],
                    spec_id=r["spec_id"],
                    member_ids=r["member_ids"],
                    observed_aligned=y,
                    predicted=predicted,
                    signed_error_percent=100 * (predicted / y - 1),
                    training_bridge_factor=math.exp(fold_b),
                    training_factor=math.exp(fold_k),
                )
            )
        center_errors.append(100 * abs(math.expm1(statistics.median(residuals))))
        within.append(quantile([100 * abs(math.expm1(e)) for e in residuals], 0.95))
    summary.update(
        status="exploratory_native_integer_scale",
        factor=math.exp(k),
        bridge_factor=math.exp(b),
        factor_ci95_low=quantile(samples, 0.025),
        factor_ci95_high=quantile(samples, 0.975),
        valid_bootstrap_draws=len(samples),
        loo_model_p95_percent=quantile(center_errors, 0.95),
        loo_within_model_p95_max_percent=max(within),
    )
    return summary, predictions


def plot(output, rows, summaries, bridge_factor):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, FuncFormatter, LogLocator, NullFormatter

    patterns = sorted({r["pattern"] for r in rows})
    fig, axes = plt.subplots(math.ceil(len(patterns) / 3), 3, figsize=(17, 4 * math.ceil(len(patterns) / 3)), squeeze=False)
    for ax, pattern in zip(axes.flat, patterns):
        selected = [r for r in rows if r["pattern"] == pattern]
        fit = next(
            r for r in summaries if r["pattern"] == pattern and r["cohort"] == "pooled_aligned" and r["predictor"] == "equal_weight"
        )
        for generation, color in (("89", "#d67c24"), ("92", "#167eaf")):
            group = [r for r in selected if r["generation"] == generation]
            ax.scatter(
                [r["x"] for r in group],
                [r["raw_target"] * (bridge_factor if generation == "89" else 1) for r in group],
                s=18,
                alpha=0.5,
                color=color,
                label="SPECint" + generation,
            )
        if "factor" in fit:
            x = np.array([min(r["x"] for r in selected), max(r["x"] for r in selected)])
            ax.plot(x, x * fit["factor"], color="black")
            ax.fill_between(x, x * fit["factor_ci95_low"], x * fit["factor_ci95_high"], color="gray", alpha=0.2)
        ax.set(
            xscale="log",
            yscale="log",
            title=pattern.replace("Dhrystone:", "D ").replace("Whetstone:", "W ").replace("LINPACK:", "L ").replace("+", " +\n"),
            xlabel="Equal-weight geometric composite",
            ylabel="SPECint92-equivalent score",
        )
        xx = [r["x"] for r in selected]
        yy = [r["raw_target"] * (bridge_factor if r["generation"] == "89" else 1) for r in selected]
        ax.set_xlim(min(xx) / 1.3, max(xx) * 1.3)
        ax.set_ylim(min(yy) / 1.3, max(yy) * 1.3)
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_locator(LogLocator(base=10, subs=(1, 2, 5)))
            axis.set_minor_formatter(NullFormatter())
        for axis, values in ((ax.xaxis, xx), (ax.yaxis, yy)):
            if max(values) / min(values) < 2:
                axis.set_major_locator(FixedLocator(np.geomspace(min(values) / 1.2, max(values) * 1.2, 3)))
                axis.set_major_formatter(FuncFormatter(lambda value, pos: f"{value:.3g}"))
        ax.text(
            0.03,
            0.95,
            f"{fit['models']} models / {fit['observations']} tuples" + ("; no fit" if "factor" not in fit else ""),
            transform=ax.transAxes,
            va="top",
            fontsize=8,
        )
        ax.legend(fontsize=8, loc="lower right")
        ax.grid(alpha=0.2)
    for ax in list(axes.flat)[len(patterns) :]:
        ax.axis("off")
    fig.suptitle(
        "Classical composites → pooled SPECint89/92 (unscaled clocks)\nShading: joint model-bootstrap factor CI95; not rate-VAXen or prediction intervals"
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    for suffix in ("png", "svg"):
        fig.savefig(output / ("pooled-scatter." + suffix), dpi=150)
    plt.close(fig)


@click.command("pooled-fit")
@click.option(
    "--pairs",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/source-pair-fit/pairs.csv"),
    show_default=True,
)
@click.option(
    "--bridges",
    type=click.Path(path_type=Path, exists=True),
    default=Path("research/data/spec89/v2.0.0/csv/bridges89_92.csv"),
    show_default=True,
)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/pooled-fit"), show_default=True)
@click.option("--bootstrap", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260926, show_default=True)
def pooled_fit(pairs, bridges, output, bootstrap, seed):
    """Fit pooled native integer generations with joint bridge uncertainty."""
    output.mkdir(parents=True, exist_ok=True)
    evidence = bridge_rows(bridges)
    bridge = bridge_centers(evidence)
    source_rows = read_csv(pairs)
    rows = composites(source_rows, "plus_cross_source_unscaled")
    coverage = []
    for target in sorted({r["target"] for r in source_rows}):
        cohort = [r for r in source_rows if r["stage"] == "plus_cross_source_unscaled" and r["target"] == target]
        coverage.append(
            dict(
                target=target,
                observations=len(cohort),
                models=len({r["model_key"] for r in cohort}),
                included=target in TARGETS,
                reason="native_integer_pool" if target in TARGETS else "different_metric_not_pooled",
            )
        )
    summaries, predictions = [], []
    for pattern in sorted({r["pattern"] for r in rows}):
        selected = [r for r in rows if r["pattern"] == pattern]
        common = {r["model_key"] for r in selected if r["generation"] == "89"} & {
            r["model_key"] for r in selected if r["generation"] == "92"
        }
        for cohort in ("pooled_aligned", "pooled_identity", "89_only", "92_only", "common_89", "common_92", "common_pooled"):
            data = [
                r
                for r in selected
                if (not cohort.startswith("common_") or r["model_key"] in common)
                and (cohort not in ("89_only", "common_89") or r["generation"] == "89")
                and (cohort not in ("92_only", "common_92") or r["generation"] == "92")
            ]
            for predictor in ["equal_weight"] + pattern.split("+"):
                prepared = []
                for r in data:
                    x = (
                        r["x"]
                        if predictor == "equal_weight"
                        else json.loads(r["member_values"])[pattern.split("+").index(predictor)]
                    )
                    prepared.append(dict(r, x=x, z=math.log(r["raw_target"] / x)))
                context = dict(pattern=pattern, cohort=cohort, predictor=predictor)
                result, heldout = evaluate(prepared, bridge, bootstrap, seed, cohort == "pooled_identity")
                summaries.append(dict(context, **result))
                predictions.extend(dict(context, **r) for r in heldout)
        click.echo("Completed " + pattern, err=True)
    for name, data in [
        ("observations", rows),
        ("bridge-evidence", evidence),
        ("summary", summaries),
        ("predictions", predictions),
        ("target-coverage", coverage),
    ]:
        write_csv(output / (name + ".csv"), data)
    plot(output, rows, summaries, math.exp(statistics.mean(bridge.values())))
    ratios = [math.exp(r["log_ratio"]) for r in evidence]
    rng = np.random.default_rng(seed)
    bridge_draws = np.exp(rng.choice(list(bridge.values()), size=(bootstrap, len(bridge))).mean(axis=1))
    audit = dict(
        method="classic-pooled-native-integer-v1",
        date="2026-09-26",
        bootstrap=bootstrap,
        seed=seed,
        bridge_rows=len(evidence),
        bridge_models=len(bridge),
        bridge_factor=math.exp(statistics.mean(bridge.values())),
        bridge_ci95_low=float(np.quantile(bridge_draws, 0.025)),
        bridge_ci95_high=float(np.quantile(bridge_draws, 0.975)),
        bridge_min=min(ratios),
        bridge_max=max(ratios),
        bridge_rows_within_10pct=sum(abs(r - 1) <= 0.1 for r in ratios),
        observations=len(rows),
        comparisons=len(summaries),
        target="SPECint92-equivalent; not SPECrate or production VAXen",
        uncertainty="joint model-cluster bootstrap, shared bridge/fitting keys share weights; conditional on sources and matching",
        inputs_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (pairs, bridges)},
        code_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__), Path(__file__).with_name("classic_overlap.py"), Path(__file__).with_name("classic_fit.py"))
        },
    )
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(audit))
