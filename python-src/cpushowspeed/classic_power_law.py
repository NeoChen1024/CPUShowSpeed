"""Power-law sensitivity of single-benchmark speed-VAXen calibrations, outside the network model.

Each classical metric is fitted alone on the network's anchored nodes (log target against
log score), comparing the network's proportional form (exponent 1) with free and
VAX-11/780-anchored power laws, an errors-in-variables (Deming) slope and a year covariate.
The VAX-11/780 never enters a fit; its predicted speed is a validation of each form.
"""

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import click
import numpy as np
from cpushowspeed.calibration import error_summary
from cpushowspeed.classic_network import build
from cpushowspeed.classic_network_model import bridge_log
from cpushowspeed.classical_fit import DERIVED, RESEARCH, bridge_evidence, speed_edges
from cpushowspeed.classical_store import BRIDGE_SCOPE, SCOPES, VAX780, results
from cpushowspeed.curated import DATABASE
from cpushowspeed.observation_store import connect, inputs_digest
from cpushowspeed.research_io import code_hashes, write_csv

YEAR0 = 1990
# Announced 1977; the year methods predict it there.
VAX780_YEAR = 1977 - YEAR0
METHODS = (
    "proportional",
    "free_ols",
    "free_deming",
    "anchored_ols",
    "anchored_deming",
    "proportional_year",
    "free_ols_year",
)


def weighted_moments(x, y, w, cx, cy):
    dx, dy = x - cx, y - cy
    return (w * dx * dx).sum(), (w * dy * dy).sum(), (w * dx * dy).sum()


def deming_slope(sxx, syy, sxy, delta):
    """Errors-in-variables slope; delta is the ratio of y to x error variances."""
    d = syy - delta * sxx
    s = math.sqrt(d * d + 4 * delta * sxy * sxy)
    # The two algebraic forms of the positive root; each avoids cancellation on one side.
    return (d + s) / (2 * sxy) if d >= 0 else 2 * delta * sxy / (s - d)


def fit(method, x, y, w, t, anchor, delta):
    """Coefficients (a, b, c) of y = a + b x + c t for one method."""
    if method == "proportional":
        return np.average(y - x, weights=w), 1.0, 0.0
    if method in ("free_ols", "free_deming"):
        cx, cy = np.average(x, weights=w), np.average(y, weights=w)
        sxx, syy, sxy = weighted_moments(x, y, w, cx, cy)
        b = sxy / sxx if method == "free_ols" else deming_slope(sxx, syy, sxy, delta)
        return cy - b * cx, b, 0.0
    if method in ("anchored_ols", "anchored_deming"):
        sxx, syy, sxy = weighted_moments(x, y, w, anchor, 0.0)
        b = sxy / sxx if method == "anchored_ols" else deming_slope(sxx, syy, sxy, delta)
        return -b * anchor, b, 0.0
    sw = np.sqrt(w)
    if method == "proportional_year":
        design = np.column_stack([np.ones_like(x), t])
        a, c = np.linalg.lstsq(design * sw[:, None], (y - x) * sw, rcond=None)[0]
        return a, 1.0, c
    design = np.column_stack([np.ones_like(x), x, t])
    a, b, c = np.linalg.lstsq(design * sw[:, None], y * sw, rcond=None)[0]
    return a, b, c


def model_weights(keys):
    counts = defaultdict(int)
    for k in keys:
        counts[k] += 1
    return np.array([1 / counts[k] for k in keys])


def pooled_within(groups):
    """Pooled within-group variance of replicate values and its degrees of freedom."""
    ss, df = 0.0, 0
    for values in groups.values():
        if len(values) > 1:
            mean = statistics.fmean(values)
            ss += sum((v - mean) ** 2 for v in values)
            df += len(values) - 1
    return (ss / df if df else None), df


def metric_points(nodes, metric, bridge, years):
    points = []
    for n in nodes:
        if n["target_kind"] == "unanchored" or metric not in n["log_scores"]:
            continue
        y = math.log(n["target"]) + (bridge if n["target_kind"] == "estimated_89" else 0.0)
        clock = n["observations"][0]["target_clock_mhz"]
        points.append(dict(node=n, key=n["model_key"], x=n["log_scores"][metric], y=y, clock=clock, year=years.get(n["node_id"])))
    return points


def evaluate(method, points, anchor, delta, draws, rng):
    rows = [p for p in points if p["year"] is not None] if method.endswith("_year") else points
    keys = [p["key"] for p in rows]
    x = np.array([p["x"] for p in rows])
    y = np.array([p["y"] for p in rows])
    t = np.array([(p["year"] or YEAR0) - YEAR0 for p in rows], dtype=float)
    w = model_weights(keys)
    a, b, c = fit(method, x, y, w, t, anchor, delta)
    held = []
    for k in sorted(set(keys)):
        train = np.array([kk != k for kk in keys])
        if len(set(np.array(keys)[train])) < 3:
            continue
        ka, kb, kc = fit(method, x[train], y[train], model_weights(np.array(keys)[train]), t[train], anchor, delta)
        for i in np.flatnonzero(~train):
            held.append(dict(model_key=k, log_error=ka + kb * x[i] + kc * t[i] - y[i]))
    systems = sorted(set(keys))
    members = defaultdict(list)
    for i, k in enumerate(keys):
        members[k].append(i)
    slopes, years_c, vax = [], [], []
    for _ in range(draws):
        pick = np.concatenate([members[k] for k in rng.choice(systems, size=len(systems))])
        try:
            ba, bb, bc = fit(method, x[pick], y[pick], model_weights(np.array(keys)[pick]), t[pick], anchor, delta)
        except (ValueError, ZeroDivisionError, np.linalg.LinAlgError):
            continue
        slopes.append(bb)
        years_c.append(bc)
        if anchor is not None:
            vax.append(math.exp(ba + bb * anchor + bc * VAX780_YEAR))
    summary = error_summary(held)
    ci = lambda v: (float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))) if v else (None, None)
    return dict(
        method=method,
        nodes=len(rows),
        systems=len(systems),
        intercept_log=a,
        coefficient_at_1=math.exp(a),
        exponent=b,
        exponent_ci95=ci(slopes) if method not in ("proportional", "proportional_year") else (1.0, 1.0),
        year_per_decade_percent=100 * math.expm1(10 * c) if method.endswith("_year") else None,
        year_ci95=tuple(100 * math.expm1(10 * v) for v in ci(years_c)) if method.endswith("_year") else (None, None),
        vax780_predicted=math.exp(a + b * anchor + c * VAX780_YEAR) if anchor is not None else None,
        vax780_ci95=ci(vax),
        loso_model_center_p95_percent=summary.get("model_center_p95_percent"),
        loso_balanced_p95_percent=summary.get("model_balanced_observation_p95_percent"),
        loso_median_percent=(100 * math.expm1(statistics.median(abs(r["log_error"]) for r in held)) if held else None),
    )


@click.command("power-law-sensitivity")
@click.option("--database", type=click.Path(path_type=Path, dir_okay=False), default=DATABASE, show_default=True)
@click.option("--output", type=click.Path(path_type=Path), default=DERIVED / "power-law-sensitivity", show_default=True)
@click.option("--research-dir", type=click.Path(path_type=Path), default=RESEARCH, show_default=True)
@click.option("--bootstrap", "draws", type=click.IntRange(min=100), default=2000, show_default=True)
@click.option("--seed", type=int, default=20261003, show_default=True)
def power_law_sensitivity(database, output, research_dir, draws, seed):
    """Compare proportional, free, 780-anchored, Deming and year-adjusted single-metric calibrations."""
    with connect(database) as db:
        rows = results(db, SCOPES + (BRIDGE_SCOPE,))
        digest = inputs_digest(db)
        years = dict(db.execute("SELECT result_id, year FROM result_chronology WHERE year IS NOT NULL").fetchall())
    bridge = bridge_log(speed_edges(bridge_evidence(rows)))
    output.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)
    nodes, _, _ = build(rows, True)
    rng = np.random.default_rng(seed)
    table, errors = [], []
    metrics = sorted({m for n in nodes if n["target_kind"] != "unanchored" for m in n["log_scores"]})
    for metric in metrics:
        points = metric_points(nodes, metric, bridge, years)
        if len({p["key"] for p in points}) < 5:
            continue
        measured = [n["log_scores"][metric] for n in nodes if n["model_key"] == VAX780 and metric in n["log_scores"]]
        anchor = statistics.median(measured) if measured else None
        # Replicates are distinct classical results, and distinct targets, of one system at one clock;
        # one classical result paired with several targets is counted once.
        runs, groups_y = defaultdict(dict), defaultdict(list)
        for p in points:
            for o in p["node"]["observations"]:
                if o["metric"] == metric:
                    runs[p["key"], p["clock"]][o["classical_result_id"]] = math.log(o["adjusted_score"])
            groups_y[p["key"], p["clock"]].append(p["y"])
        groups_x = {k: list(v.values()) for k, v in runs.items()}
        (vx, dfx), (vy, dfy) = pooled_within(groups_x), pooled_within(groups_y)
        delta = vy / vx if vx and vy else 1.0
        errors.append(dict(metric=metric, x_within_var=vx, y_within_var=vy, df_x=dfx, df_y=dfy, delta=delta))
        for method in METHODS:
            if method.startswith("anchored") and anchor is None:
                continue
            r = evaluate(method, points, anchor, delta, draws, rng)
            table.append(
                dict(
                    metric=metric,
                    method=r["method"],
                    nodes=r["nodes"],
                    systems=r["systems"],
                    coefficient_at_1=r["coefficient_at_1"],
                    exponent=r["exponent"],
                    exponent_ci95_low=r["exponent_ci95"][0],
                    exponent_ci95_high=r["exponent_ci95"][1],
                    year_per_decade_percent=r["year_per_decade_percent"],
                    year_ci95_low=r["year_ci95"][0],
                    year_ci95_high=r["year_ci95"][1],
                    deming_delta=delta if "deming" in method else None,
                    vax780_score=math.exp(anchor) if measured else None,
                    vax780_nodes=len(measured),
                    vax780_predicted_vaxen=r["vax780_predicted"],
                    vax780_ci95_low=r["vax780_ci95"][0],
                    vax780_ci95_high=r["vax780_ci95"][1],
                    loso_median_percent=r["loso_median_percent"],
                    loso_model_center_p95_percent=r["loso_model_center_p95_percent"],
                    loso_balanced_p95_percent=r["loso_balanced_p95_percent"],
                )
            )
    write_csv(output / "summary.csv", table)
    write_csv(output / "error-variances.csv", errors)
    write_csv(research_dir / "power-law-sensitivity.csv", table)
    audit = dict(
        method="single-metric-power-law-sensitivity-v1",
        scenario="linear_clock nodes of the network fit; anchored on observed SPECint92 and bridged SPECint89",
        bridge_log=bridge,
        bootstrap=draws,
        seed=seed,
        weights="each system weighs 1, divided over its nodes with that metric",
        deming="delta = pooled within-(system, target clock) variance of distinct log targets over that of distinct classical runs' log scores",
        anchored="through (VAX-11/780 log score, log 1 speed-VAXen); the 780 score is the median of its measured classical nodes",
        year="result_chronology year of the target result; nodes without one are dropped from the year methods; the 780 is predicted at 1977",
        validation="leave-one-system-out relative errors; VAX-11/780 is never fitted (it has no speed target)",
        qualification="single-metric fits ignore the network's latent coupling; replicate variances mix compiler, OS and clock differences",
        inputs_sha256=digest,
        shared_code_sha256=code_hashes(Path(__file__)),
    )
    for path in (output / "audit.json", research_dir / "power-law-sensitivity-audit.json"):
        path.write_text(json.dumps(audit, indent=2) + "\n")
    click.echo(json.dumps(dict(output=str(output), rows=len(table))))
