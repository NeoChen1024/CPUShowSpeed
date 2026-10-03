"""Predict speed-VAXen (SPECint92 peak) from arbitrary available classical measurements."""

import hashlib
import io
import json
import math
from pathlib import Path

import click
import numpy as np
from cpushowspeed.classic_network_model import metric_weights
from cpushowspeed.rate_convert import _si

OPTIONS = {
    "dhrystone_1_1": ("Dhrystone:v1.1_DMIPS", "DMIPS"),
    "dhrystone_2_1": ("Dhrystone:v2.1_DMIPS", "DMIPS"),
    "whetstone_sp": ("Whetstone:MWIPS_SP", "MWIPS"),
    "whetstone_dp": ("Whetstone:MWIPS_DP", "MWIPS"),
    "whetstone_native": ("Whetstone:MWIPS", "MWIPS"),
    "linpack_100": ("LINPACK:n100_MFLOPS", "MFLOPS"),
}


def write_prediction_manifest(output, runs):
    """Bind coefficient rows and draw column identities to their exact bytes."""
    manifest = dict(
        schema_version=3,
        target_metric="SPECint92",
        mode="peak",
        unit="speed-VAXen",
        form="log speed-VAXen = intercept + exponent * log(score)",
        files={
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in ("coefficients.csv", "coefficient-log-draws.npz")
        },
        runs=[
            dict(
                scenario=r["scenario"],
                cohort=r["cohort"],
                draw_key=r["scenario"] + "__" + r["cohort"],
                draw_arrays=dict(intercept="__intercept", exponent="__exponent"),
                metrics=r["calibrated_metrics"],
            )
            for r in runs
        ],
    )
    (output / "prediction-calibration.json").write_text(json.dumps(manifest, indent=2) + "\n")


def positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and greater than zero")
    return value


def predict_scores(scores, calibration_dir, scenario="linear_clock", cohort="with_spec89"):
    """Inputs are already expressed in their named units at the target clock."""
    if not scores:
        raise ValueError("provide at least one classical benchmark score")
    known = {metric for metric, unit in OPTIONS.values()}
    if set(scores) - known:
        raise ValueError("unsupported metric: " + ", ".join(sorted(set(scores) - known)))
    scores = {m: positive(v, m) for m, v in scores.items()}
    manifest_path = calibration_dir / "prediction-calibration.json"
    if not manifest_path.exists():
        raise ValueError("calibration bundle missing; run cpushowspeed classic network-fit first")
    manifest = json.loads(manifest_path.read_text())
    if (
        manifest.get("schema_version") != 3
        or manifest.get("target_metric") != "SPECint92"
        or manifest.get("mode") != "peak"
        or manifest.get("unit") != "speed-VAXen"
    ):
        raise ValueError("unsupported calibration bundle; rebuild it with cpushowspeed classic network-fit")
    files = {}
    for name in ("coefficients.csv", "coefficient-log-draws.npz"):
        files[name] = (calibration_dir / name).read_bytes()
        if hashlib.sha256(files[name]).hexdigest() != manifest["files"][name]:
            raise ValueError(f"calibration file changed: {name}; rebuild the calibration bundle")
    runs = [r for r in manifest["runs"] if (r["scenario"], r["cohort"]) == (scenario, cohort)]
    if len(runs) != 1:
        raise ValueError("expected one matching scenario/cohort calibration")
    run = runs[0]
    metrics = run["metrics"]
    if len(metrics) != len(set(metrics)) or not set(scores) <= set(metrics):
        raise ValueError("requested metric not uniquely calibrated")
    # Parse the already verified bytes instead of rereading a mutable file.
    import csv

    rows = [
        r
        for r in csv.DictReader(io.StringIO(files["coefficients.csv"].decode("utf-8-sig")))
        if (r["scenario"], r["cohort"]) == (scenario, cohort)
    ]
    bymetric = {r["metric"]: r for r in rows}
    expected_units = dict(OPTIONS.values())
    if any(r["metric"] not in expected_units or r["score_unit"] != expected_units[r["metric"]] for r in rows):
        raise ValueError("coefficient score units disagree with supported benchmark units")
    if len(rows) != len(bymetric) or set(bymetric) != set(metrics):
        raise ValueError("coefficient rows disagree with declared draw columns")
    with np.load(io.BytesIO(files["coefficient-log-draws.npz"]), allow_pickle=False) as saved:
        intercepts, exponents = (
            np.asarray(saved[run["draw_key"] + run["draw_arrays"][k]], dtype=float) for k in ("intercept", "exponent")
        )
    for draws in (intercepts, exponents):
        if draws.shape != intercepts.shape or draws.ndim != 2 or draws.shape[1] != len(metrics) or len(draws) < 100:
            raise ValueError("invalid joint coefficient draw arrays")
        if not np.isfinite(draws).all():
            raise ValueError("invalid joint coefficient draw arrays")
    if any(int(r["valid_bootstrap_draws"]) != len(intercepts) for r in rows):
        raise ValueError("coefficient/draw sample counts disagree")
    weights = metric_weights(scores)
    point_log = 0.0
    draw_logs = np.zeros(len(intercepts))
    components = []
    for metric in sorted(scores):
        score = scores[metric]
        a = math.log(positive(bymetric[metric]["vaxen_at_unit_score"], "coefficient"))
        b = positive(bymetric[metric]["exponent"], "exponent")
        weight = weights[metric]
        point_log += weight * (a + b * math.log(score))
        i = metrics.index(metric)
        draw_logs += weight * (intercepts[:, i] + exponents[:, i] * math.log(score))
        components.append(
            dict(
                metric=metric,
                score=score,
                unit=bymetric[metric]["score_unit"],
                weight=weight,
                vaxen_at_unit_score=math.exp(a),
                exponent=b,
                individual_vaxen=positive(math.exp(a + b * math.log(score)), "component estimate"),
            )
        )
    point = positive(math.exp(point_log), "combined estimate")
    with np.errstate(over="raise", invalid="raise", under="ignore"):
        low, high = np.quantile(np.exp(draw_logs), [0.025, 0.975])
    low, high = positive(low, "CI lower bound"), positive(high, "CI upper bound")
    return dict(
        target_metric="SPECint92",
        mode="peak",
        unit="speed-VAXen",
        evidence_class="model_prediction_not_reported_SPEC_result",
        vaxen=point,
        vaxen_ci95=dict(low=low, high=high),
        scenario=scenario,
        cohort=cohort,
        components=components,
        family_weighting="equal families, equal variants within each available family",
        confidence_level=0.95,
        bootstrap_draws=len(intercepts),
        uncertainty_scope="conditional_joint_calibration_not_individual_machine_prediction_interval",
        input_clock_policy="scores used at supplied target configuration; no additional frequency scaling",
        calibration_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        calibration_files_sha256=manifest["files"],
    )


@click.command("predict-speed")
@click.option("--dhrystone-1-1", type=float, help="Dhrystone 1.1 score (DMIPS by default).")
@click.option("--dhrystone-2-1", type=float, help="Dhrystone 2.1 score (DMIPS by default).")
@click.option("--dhrystone-unit", type=click.Choice(["dmips", "dhrystones-per-second"]), default="dmips", show_default=True)
@click.option("--whetstone-sp", type=float, help="Whetstone SP in MWIPS.")
@click.option("--whetstone-dp", type=float, help="Whetstone DP in MWIPS.")
@click.option("--whetstone-native", type=float, help="Whetstone native precision in MWIPS.")
@click.option("--linpack-100", type=float, help="LINPACK n=100 in MFLOPS.")
@click.option("--scenario", type=click.Choice(["linear_clock", "reported_clock"]), default="linear_clock", show_default=True)
@click.option("--cohort", type=click.Choice(["with_spec89", "spec92_only"]), default="with_spec89", show_default=True)
@click.option(
    "--calibration-dir", type=click.Path(path_type=Path), default=Path("data/derived/classic/network-fit"), show_default=True
)
@click.option("--format", "output_format", type=click.Choice(["json", "text"]), default="json", show_default=True)
def predict_speed(
    dhrystone_1_1,
    dhrystone_2_1,
    dhrystone_unit,
    whetstone_sp,
    whetstone_dp,
    whetstone_native,
    linpack_100,
    scenario,
    cohort,
    calibration_dir,
    output_format,
):
    """Predict speed-VAXen (SPECint92 peak, VAX-11/780 = 1) from any nonempty score subset.

    Inputs must describe the same target hardware/configuration. Native Whetstone
    is separate from SP. CI95 is shared calibration uncertainty, not an individual
    machine prediction interval. Scenario selects training calibration and does
    not rescale supplied scores. No fitting or network request is performed.
    """
    supplied = locals().copy()
    scores = {}
    original = []
    try:
        for option, (metric, unit) in OPTIONS.items():
            if supplied[option] is None:
                continue
            value = positive(supplied[option], option)
            original.append(dict(option=option, value=value, unit=dhrystone_unit if option.startswith("dhrystone") else unit))
            scores[metric] = value / 1757 if option.startswith("dhrystone") and dhrystone_unit == "dhrystones-per-second" else value
        result = predict_scores(scores, calibration_dir, scenario, cohort)
    except (OSError, ValueError, KeyError, OverflowError, FloatingPointError) as exc:
        raise click.ClickException(str(exc)) from exc
    result["supplied_inputs"] = original
    if output_format == "json":
        click.echo(json.dumps(result, sort_keys=True, allow_nan=False))
    else:
        ci = result["vaxen_ci95"]
        click.echo(f"Estimated SPECint92 (peak): {_si(result['vaxen'])} speed-VAXen (CI95 {_si(ci['low'])}–{_si(ci['high'])})")
        label = "metric" if len(scores) == 1 else "metrics"
        click.echo(f"Calibration: {scenario} / {cohort}; {len(scores)} {label}")
        click.echo("Conditional calibration CI95; not an individual-machine prediction interval.")
