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
from cpushowspeed.classic_composite import TARGETS, clock_status
from cpushowspeed.classic_fit import (
    ANCHOR,
    fit,
    linpack_n100,
    numeric,
    quantile,
    write_csv,
)

PATTERNS = [(("Dhrystone", d), ("Whetstone", w)) for d in ("v1.1_DMIPS", "v2.1_DMIPS") for w in ("MWIPS", "MWIPS_DP")]
PATTERNS += [(("Dhrystone", d), ("LINPACK", "n100_MFLOPS")) for d in ("v1.1_DMIPS", "v2.1_DMIPS")]
PATTERNS += [(("Whetstone", w), ("LINPACK", "n100_MFLOPS")) for w in ("MWIPS", "MWIPS_DP")]
SCENARIOS = ("known_clocks", "unknown_allowed", "linear_clock_scaling")


def values(records, scores, spec, scenario):
    reasons = []
    clocks = clock_status(records + [spec])
    multipliers = [1.0, 1.0]
    destination = None
    if scenario != "linear_clock_scaling":
        if clocks == "conflict":
            reasons.append("clock_conflict")
        elif clocks == "unknown" and scenario == "known_clocks":
            reasons.append("unknown_clock")
    else:
        # Prefer SPEC, then LINPACK (never scaled), then Whetstone, Dhrystone.
        ordered = [spec] + sorted(records, key=lambda r: {"LINPACK": 0, "Whetstone": 1, "Dhrystone": 2}[r["benchmark"]])
        destination = next((r for r in ordered if numeric(r.get("clock_mhz"))), None)
        for i, record in enumerate(records):
            if record["benchmark"] == "LINPACK":
                if clock_status([record, spec]) == "conflict":
                    reasons.append("unscaled_linpack_spec_clock_conflict")
                continue
            frequency = numeric(record.get("clock_mhz"))
            if not destination or not frequency:
                reasons.append("missing_clock_for_scaling")
            else:
                multipliers[i] = numeric(destination["clock_mhz"]) / frequency
    return [x * m for x, m in zip(scores, multipliers)], multipliers, destination, reasons


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


def build(classical, specs, pairs, pages):
    groups = defaultdict(lambda: defaultdict(set))
    keys = {}
    for p in pairs:
        groups[p["spec_id"]][classical[p["classic_id"]]["benchmark"]].add(p["classic_id"])
        keys[p["spec_id"]] = p["model_key"]
    rows = []
    cache = {}
    for sid, families in sorted(groups.items()):
        spec = specs[sid]
        for pattern in PATTERNS:
            label = "+".join(f"{family}:{metric}" for family, metric in pattern)
            options = []
            for family, metric in pattern:
                members = []
                for cid in sorted(families[family]):
                    r = classical[cid]
                    if (cid, metric) not in cache:
                        cache[cid, metric] = (
                            linpack_n100(r, pages) if family == "LINPACK" else numeric(r["metrics_raw"].get(metric))
                        )
                    if cache[cid, metric]:
                        members.append((r, cache[cid, metric]))
                options.append(members)
            for target in TARGETS:
                score = numeric(spec["metrics_raw"].get(target))
                if score is None:
                    continue
                for combination in itertools.product(*options):
                    records = [x[0] for x in combination]
                    scores = [x[1] for x in combination]
                    exclusions = []
                    if target.startswith("SPECrate") and numeric(spec.get("cpu_count")) != 1:
                        exclusions.append("spec_cpu_count_not_one")
                    if any(r.get("reported_processor_count") is not None and r["reported_processor_count"] != 1 for r in records):
                        exclusions.append("classic_cpu_count_not_one")
                    raw = spec["raw_record"]
                    if isinstance(raw, dict) and (
                        raw.get("measurement_type") == "reference_definition"
                        or "reference_definition" in raw.get("review_flags", "")
                    ):
                        exclusions.append("reference_definition")
                    for scenario in SCENARIOS:
                        adjusted, multipliers, destination, reasons = values(records, scores, spec, scenario)
                        rows.append(
                            dict(
                                pattern=label,
                                target=target,
                                scenario=scenario,
                                model_key=keys[sid],
                                spec_id=sid,
                                first_id=records[0]["id"],
                                second_id=records[1]["id"],
                                system=spec["system"],
                                first_original=scores[0],
                                second_original=scores[1],
                                first=adjusted[0],
                                second=adjusted[1],
                                first_multiplier=multipliers[0],
                                second_multiplier=multipliers[1],
                                normalization_clock_source=destination["id"] if destination else "",
                                y=score * (ANCHOR if target.startswith("SPECrate") else 1),
                                included=not (exclusions + reasons),
                                exclusion_reasons=";".join(exclusions + reasons),
                                provenance=json.dumps(
                                    [
                                        dict(id=r["id"], url=r["source_url"], locator=r.get("locator"), raw=r["raw_record"])
                                        for r in records + [spec]
                                    ],
                                    sort_keys=True,
                                ),
                            )
                        )
    return rows


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
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), comparisons=len(summaries), version_pairs=len(version_rows))))
