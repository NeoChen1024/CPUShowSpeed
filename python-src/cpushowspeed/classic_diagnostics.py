"""Matched-model cohort diagnostics; no score/residual-driven exclusions."""

import csv
import hashlib
import itertools
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
from cpushowspeed.classic_fit import quantile, write_csv

ORIGINS = ("within_DEC", "legacy_cross_source", "DEC_to_archive")
STAGE = "plus_cross_source_clock_sensitivity"
FOCUS = "Whetstone:MWIPS_DP+LINPACK:n100_MFLOPS"


def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def centers(rows, predictor="equal_weight"):
    groups = defaultdict(list)
    for r in rows:
        x = math.sqrt(float(r["first"]) * float(r["second"])) if predictor == "equal_weight" else float(r[predictor])
        groups[r["model_key"]].append(math.log(float(r["y"]) / x))
    return {k: statistics.median(v) for k, v in sorted(groups.items())}


def errors(values):
    return (
        dict(
            models=len(values),
            signed_median_percent=statistics.median(values),
            absolute_p95_percent=quantile([abs(v) for v in values], 0.95),
            absolute_max_percent=max(abs(v) for v in values),
        )
        if values
        else dict(models=0, status="insufficient_models")
    )


def diagnostics(rows):
    summary, residuals, transfers = [], [], []
    for pattern in sorted({r["pattern"] for r in rows}):
        for a, b in itertools.combinations(ORIGINS, 2):
            cohorts = {o: [r for r in rows if r["pattern"] == pattern and r["origin"] == o] for o in (a, b)}
            common = set(centers(cohorts[a])) & set(centers(cohorts[b]))
            for predictor in ("equal_weight", "first", "second"):
                cs = {o: centers(cohorts[o], predictor) for o in (a, b)}
                for scope in ("all_available", "common_models"):
                    for origin in (a, b):
                        c = {k: v for k, v in cs[origin].items() if scope == "all_available" or k in common}
                        errs = (
                            [100 * math.expm1(statistics.mean(v for k, v in c.items() if k != m) - v0) for m, v0 in c.items()]
                            if len(c) > 1
                            else []
                        )
                        summary.append(
                            dict(
                                pattern=pattern,
                                predictor=predictor,
                                comparison=a + " vs " + b,
                                scope=scope,
                                origin=origin,
                                cohort_models=len(c),
                                factor=math.exp(statistics.mean(c.values())) if c else None,
                                **errors(errs),
                            )
                        )
                for train, test in ((a, b), (b, a)):
                    for mode in ("same_common_models", "leave_test_model_out"):
                        errs = []
                        for m in sorted(common):
                            training = [v for k, v in cs[train].items() if k in common and (mode == "same_common_models" or k != m)]
                            if not training:
                                continue
                            logk = statistics.mean(training)
                            error = 100 * math.expm1(logk - cs[test][m])
                            errs.append(error)
                            residuals.append(
                                dict(
                                    pattern=pattern,
                                    predictor=predictor,
                                    train_origin=train,
                                    test_origin=test,
                                    mode=mode,
                                    model=m,
                                    training_models=len(training),
                                    factor=math.exp(logk),
                                    test_model_ratio=math.exp(cs[test][m]),
                                    signed_error_percent=error,
                                    qualification="shared_upstream_measurements_possible;matched_models_not_exact_configs",
                                )
                            )
                        transfers.append(
                            dict(
                                pattern=pattern,
                                predictor=predictor,
                                train_origin=train,
                                test_origin=test,
                                mode=mode,
                                common_models=len(common),
                                **errors(errs),
                            )
                        )
    return summary, residuals, transfers


def os_diagnostic(rows, os_by_spec):
    result = []
    for pattern in sorted({r["pattern"] for r in rows}):
        a = centers(
            [r for r in rows if r["pattern"] == pattern and r["origin"] == "within_DEC" and os_by_spec.get(r["spec_id"]) == "OSF"]
        )
        b = centers(
            [r for r in rows if r["pattern"] == pattern and r["origin"] == "within_DEC" and os_by_spec.get(r["spec_id"]) == "VMS"]
        )
        common = sorted(set(a) & set(b))
        for m in common:
            result.append(
                dict(
                    pattern=pattern,
                    model=m,
                    vms_over_osf_calibration_factor=math.exp(b[m] - a[m]),
                    qualification="paired_model_OS_columns;compiler_and_other_conditions_not_controlled",
                )
            )
    return result


def plot(output, residuals, filename="signed-residuals"):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, (train, test) in zip(axes, (("within_DEC", "legacy_cross_source"), ("legacy_cross_source", "within_DEC"))):
        selected = [
            r
            for r in residuals
            if r["pattern"] == FOCUS
            and r["predictor"] == "equal_weight"
            and r["train_origin"] == train
            and r["test_origin"] == test
            and r["mode"] == "leave_test_model_out"
        ]
        ax.axhline(0, color="black", lw=0.8)
        ax.bar(
            range(len(selected)),
            [r["signed_error_percent"] for r in selected],
            color=["#d77839" if r["signed_error_percent"] > 0 else "#2977a2" for r in selected],
        )
        ax.set_xticks(range(len(selected)), [r["model"] for r in selected], rotation=45, ha="right", fontsize=8)
        ax.set_title(train + " → " + test)
        ax.set_ylabel("Signed held-out model-center error (%)")
        ax.grid(axis="y", alpha=0.2)
    fig.suptitle(
        (
            "Whetstone DP + LINPACK100 → SPEC92 integer rate — "
            + ("OSF only" if filename.startswith("osf") else "all reported OS")
            + "\nCommon models only; target model removed from training origin; shared source lineage possible"
        )
    )
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    for ext in ("png", "svg"):
        fig.savefig(output / (filename + "." + ext), dpi=160)
    plt.close(fig)


@click.command("source-diagnostics")
@click.option(
    "--input-root",
    type=click.Path(path_type=Path, exists=True),
    default=Path("data/derived/classic/source-pair-fit"),
    show_default=True,
)
@click.option(
    "--output", type=click.Path(path_type=Path), default=Path("data/derived/classic/source-diagnostics"), show_default=True
)
def source_diagnostics(input_root, output):
    """Compare fixed model cohorts, signed residuals and reciprocal source prediction."""
    paths = [input_root / "pairs.csv", input_root / "predictions.csv", Path("research/data/classic/pdf-extraction/tables.jsonl")]
    rows = [r for r in read_csv(paths[0]) if r["stage"] == STAGE and r["target"] == "SPECrate_int92"]
    summary, residuals, transfers = diagnostics(rows)
    os_by_spec = {}
    for t in map(json.loads, paths[2].read_text().splitlines()):
        if t["source_id"] == "dec-n3909-1994":
            for r in t["rows"]:
                for i, col in enumerate(t["columns"], 1):
                    os_by_spec[f"{t['source_id']}:{t['table_id']}:l{r['line']}:c{i}"] = col["os"]
    os_rows = os_diagnostic(rows, os_by_spec)
    archive_path = Path("data/derived/classic/overlap-spec/spec-records.jsonl")
    paths.append(archive_path)
    for spec in map(json.loads, archive_path.read_text().splitlines()):
        os_by_spec[spec["id"]] = spec.get("os_raw", "")
    osf_rows = [r for r in rows if "osf" in os_by_spec.get(r["spec_id"], "").lower()]
    osf_summary, osf_residuals, osf_transfers = diagnostics(osf_rows)
    common_osf = {}
    for pattern in {r["pattern"] for r in rows}:
        sets = [set(centers([r for r in osf_rows if r["pattern"] == pattern and r["origin"] == o])) for o in ORIGINS[:2]]
        common_osf[pattern] = sets[0] & sets[1]
    controlled_rows = [r for r in rows if r["model_key"] in common_osf[r["pattern"]]]
    controlled_summary, _, controlled_transfers = diagnostics(controlled_rows)
    originals = {(r["pattern"], r["spec_id"], r["first_id"], r["second_id"], r["origin"]): r for r in rows}
    candidates = []
    for p in read_csv(paths[1]):
        if p["stage"] != STAGE or p["target"] != "SPECrate_int92" or p["predictor"] != "equal_weight":
            continue
        error = 100 * (float(p["predicted"]) / float(p["observed"]) - 1)
        original = originals[p["pattern"], p["spec_id"], p["first_id"], p["second_id"], p["origin"]]
        candidates.append(
            dict(
                p,
                signed_error_percent=error,
                absolute_error_percent=abs(error),
                first=original["first"],
                second=original["second"],
                target_os=os_by_spec.get(p["spec_id"], ""),
                provenance=original["provenance"],
            )
        )
    candidates.sort(key=lambda r: r["absolute_error_percent"], reverse=True)
    for i, r in enumerate(candidates, 1):
        r["global_rank"] = i
    output.mkdir(parents=True, exist_ok=True)
    for name, data in [
        ("cohort-comparison", summary),
        ("osf-cohort-comparison", osf_summary),
        ("osf-signed-residuals", osf_residuals),
        ("osf-transfers", osf_transfers),
        ("same-osf-models-all-os-cohorts", controlled_summary),
        ("same-osf-models-all-os-transfers", controlled_transfers),
        ("signed-residuals", residuals),
        ("transfers", transfers),
        ("os-pairs", os_rows),
        ("outlier-candidates", candidates),
    ]:
        write_csv(output / (name + ".csv"), data)
    plot(output, residuals)
    plot(output, osf_residuals, "osf-signed-residuals")
    audit = dict(
        method="classical-source-diagnostics-v1",
        target="SPECrate_int92",
        stage=STAGE,
        input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        observations=len(rows),
        discarded_for_residual=0,
        output_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.csv")},
    )
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), observations=len(rows), source_comparisons=len(transfers))))
