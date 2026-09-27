"""Source-column experiments and explicitly qualified cross-source extensions."""

import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import click
from cpushowspeed.calibration import ANCHOR as ANCHOR
from cpushowspeed.calibration import fit
from cpushowspeed.calibration import quantile as quantile
from cpushowspeed.classic_overlap import model_key
from cpushowspeed.classic_pdf import scalar
from cpushowspeed.classic_source_data import (
    STAGES,
)
from cpushowspeed.classic_source_data import make_pair as make_pair
from cpushowspeed.classic_source_data import os_key as os_key
from cpushowspeed.classic_source_data import (
    pair_patterns,
    prepare,
    source_vectors,
)
from cpushowspeed.classic_values import numeric
from cpushowspeed.research_io import code_hashes, read_csv, write_csv


def calculate(rows, bootstrap, seed):
    groups = defaultdict(list)
    for r in rows:
        groups[r["stage"], r["target"], r["pattern"]].append(r)
    summary, folds, predictions = [], [], []
    for (stage, target, pattern), data in sorted(groups.items()):
        for predictor in ("equal_weight", "first", "second"):
            context = dict(stage=stage, target=target, pattern=pattern, predictor=predictor)
            points = [
                dict(r, x=math.sqrt(r["first"] * r["second"]) if predictor == "equal_weight" else r[predictor], y_vaxen=r["y"])
                for r in data
            ]
            stat = fit(points, bootstrap, seed)
            stat["interpretation_status"] = "conditional_configuration_unverified"
            summary.append(dict(context, **stat, origins=";".join(sorted({r["origin"] for r in data}))))
            model_groups = defaultdict(list)
            for r in points:
                model_groups[r["model_key"]].append(r)
            centers = {k: statistics.median(math.log(r["y"] / r["x"]) for r in rs) for k, rs in model_groups.items()}
            if len(centers) < 2:
                continue
            for model, rs in sorted(model_groups.items()):
                k = math.exp(statistics.mean(v for m, v in centers.items() if m != model))
                folds.append(
                    dict(
                        context,
                        heldout_model=model,
                        training_models=len(centers) - 1,
                        factor=k,
                        signed_center_error_percent=100 * (k / math.exp(centers[model]) - 1),
                    )
                )
                for r in rs:
                    predictions.append(
                        dict(
                            context,
                            heldout_model=model,
                            spec_id=r["spec_id"],
                            first_id=r["first_id"],
                            second_id=r["second_id"],
                            origin=r["origin"],
                            observed=r["y"],
                            predicted=k * r["x"],
                        )
                    )
    return summary, folds, predictions


def plot(output, summary):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    patterns = sorted({r["pattern"] for r in summary if r["target"] == "SPECrate_int92" and r["stage"] == "within_source"})
    fig, axes = plt.subplots(1, 2, figsize=(17, 7))
    for ax, stage in zip(axes, (STAGES[0], STAGES[-1])):
        for j, pred in enumerate(("equal_weight", "first", "second")):
            found = {
                (r["pattern"]): r
                for r in summary
                if r["stage"] == stage and r["target"] == "SPECrate_int92" and r["predictor"] == pred
            }
            ax.scatter(
                [found[p].get("loo_model_p95_percent", float("nan")) for p in patterns],
                [i + 0.18 * (j - 1) for i in range(len(patterns))],
                label=pred,
            )
        ax.set_yticks(
            range(len(patterns)),
            [p.replace("Dhrystone:", "D ").replace("Whetstone:", "W ").replace("LINPACK:", "L ") for p in patterns],
        )
        ax.invert_yaxis()
        ax.set_xscale("log")
        ax.set_xlabel("Held-out model-center P95 absolute error (%) — log scale")
        ax.set_title(stage)
        ax.grid(alpha=0.2)
        ax.legend()
    fig.suptitle(
        "Source-column vs extended candidates — SPEC92 integer rate\nDEC printed KWIPS interpreted as MWIPS; active CPUs/copies unknown within DEC; no conversion-chain update"
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    for ext in ("png", "svg"):
        fig.savefig(output / ("source-comparison." + ext), dpi=160)
    plt.close(fig)


@click.command("source-pair-fit")
@click.option(
    "--pdf-root",
    type=click.Path(path_type=Path, exists=True),
    default=Path("research/data/classic/pdf-extraction"),
    show_default=True,
)
@click.option(
    "--legacy-pairs",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/pair-fit/pairs.csv"),
    show_default=True,
)
@click.option(
    "--spec-records",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/overlap-spec/spec-records.jsonl"),
    show_default=True,
)
@click.option("--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/source-pair-fit"), show_default=True)
@click.option("--bootstrap", type=click.IntRange(min=100), default=10000, show_default=True)
@click.option("--seed", type=int, default=20260926, show_default=True)
def source_pair_fit(pdf_root, legacy_pairs, spec_records, output, bootstrap, seed):
    """Compare within-source vectors with qualified legacy/cross-source extensions."""
    tables = list(map(json.loads, (pdf_root / "tables.jsonl").read_text().splitlines()))
    interpreted = read_csv(pdf_root / "dec-interpreted.csv")
    vectors, units = source_vectors(tables, interpreted)
    rows, matching = prepare(vectors, read_csv(legacy_pairs), list(map(json.loads, spec_records.read_text().splitlines())))
    summary, folds, predictions = calculate(rows, bootstrap, seed)
    # These sources are retained without inventing missing workload identities.
    availability = []
    for v in vectors:
        for a, b in pair_patterns(v["scores"]):
            availability.append(
                dict(
                    source_id=v["source_id"],
                    vector_id=v["id"],
                    model_key=v["model_key"],
                    pattern=a + "+" + b,
                    targets=";".join(v["targets"]),
                    status="conditional_source_column",
                )
            )
    for t in tables:
        if t["source_id"] == "sscl-375" and t["table_id"] == "Table 2":
            for r in t["rows"]:
                availability.append(
                    dict(
                        source_id=t["source_id"],
                        vector_id=f"sscl-375:Table2:l{r['line']}",
                        model_key=model_key(r["cells"][0]),
                        pattern="Dhrystone:version_unknown+LINPACK:size_unknown",
                        targets="SPECmark89",
                        status="excluded_unresolved_version_and_matrix_size",
                    )
                )
    tomari = []
    for r in read_csv(pdf_root / "tomari-configurations.csv"):
        y = numeric(r["CINT2006_reported"])
        x = scalar(r["Dhrystone2.1_DMIPS"])
        if x and y:
            tomari.append(dict(model_key=model_key(r["machine"]), x=x, y_vaxen=y))
    classical_path = spec_records.with_name("classical-records.jsonl")
    classical = list(map(json.loads, classical_path.read_text().splitlines()))
    scale_review = []
    for v in vectors:
        dec = v["scores"].get("Whetstone:MWIPS_DP")
        if not dec:
            continue
        for r in classical:
            old = numeric(r["metrics_raw"].get("MWIPS_DP"))
            if r["benchmark"] == "Whetstone" and old and model_key(r["system"]) == v["model_key"]:
                scale_review.append(
                    dict(
                        vector_id=v["id"],
                        legacy_record_id=r["id"],
                        model_key=v["model_key"],
                        dec_os=v["os"],
                        dec_dp_mwips_by_policy=dec,
                        legacy_dp_mwips=old,
                        legacy_over_dec=old / dec,
                        qualification="model_only_scale_check_not_verified_same_config",
                        dec_source_url=v["source_url"],
                        legacy_source_url=r["source_url"],
                    )
                )
    output.mkdir(parents=True, exist_ok=True)
    (output / "vectors.jsonl").write_text("".join(json.dumps(v) + "\n" for v in vectors))
    for name, data in [
        ("unit-review", units),
        ("unit-scale-review", scale_review),
        ("availability", availability),
        ("pairs", rows),
        ("matching-review", matching),
        ("summary", summary),
        ("folds", folds),
        ("predictions", predictions),
    ]:
        write_csv(output / (name + ".csv"), data)
    (output / "tomari-diagnostic.json").write_text(
        json.dumps(dict(target="CINT2006_reported_raw_not_rate_or_VAXen", **fit(tomari, bootstrap, seed)), indent=2) + "\n"
    )
    plot(output, summary)
    paths = [
        pdf_root / n for n in ("tables.jsonl", "dec-interpreted.csv", "interpretation-policy.json", "tomari-configurations.csv")
    ] + [legacy_pairs, spec_records, classical_path]
    audit = dict(
        method="source-pair-fit-v1",
        bootstrap=bootstrap,
        seed=seed,
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        helper_sha256=hashlib.sha256(Path(__file__).with_name("classic_fit.py").read_bytes()).hexdigest(),
        counts=dict(vectors=len(vectors), pairs_by_stage=dict(Counter(r["stage"] for r in rows)), comparisons=len(summary)),
        output_sha256={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.suffix in (".csv", ".jsonl")
        },
    )
    audit["shared_code_sha256"] = code_hashes(Path(__file__))
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(audit["counts"]))
