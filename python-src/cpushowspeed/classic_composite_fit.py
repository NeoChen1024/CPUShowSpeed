"""Equal-weight composite and single-score baselines on identical model folds."""

import csv
import hashlib
import itertools
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
from cpushowspeed.classic_composite import TARGETS
from cpushowspeed.classic_fit import ANCHOR, fit, quantile, write_csv

SCENARIOS = ("candidate_known_clocks", "candidate_unknown_clock_allowed", "candidate_linear_clock_scaling")
PREDICTORS = ("equal_weight", "dhrystone", "whetstone", "linpack")


def inputs(vector, scenario):
    scaled = scenario == "candidate_linear_clock_scaling"
    d = float(vector["dhrystone_adjusted"] if scaled else vector["dhrystone"])
    w = float(vector["whetstone_adjusted"] if scaled else vector["whetstone_score"])
    l = float(vector["linpack"])
    if min(d, w, l) <= 0:
        raise ValueError("Composite requires three positive observed/adjusted inputs")
    # Fixed unit normalizers: 1 DMIPS, 1 MWIPS, 1 MFLOPS. No fitted weights.
    return dict(equal_weight=math.exp((math.log(d) + math.log(w) + math.log(l)) / 3), dhrystone=d, whetstone=w, linpack=l)


def compare(vectors, bootstrap=10000, seed=20260926):
    summaries, folds, observations = [], [], []
    for target, whet, scenario in itertools.product(TARGETS, ("MWIPS", "MWIPS_DP"), SCENARIOS):
        selected = [v for v in vectors if v["target"] == target and v["whetstone"] == whet and str(v[scenario]).lower() == "true"]
        for predictor in PREDICTORS:
            context = dict(
                target=target,
                whetstone=whet,
                scenario=scenario,
                predictor=predictor,
                target_unit="SPEC92 rate-VAXen" if target.startswith("SPECrate") else target + " raw score",
            )
            rows = []
            for v in selected:
                row = dict(
                    v,
                    x=inputs(v, scenario)[predictor],
                    y_vaxen=float(v["spec_score"]) * (ANCHOR if target.startswith("SPECrate") else 1),
                )
                rows.append(row)
            result = fit(rows, bootstrap, seed)
            # All predictors use exactly the same tuple multiset and model folds.
            groups = defaultdict(list)
            for row in rows:
                groups[row["model_key"]].append(row)
            centers = {k: statistics.median(math.log(r["y_vaxen"] / r["x"]) for r in group) for k, group in groups.items()}
            model_errors = []
            for model, group in sorted(groups.items()):
                training = [c for k, c in centers.items() if k != model]
                if not training:
                    continue
                log_factor = statistics.mean(training)
                error = 100 * math.expm1(log_factor - centers[model])
                model_errors.append(abs(error))
                folds.append(
                    dict(
                        context,
                        heldout_model=model,
                        training_models=len(training),
                        heldout_tuples=len(group),
                        factor=math.exp(log_factor),
                        center_observed_ratio=math.exp(centers[model]),
                        signed_center_error_percent=error,
                        absolute_center_error_percent=abs(error),
                    )
                )
                for row in group:
                    predicted = math.exp(log_factor) * row["x"]
                    observations.append(
                        dict(
                            context,
                            heldout_model=model,
                            spec_id=row["spec_id"],
                            dhrystone_id=row["dhrystone_id"],
                            whetstone_id=row["whetstone_id"],
                            linpack_id=row["linpack_id"],
                            x=row["x"],
                            observed=row["y_vaxen"],
                            predicted=predicted,
                            signed_error_percent=100 * (predicted / row["y_vaxen"] - 1),
                        )
                    )
            if model_errors:
                result.update(loo_model_median_percent=statistics.median(model_errors), loo_model_max_percent=max(model_errors))
            summaries.append(dict(context, **result))
    return summaries, folds, observations


def plot(output, folds):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    colors = ("#222222", "#1875aa", "#e58b28", "#458750")
    for ax, (whet, scenario) in zip(axes.flat, itertools.product(("MWIPS", "MWIPS_DP"), SCENARIOS[1:])):
        rows = [r for r in folds if r["target"] == "SPECrate_int92" and r["whetstone"] == whet and r["scenario"] == scenario]
        models = sorted({r["heldout_model"] for r in rows})
        for j, (predictor, color) in enumerate(zip(PREDICTORS, colors)):
            ys = [
                next(r["absolute_center_error_percent"] for r in rows if r["heldout_model"] == m and r["predictor"] == predictor)
                for m in models
            ]
            ax.plot(range(len(models)), ys, marker="o", color=color, label=predictor.replace("_", " "), alpha=0.8)
        ax.set_xticks(range(len(models)), [m.removeprefix("dec") for m in models], rotation=25)
        ax.set_ylabel("Held-out model-center absolute error (%)")
        ax.set_title(whet + (" | linear clock adjustment" if scenario == SCENARIOS[2] else " | no clock adjustment"))
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    fig.suptitle(
        "Equal-weight classical composite vs single benchmarks — SPEC92 peak\nSame candidate tuples for every predictor; leave one entire DEC model out",
        fontsize=13,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    for suffix in ("png", "svg"):
        fig.savefig(output / ("heldout-errors." + suffix), dpi=160)
    plt.close(fig)


@click.command("composite-fit")
@click.option(
    "--vectors",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/composite-overlap/vectors.csv"),
    show_default=True,
)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/composite-fit"), show_default=True)
@click.option("--bootstrap", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260926, show_default=True)
def composite_fit(vectors, output, bootstrap, seed):
    """Compare equal weights against single benchmarks on identical held-out models."""
    with vectors.open(newline="") as f:
        rows = list(csv.DictReader(f))
    summaries, folds, observations = compare(rows, bootstrap, seed)
    output.mkdir(parents=True, exist_ok=True)
    for name, data in [("summary", summaries), ("folds", folds), ("predictions", observations)]:
        write_csv(output / (name + ".csv"), data)
    plot(output, folds)
    audit = dict(
        method="classic-equal-weight-heldout-v1",
        bootstrap=bootstrap,
        seed=seed,
        unit_normalizers={"Dhrystone": "1 DMIPS", "Whetstone": "1 MWIPS", "LINPACK": "1 MFLOPS"},
        weights=[1 / 3, 1 / 3, 1 / 3],
        input_sha256={str(vectors): hashlib.sha256(vectors.read_bytes()).hexdigest()},
        code_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__), Path(__file__).with_name("classic_fit.py"))
        },
        output_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.csv")},
    )
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), comparisons=len(summaries), model_folds=len(folds))))
