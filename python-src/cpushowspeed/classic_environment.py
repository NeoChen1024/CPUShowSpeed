"""Leakage-controlled comparison of pooled, grouped and shrinkage log-ratio fits."""

import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
from cpushowspeed.calibration import error_summary, weighted_quantile
from cpushowspeed.classic_source_data import os_key
from cpushowspeed.research_io import code_hashes
from cpushowspeed.research_io import read_csv as csv_rows
from cpushowspeed.research_io import write_csv

MODELS = ("pooled", "grouped", "shrinkage")
LAMBDAS = (1.0, 4.0, 16.0)


def cells(rows):
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["model_key"], r["environment"]].append(r["z"])
    counts = defaultdict(int)
    for (m, e), zs in grouped.items():
        counts[m] += len(zs)
    return [(m, e, statistics.median(zs), len(zs) / counts[m]) for (m, e), zs in sorted(grouped.items())]


def train(rows, method, lam=4.0):
    data = cells(rows)
    if not data:
        raise ValueError("empty training set")
    model_values = defaultdict(list)
    for r in rows:
        model_values[r["model_key"]].append(r["z"])
    alpha = statistics.mean(statistics.median(v) for v in model_values.values())
    envs = defaultdict(list)
    for m, e, z, w in data:
        envs[e].append((z, w))
    offsets = {}
    supports = {}
    for e, items in envs.items():
        n = sum(w for z, w in items)
        mean = sum(z * w for z, w in items) / n
        offsets[e] = 0 if method == "pooled" else (mean - alpha) * (1 if method == "grouped" else n / (n + lam))
        supports[e] = n
    return dict(alpha=alpha, offsets=offsets, supports=supports)


def predict(model, environment):
    return model["alpha"] + model["offsets"].get(environment, 0)


def select_lambda(rows):
    keys = sorted({r["model_key"] for r in rows})
    if len(keys) < 3:
        return 4.0, "fixed_fallback_less_than_three_training_models"
    losses = []
    for lam in LAMBDAS:
        errors = []
        for key in keys:
            fitted = train([r for r in rows if r["model_key"] != key], "shrinkage", lam)
            heldout = cells([r for r in rows if r["model_key"] == key])
            errors.append(sum(w * (predict(fitted, e) - z) ** 2 for m, e, z, w in heldout) / sum(w for m, e, z, w in heldout))
        losses.append((statistics.mean(errors), lam))
    return min(losses)[1], "inner_leave_model_out"


def evaluate(rows):
    predictions, folds = [], []
    plans = [("leave_model_out", k) for k in sorted({r["model_key"] for r in rows})]
    plans += [("leave_environment_out", k) for k in sorted({r["environment"] for r in rows})]
    plans += [("leave_origin_out_purged", k) for k in sorted({r["origin"] for r in rows})]
    for scheme, key in plans:
        field = {"leave_model_out": "model_key", "leave_environment_out": "environment", "leave_origin_out_purged": "origin"}[
            scheme
        ]
        testing = [r for r in rows if r[field] == key]
        training = [r for r in rows if r[field] != key]
        purged = 0
        if scheme == "leave_origin_out_purged":
            ids = {r[f] for r in testing for f in ("spec_id", "first_id", "second_id")}
            keep = [r for r in training if not any(r[f] in ids for f in ("spec_id", "first_id", "second_id"))]
            purged = len(training) - len(keep)
            training = keep
        if not training:
            for method in MODELS:
                folds.append(dict(scheme=scheme, heldout=key, method=method, status="no_training_data", purged=purged))
            continue
        lam, selection = select_lambda(training)
        for method in MODELS:
            fitted = train(training, method, lam)
            folds.append(
                dict(
                    scheme=scheme,
                    heldout=key,
                    method=method,
                    status="evaluated",
                    training_models=len({r["model_key"] for r in training}),
                    training_rows=len(training),
                    test_rows=len(testing),
                    purged=purged,
                    shrinkage_lambda=lam if method == "shrinkage" else "",
                    lambda_selection=selection if method == "shrinkage" else "not_applicable",
                )
            )
            for r in testing:
                logratio = predict(fitted, r["environment"])
                predictions.append(
                    dict(
                        scheme=scheme,
                        heldout=key,
                        method=method,
                        model_key=r["model_key"],
                        environment=r["environment"],
                        spec_id=r["spec_id"],
                        first_id=r["first_id"],
                        second_id=r["second_id"],
                        unseen_environment=r["environment"] not in fitted["offsets"],
                        observed=float(r["y"]),
                        predicted=math.exp(logratio) * r["x"],
                        signed_error_percent=100 * math.expm1(logratio - r["z"]),
                        log_error=logratio - r["z"],
                    )
                )
    summaries = []
    for scheme in sorted({f["scheme"] for f in folds}):
        for method in MODELS:
            selected = [r for r in predictions if r["scheme"] == scheme and r["method"] == method]
            if not selected:
                summaries.append(dict(scheme=scheme, method=method, status="no_evaluable_folds"))
                continue
            by_model = defaultdict(lambda: defaultdict(list))
            for r in selected:
                by_model[r["model_key"]][r["environment"]].append(r)
            weighted = []
            logs = []
            signed = []
            for envs in by_model.values():
                for obs in envs.values():
                    w = 1 / sum(len(v) for v in envs.values())
                    weighted += [(abs(r["signed_error_percent"]), w) for r in obs]
                    signed += [(r["signed_error_percent"], w) for r in obs]
                    logs += [(r["log_error"] ** 2, w) for r in obs]
            summaries.append(
                dict(
                    scheme=scheme,
                    method=method,
                    status="evaluated",
                    **error_summary(selected),
                    models=len(by_model),
                    observations=len(selected),
                    weighted_absolute_p95_percent=weighted_quantile(weighted, 0.95),
                    weighted_absolute_median_percent=weighted_quantile(weighted, 0.5),
                    weighted_signed_median_percent=weighted_quantile(signed, 0.5),
                    log_rmse=math.sqrt(sum(x * w for x, w in logs) / sum(w for x, w in logs)),
                    unseen_environment_rows=sum(r["unseen_environment"] for r in selected),
                )
            )
    return summaries, folds, predictions


def plot(output, summaries):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    patterns = sorted({r["pattern"] for r in summaries if r["cohort"] == "within_DEC" and r["scheme"] == "leave_model_out"})
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    for ax, cohort in zip(axes, ("within_DEC", "extended")):
        for j, method in enumerate(MODELS):
            vals = {
                r["pattern"]: float(r["model_center_p95_percent"])
                for r in summaries
                if r["cohort"] == cohort
                and r["scheme"] == "leave_model_out"
                and r["method"] == method
                and r["status"] == "evaluated"
            }
            ax.scatter(
                [vals.get(p, float("nan")) for p in patterns], [i + 0.18 * (j - 1) for i in range(len(patterns))], label=method
            )
        ax.set_yticks(
            range(len(patterns)),
            [p.replace("Dhrystone:", "D ").replace("Whetstone:", "W ").replace("LINPACK:", "L ") for p in patterns],
        )
        ax.invert_yaxis()
        ax.set_title(cohort)
        ax.set_xlabel("Equal-model center P95 relative error (%)")
        ax.grid(alpha=0.2)
        ax.legend()
    fig.suptitle(
        "Environment model comparison — held-out machine models\nFixed equal benchmark weights; shrinkage tuned inside training folds; all environments retained"
    )
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    for ext in ("png", "svg"):
        fig.savefig(output / ("environment-comparison." + ext), dpi=160)
    plt.close(fig)


@click.command("environment-fit")
@click.option(
    "--input-root",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/source-pair-fit"),
    show_default=True,
)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/environment-fit"), show_default=True)
def environment_fit(input_root, output):
    """Compare pooled, environment-grouped and nested-CV shrinkage multipliers."""
    paths = [
        input_root / "pairs.csv",
        Path("research/data/classic/pdf-extraction/tables.jsonl"),
        Path("data/derived/classic/overlap-spec/spec-records.jsonl"),
    ]
    osmap = {}
    for t in map(json.loads, paths[1].read_text().splitlines()):
        if t["source_id"] == "dec-n3909-1994":
            for r in t["rows"]:
                for i, c in enumerate(t["columns"], 1):
                    osmap[f"{t['source_id']}:{t['table_id']}:l{r['line']}:c{i}"] = os_key(c["os"]) or "unknown"
    for s in map(json.loads, paths[2].read_text().splitlines()):
        osmap[s["id"]] = os_key(s.get("os_raw", "")) or ("hpux" if "hp-ux" in s.get("os_raw", "").lower() else "unknown")
    rows = []
    for r in csv_rows(paths[0]):
        if r["stage"] != "plus_cross_source_clock_sensitivity" or r["target"] != "SPECrate_int92":
            continue
        r["x"] = math.sqrt(float(r["first"]) * float(r["second"]))
        r["z"] = math.log(float(r["y"]) / r["x"])
        r["environment"] = r["origin"] + "|" + osmap.get(r["spec_id"], "unknown")
        rows.append(r)
    summaries, folds, predictions, parameters, coverage = [], [], [], [], []
    for cohort in ("within_DEC", "extended"):
        subset = [r for r in rows if cohort == "extended" or r["origin"] == "within_DEC"]
        for pattern in sorted({r["pattern"] for r in subset}):
            data = [r for r in subset if r["pattern"] == pattern]
            ctx = dict(cohort=cohort, pattern=pattern)
            a, b, c = evaluate(data)
            summaries += [dict(ctx, **r) for r in a]
            folds += [dict(ctx, **r) for r in b]
            predictions += [dict(ctx, **r) for r in c]
            lam, selection = select_lambda(data)
            for method in MODELS:
                f = train(data, method, lam)
                for e, offset in f["offsets"].items():
                    parameters.append(
                        dict(
                            ctx,
                            method=method,
                            environment=e,
                            factor=math.exp(f["alpha"] + offset),
                            pooled_factor=math.exp(f["alpha"]),
                            effective_support=f["supports"][e],
                            shrinkage_lambda=lam if method == "shrinkage" else "",
                            fit_status="descriptive_full_data_not_validated_historical_conversion",
                        )
                    )
            for m, e, z, w in cells(data):
                coverage.append(dict(ctx, model_key=m, environment=e, log_ratio_median=z, model_environment_weight=w))
    output.mkdir(parents=True, exist_ok=True)
    for name, data in [
        ("summary", summaries),
        ("folds", folds),
        ("predictions", predictions),
        ("parameters", parameters),
        ("coverage", coverage),
    ]:
        write_csv(output / (name + ".csv"), data)
    plot(output, summaries)
    audit = dict(
        method="classical-environment-model-balanced-v2",
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        environment_definition="construction cohort plus SPEC target OS family; not isolated compiler or classical-run environment",
        shrinkage_grid=list(LAMBDAS),
        discarded_for_error=0,
        output_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.csv")},
    )
    audit["shared_code_sha256"] = code_hashes(Path(__file__))
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), comparisons=len(summaries))))
