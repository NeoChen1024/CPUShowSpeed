"""Source-column experiments and explicitly qualified cross-source extensions."""

import csv
import hashlib
import itertools
import json
import math
import random
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import click
from cpushowspeed.classic_fit import ANCHOR
from cpushowspeed.classic_fit import fit as reference_fit
from cpushowspeed.classic_fit import numeric, quantile, write_csv
from cpushowspeed.classic_overlap import model_key
from cpushowspeed.classic_pdf import scalar

STAGES = ("within_source", "plus_legacy_unscaled", "plus_cross_source_unscaled", "plus_cross_source_clock_sensitivity")


def fit(rows, bootstrap, seed):
    # Reuse the established point/held-out estimators; replace their temporary
    # interval using all requested draws with a faster floating-point mean.
    result = reference_fit(rows, 100, seed)
    if result["models"] < 2:
        return result
    groups = defaultdict(list)
    for r in rows:
        groups[r["model_key"]].append(math.log(r["y_vaxen"] / r["x"]))
    centers = [statistics.median(v) for k, v in sorted(groups.items())]
    rng = random.Random(seed)
    draws = [math.exp(math.fsum(rng.choices(centers, k=len(centers))) / len(centers)) for _ in range(bootstrap)]
    result["factor_ci95_low"] = quantile(draws, 0.025)
    result["factor_ci95_high"] = quantile(draws, 0.975)
    return result


def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def os_key(value):
    value = value.lower()
    if "vms" in value:
        return "vms"
    if "osf" in value:
        return "osf"
    if "ultrix" in value:
        return "ultrix"
    return None


def pair_patterns(scores):
    for a, b in itertools.combinations(
        sorted(scores, key=lambda s: ({"Dhrystone": 0, "Whetstone": 1, "LINPACK": 2}[s.split(":")[0]], s)), 2
    ):
        if a.split(":")[0] != b.split(":")[0]:
            yield a, b


def source_vectors(tables, interpreted):
    lookup = {r["observation_id"]: r for r in interpreted}
    vectors = []
    units = []
    for table in tables:
        if table["source_id"] != "dec-n3909-1994":
            continue
        for i, col in enumerate(table["columns"], 1):
            scores, targets, ids = {}, {}, {}
            for row in table["rows"]:
                metric = row["label_checked"]
                raw = row["cells"][i - 1]
                oid = f"{table['source_id']}:{table['table_id']}:l{row['line']}:c{i}"
                if oid in lookup:
                    r = lookup[oid]
                    if metric.startswith("Dhrystone"):
                        name = "Dhrystone:v" + ("1.1" if "1.1" in metric else "2.1") + "_DMIPS"
                    else:
                        name = "Whetstone:MWIPS_" + ("DP" if metric.endswith("dp") else "SP")
                    scores[name] = float(r["normalized_value"])
                    ids[name] = oid
                    units.append(dict(r, normalized_metric=name, unit_review="explicit_user_policy_applied"))
                elif metric.startswith("LINPACK 100x100") and scalar(raw) is not None:
                    name = "LINPACK:n100_MFLOPS"
                    scores[name] = scalar(raw)
                    ids[name] = oid
                    units.append(
                        dict(
                            observation_id=oid,
                            metric=metric,
                            value_raw=raw,
                            normalized_value=scalar(raw),
                            normalized_unit="MFLOPS",
                            unit_review="n100_dp_source_row",
                        )
                    )
                elif (
                    metric in ("SPECmark89", "SPECint92", "SPECbase_int92", "SPECfp92", "SPECrate_int92", "SPECrate_fp92")
                    and scalar(raw) is not None
                ):
                    targets[metric] = scalar(raw)
                    ids[metric] = oid
            vectors.append(
                dict(
                    id=f"{table['source_id']}:{table['table_id']}:column:{i}",
                    source_id=table["source_id"],
                    machine=col["machine"],
                    os=col["os"],
                    model_key=model_key(col["machine"]),
                    scores=scores,
                    targets=targets,
                    observation_ids=ids,
                    clock_mhz=None,
                    cpu_count=None,
                    source_url=table["source_url"],
                    pdf_page=table["pdf_page"],
                    pdf_blake3=table["pdf_blake3"],
                    qualification="same_source_column;compiler_copies_active_cpu_not_established",
                )
            )
    return vectors, units


def make_pair(vector, a, b, target, score, spec_id, origin, extra=""):
    return dict(
        pattern=a + "+" + b,
        target=target,
        model_key=vector["model_key"],
        system=vector["machine"],
        spec_id=spec_id,
        first_id=vector["observation_ids"][a],
        second_id=vector["observation_ids"][b],
        first=vector["scores"][a],
        second=vector["scores"][b],
        y=score * (ANCHOR if target == "SPECrate_int92" else 1),
        origin=origin,
        qualification=vector["qualification"] + extra,
        target_unit="SPEC92 integer-rate VAXen" if target == "SPECrate_int92" else target + " raw",
        provenance=json.dumps(dict(vector_id=vector["id"], source_url=vector["source_url"], target_record_id=spec_id)),
    )


def prepare(vectors, legacy, specs):
    within, cross, audit = [], [], []
    for vector in vectors:
        for a, b in pair_patterns(vector["scores"]):
            for target, score in vector["targets"].items():
                within.append(make_pair(vector, a, b, target, score, vector["observation_ids"][target], "within_DEC"))
        for spec in specs:
            if model_key(spec["system"]) != vector["model_key"]:
                continue
            reasons = []
            if not os_key(spec.get("os_raw", "")) or os_key(spec["os_raw"]) != os_key(vector["os"]):
                reasons.append("os_missing_or_conflict")
            if spec["cohort"].startswith("SPEC92") and numeric(spec.get("cpu_count")) != 1:
                reasons.append("archive_rate_cpu_count_not_one")
            raw = spec["raw_record"]
            if isinstance(raw, dict) and (
                raw.get("measurement_type") == "reference_definition" or "reference_definition" in raw.get("review_flags", "")
            ):
                reasons.append("reference_definition")
            targets = {
                k: numeric(v)
                for k, v in spec["metrics_raw"].items()
                if k in ("SPECmark89", "SPECint89", "SPECrate_int92", "SPECrate_base_int92") and numeric(v)
            }
            audit.append(
                dict(
                    vector_id=vector["id"],
                    spec_id=spec["id"],
                    model_key=vector["model_key"],
                    included=bool(targets) and not reasons,
                    exclusion_reasons=";".join(reasons) if targets else "no_supported_target",
                    clock_status="source_column_clock_unknown_no_scaling",
                    source_url=spec["source_url"],
                )
            )
            if reasons:
                continue
            for a, b in pair_patterns(vector["scores"]):
                for target, score in targets.items():
                    row = make_pair(
                        vector,
                        a,
                        b,
                        target,
                        score,
                        spec["id"],
                        "DEC_to_archive",
                        ";model_os_candidate_only;source_independence_unverified;clock_unknown_unscaled",
                    )
                    if target == "SPECrate_base_int92":
                        row["y"] = score * ANCHOR
                        row["target_unit"] = "SPEC92 integer-rate VAXen"
                    cross.append(row)
    result = []
    for stage in STAGES:
        result += [dict(r, stage=stage) for r in within]
        if stage != "within_source":
            scenario = "linear_clock_scaling" if stage == STAGES[-1] else "unknown_allowed"
            for old in legacy:
                if old["scenario"] != scenario or old["included"] != "True":
                    continue
                result.append(
                    dict(
                        pattern=old["pattern"],
                        target=old["target"],
                        stage=stage,
                        model_key=old["model_key"],
                        system=old["system"],
                        spec_id=old["spec_id"],
                        first_id=old["first_id"],
                        second_id=old["second_id"],
                        first=float(old["first"]),
                        second=float(old["second"]),
                        y=float(old["y"]),
                        origin="legacy_cross_source",
                        qualification="legacy_candidate_rules;shared_lineage_possible",
                        provenance=old["provenance"],
                        target_unit="SPEC92 integer-rate VAXen" if old["target"].startswith("SPECrate") else old["target"] + " raw",
                    )
                )
        if stage in STAGES[2:]:
            result += [dict(r, stage=stage) for r in cross]
    return result, audit


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
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(audit["counts"]))
