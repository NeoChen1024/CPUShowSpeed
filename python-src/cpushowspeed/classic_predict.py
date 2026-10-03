"""Predict speed-VAXen (SPECint92 peak) from arbitrary available classical measurements."""

import hashlib
import io
import json
import math
import os
from pathlib import Path

import numpy as np
from cpushowspeed.classic_network_model import metric_weights

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


# Validated bundles keyed by directory, run and the files' stat signatures, so a changed file is reread and rechecked.
_BUNDLES = {}
BUNDLE_FILES = ("prediction-calibration.json", "coefficients.csv", "coefficient-log-draws.npz")


def load_bundle(calibration_dir, scenario, cohort):
    """The verified calibration of one scenario/cohort: (manifest, manifest sha256, metrics, rows by metric, draws)."""
    manifest_path = calibration_dir / "prediction-calibration.json"
    if not manifest_path.exists():
        raise ValueError("calibration bundle missing; run cpushowspeed classic network-fit first")
    try:
        stats = tuple((st.st_mtime_ns, st.st_size, st.st_ino) for st in (os.stat(calibration_dir / n) for n in BUNDLE_FILES))
    except FileNotFoundError:
        stats = None
    key = (str(Path(calibration_dir).resolve()), scenario, cohort, stats)
    if stats is not None and key in _BUNDLES:
        return _BUNDLES[key]
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
    if len(metrics) != len(set(metrics)):
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
    bundle = (manifest, hashlib.sha256(manifest_path.read_bytes()).hexdigest(), metrics, bymetric, intercepts, exponents)
    if stats is not None:
        _BUNDLES[key] = bundle
    return bundle


def predict_scores(scores, calibration_dir, scenario="linear_clock", cohort="with_spec89"):
    """Inputs are already expressed in their named units at the target clock."""
    if not scores:
        raise ValueError("provide at least one classical benchmark score")
    known = {metric for metric, unit in OPTIONS.values()}
    if set(scores) - known:
        raise ValueError("unsupported metric: " + ", ".join(sorted(set(scores) - known)))
    scores = {m: positive(v, m) for m, v in scores.items()}
    manifest, manifest_sha256, metrics, bymetric, intercepts, exponents = load_bundle(calibration_dir, scenario, cohort)
    if not set(scores) <= set(metrics):
        raise ValueError("requested metric not uniquely calibrated")
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
        calibration_manifest_sha256=manifest_sha256,
        calibration_files_sha256=manifest["files"],
    )
