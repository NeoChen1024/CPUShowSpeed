"""Two-family classical fits, with Dhrystone versions kept separate."""

import csv
import hashlib
import itertools
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
from cpushowspeed.calibration import ANCHOR as ANCHOR
from cpushowspeed.calibration import fit, quantile
from cpushowspeed.classic_pair_data import PATTERNS, SCENARIOS, build
from cpushowspeed.classic_pair_data import values as values
from cpushowspeed.classic_values import TARGETS
from cpushowspeed.classic_values import clock_status as clock_status
from cpushowspeed.classic_values import linpack_n100 as linpack_n100
from cpushowspeed.classic_values import numeric
from cpushowspeed.research_io import code_hashes, write_csv


def version_audit(classical):
    rows = []
    for r in classical.values():
        if r["benchmark"] != "Dhrystone":
            continue
        a, b = [numeric(r["metrics_raw"].get(k)) for k in ("v1.1_DMIPS", "v2.1_DMIPS")]
        if a and b:
            rows.append(
                dict(
                    id=r["id"],
                    system=r["system"],
                    v11=a,
                    v21=b,
                    ratio_v11_v21=a / b,
                    source_url=r["source_url"],
                    locator=r["locator"],
                    raw_record=r["raw_record"],
                )
            )
    ratios = [r["ratio_v11_v21"] for r in rows]
    stats = (
        dict(
            paired_source_rows=len(rows),
            geometric_mean=math.exp(statistics.mean(map(math.log, ratios))),
            median=statistics.median(ratios),
            p05=quantile(ratios, 0.05),
            p95=quantile(ratios, 0.95),
            min=min(ratios),
            max=max(ratios),
            within_10pct=sum(abs(r - 1) <= 0.1 for r in ratios),
        )
        if ratios
        else dict(paired_source_rows=0)
    )
    return rows, stats


def analyze(rows, bootstrap, seed):
    summaries, folds, predictions = [], [], []
    for pattern, target, scenario in itertools.product(["+".join(f"{f}:{m}" for f, m in p) for p in PATTERNS], TARGETS, SCENARIOS):
        selected = [r for r in rows if (r["pattern"], r["target"], r["scenario"]) == (pattern, target, scenario) and r["included"]]
        for predictor in ("equal_weight", "first", "second"):
            context = dict(pattern=pattern, target=target, scenario=scenario, predictor=predictor)
            data = [
                dict(r, x=math.sqrt(r["first"] * r["second"]) if predictor == "equal_weight" else r[predictor], y_vaxen=r["y"])
                for r in selected
            ]
            result = fit(data, bootstrap, seed)
            summaries.append(dict(context, **result))
            groups = defaultdict(list)
            for r in data:
                groups[r["model_key"]].append(r)
            centers = {k: statistics.median(math.log(r["y"] / r["x"]) for r in g) for k, g in groups.items()}
            if len(centers) < 2:
                continue
            for model, group in sorted(groups.items()):
                logk = statistics.mean(c for k, c in centers.items() if k != model)
                folds.append(
                    dict(
                        context,
                        heldout_model=model,
                        training_models=len(centers) - 1,
                        factor=math.exp(logk),
                        signed_center_error_percent=100 * math.expm1(logk - centers[model]),
                    )
                )
                for r in group:
                    predictions.append(
                        dict(
                            context,
                            heldout_model=model,
                            spec_id=r["spec_id"],
                            first_id=r["first_id"],
                            second_id=r["second_id"],
                            observed=r["y"],
                            predicted=math.exp(logk) * r["x"],
                        )
                    )
    return summaries, folds, predictions


def plot(output, summaries):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    labels = ["+".join(f"{f}:{m}" for f, m in p) for p in PATTERNS]
    for ax, scenario in zip(axes, SCENARIOS[1:]):
        for offset, predictor in enumerate(("equal_weight", "first", "second")):
            selected = [
                next(
                    r
                    for r in summaries
                    if r["pattern"] == p
                    and r["target"] == "SPECrate_int92"
                    and r["scenario"] == scenario
                    and r["predictor"] == predictor
                )
                for p in labels
            ]
            ax.scatter(
                [r.get("loo_model_p95_percent", float("nan")) for r in selected],
                [i + 0.18 * (offset - 1) for i in range(len(labels))],
                label=predictor,
            )
        ax.set_yticks(
            range(len(labels)),
            [p.replace("Dhrystone:", "D ").replace("Whetstone:", "W ").replace("LINPACK:", "L ") for p in labels],
        )
        ax.invert_yaxis()
        ax.set_title(scenario)
        ax.set_xlabel("Held-out model-center P95 absolute error (%)")
        ax.grid(alpha=0.2)
        ax.legend()
    fig.suptitle(
        "Two-family intersections — SPEC92 integer-rate peak\nSame tuples for composite / first / second within each row; cohorts differ between rows"
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    for suffix in ("png", "svg"):
        fig.savefig(output / ("heldout-comparison." + suffix), dpi=160)
    plt.close(fig)


@click.command("pair-fit")
@click.option(
    "--input-root",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/overlap-spec"),
    show_default=True,
)
@click.option(
    "--linpack-text",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/netlib-linpack-report.txt"),
    show_default=True,
)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/pair-fit"), show_default=True)
@click.option("--bootstrap", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260926, show_default=True)
def pair_fit(input_root, linpack_text, output, bootstrap, seed):
    """Fit separate two-family cohorts; audit paired Dhrystone version differences."""
    paths = [input_root / name for name in ("classical-records.jsonl", "spec-records.jsonl", "candidate-pairs.csv")]
    classical, specs = [{r["id"]: r for r in map(json.loads, p.read_text().splitlines())} for p in paths[:2]]
    with paths[2].open(newline="") as f:
        pairs = list(csv.DictReader(f))
    rows = build(classical, specs, pairs, linpack_text.read_text().split("\f"))
    summaries, folds, predictions = analyze(rows, bootstrap, seed)
    version_rows, version_stats = version_audit(classical)
    output.mkdir(parents=True, exist_ok=True)
    for name, data in [
        ("pairs", rows),
        ("summary", summaries),
        ("folds", folds),
        ("predictions", predictions),
        ("dhrystone-versions", version_rows),
    ]:
        write_csv(output / (name + ".csv"), data)
    (output / "dhrystone-version-summary.json").write_text(json.dumps(version_stats, indent=2) + "\n")
    plot(output, summaries)
    audit = dict(
        method="classic-two-family-fit-v1",
        bootstrap=bootstrap,
        seed=seed,
        weights=[0.5, 0.5],
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths + [linpack_text]},
        code_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__), Path(__file__).with_name("classic_fit.py"), Path(__file__).with_name("classic_composite.py")]
        },
        output_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.csv")},
    )
    audit["shared_code_sha256"] = code_hashes(Path(__file__))
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), comparisons=len(summaries), version_pairs=len(version_rows))))
