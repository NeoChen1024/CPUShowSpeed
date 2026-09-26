"""Direct classical pair/triple fits to the CPU92 integer-rate VAX reference."""

import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
from cpushowspeed.classic_fit import ANCHOR, write_csv
from cpushowspeed.classic_pooled import composites
from cpushowspeed.classic_source_fit import fit, read_csv

TARGETS = ("SPECrate_base_int92", "SPECrate_int92")
STAGES = ("within_source", "plus_cross_source_unscaled")


def prepare(source, stage):
    rows = composites(source, stage, targets=TARGETS)
    for r in rows:
        # source-pair-fit already applies ANCHOR to rate scores. Never apply it twice.
        r["y_vaxen"] = r.pop("raw_target")
        r["rate_score_reconstructed_from_input"] = r["y_vaxen"] / ANCHOR
        r["target_unit"] = "SPEC92 integer-rate VAXen"
        r["variant"] = "base" if r["target"] == TARGETS[0] else "peak"
        for key in ("generation", "z", "first_id", "second_id", "first", "second"):
            r.pop(key, None)
    return rows


def calculate(rows, bootstrap, seed):
    groups = defaultdict(list)
    for r in rows:
        groups[r["stage"], r["target"], r["pattern"]].append(r)
    summaries, predictions = [], []
    for (stage, target, pattern), data in sorted(groups.items()):
        for predictor in ["equal_weight"] + pattern.split("+"):
            prepared = []
            for r in data:
                x = r["x"] if predictor == "equal_weight" else json.loads(r["member_values"])[pattern.split("+").index(predictor)]
                prepared.append(dict(r, x=x))
            context = dict(
                stage=stage,
                target=target,
                variant=data[0]["variant"],
                pattern=pattern,
                predictor=predictor,
                target_unit="SPEC92 integer-rate VAXen",
            )
            result = fit(prepared, bootstrap, seed)
            summaries.append(dict(context, **result))
            by_model = defaultdict(list)
            for r in prepared:
                by_model[r["model_key"]].append(r)
            centers = {k: statistics.median(math.log(r["y_vaxen"] / r["x"]) for r in group) for k, group in by_model.items()}
            if len(centers) < 2:
                continue
            for model, group in sorted(by_model.items()):
                k = math.exp(statistics.mean(v for key, v in centers.items() if key != model))
                for r in group:
                    predicted = k * r["x"]
                    predictions.append(
                        dict(
                            context,
                            model_key=model,
                            spec_id=r["spec_id"],
                            member_ids=r["member_ids"],
                            observed_vaxen=r["y_vaxen"],
                            predicted_vaxen=predicted,
                            training_factor=k,
                            signed_error_percent=100 * (predicted / r["y_vaxen"] - 1),
                        )
                    )
    return summaries, predictions


def plot(output, rows, summaries):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter

    for target in TARGETS:
        selected = [r for r in rows if r["stage"] == STAGES[-1] and r["target"] == target]
        patterns = sorted({r["pattern"] for r in selected})
        if not patterns:
            continue
        fig, axes = plt.subplots(math.ceil(len(patterns) / 3), 3, figsize=(17, 4 * math.ceil(len(patterns) / 3)), squeeze=False)
        for ax, pattern in zip(axes.flat, patterns):
            data = [r for r in selected if r["pattern"] == pattern]
            result = next(
                r
                for r in summaries
                if r["stage"] == STAGES[-1]
                and r["target"] == target
                and r["pattern"] == pattern
                and r["predictor"] == "equal_weight"
            )
            for origin, color in [("within_DEC", "#167eaf"), ("legacy_cross_source", "#d67c24"), ("DEC_to_archive", "#40975a")]:
                group = [r for r in data if r["origin"] == origin]
                if group:
                    ax.scatter([r["x"] for r in group], [r["y_vaxen"] for r in group], s=18, alpha=0.55, label=origin, color=color)
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
                ylabel="SPEC92 integer-rate VAXen",
            )
            ax.xaxis.set_minor_formatter(NullFormatter())
            ax.yaxis.set_minor_formatter(NullFormatter())
            ax.text(
                0.03, 0.96, f"{result['models']} models / {result['pairs']} tuples", transform=ax.transAxes, va="top", fontsize=8
            )
            ax.legend(fontsize=7, loc="lower right")
            ax.grid(alpha=0.2)
        for ax in list(axes.flat)[len(patterns) :]:
            ax.axis("off")
        variant = selected[0]["variant"]
        fig.suptitle(
            f"Classical composites → SPEC92 integer rate — {variant}\nAll eligible unscaled source cohorts; shading: factor CI95, not prediction interval"
        )
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        for ext in ("png", "svg"):
            fig.savefig(output / f"rate-composite-{variant}.{ext}", dpi=150)
        plt.close(fig)


@click.command("rate-composite-fit")
@click.option(
    "--pairs",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/source-pair-fit/pairs.csv"),
    show_default=True,
)
@click.option(
    "--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/rate-composite-fit"), show_default=True
)
@click.option("--bootstrap", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260926, show_default=True)
def rate_composite_fit(pairs, output, bootstrap, seed):
    """Fit two/three classical families directly to SPEC92 rate-VAXen, base/peak separately."""
    source = read_csv(pairs)
    rows = [r for stage in STAGES for r in prepare(source, stage)]
    summaries, predictions = calculate(rows, bootstrap, seed)
    coverage = []
    for stage in STAGES:
        for target in sorted({r["target"] for r in source}):
            group = [r for r in source if r["stage"] == stage and r["target"] == target]
            coverage.append(
                dict(
                    stage=stage,
                    target=target,
                    input_pair_tuples=len(group),
                    models=len({r["model_key"] for r in group}),
                    included=target in TARGETS,
                    reason="direct_integer_rate" if target in TARGETS else "different_metric",
                )
            )
    output.mkdir(parents=True, exist_ok=True)
    for name, data in [("observations", rows), ("summary", summaries), ("predictions", predictions), ("target-coverage", coverage)]:
        write_csv(output / (name + ".csv"), data)
    plot(output, rows, summaries)
    audit = dict(
        method="classic-direct-rate-composites-v1",
        date="2026-09-27",
        bootstrap=bootstrap,
        seed=seed,
        primary_stage=STAGES[-1],
        comparison_stage=STAGES[0],
        target_unit="SPEC92 integer-rate VAXen",
        rate_to_vaxen=ANCHOR,
        normalization="Input y already normalized by source-pair-fit; no second scaling",
        spec89_included=False,
        observations_across_stages=len(rows),
        comparisons=len(summaries),
        uncertainty="model-cluster bootstrap; conditional on sources, matches, configurations and unit interpretation",
        input_sha256={str(pairs): hashlib.sha256(pairs.read_bytes()).hexdigest()},
        code_sha256={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__)]
            + [Path(__file__).with_name(n) for n in ("classic_pooled.py", "classic_source_fit.py", "classic_fit.py")]
        },
    )
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), comparisons=len(summaries), observations=len(rows))))
