"""Shared model-balanced calibration and validation statistics."""

import math
import random
import statistics
from collections import defaultdict

ANCHOR = 25500 / 604800
POLICY = "model-balanced-relative-error-v2"


def quantile(values, p):
    values = sorted(values)
    index = (len(values) - 1) * p
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def fit(rows, bootstrap, seed):
    groups = defaultdict(list)
    for row in rows:
        groups[row["model_key"]].append(row)
    centers = [statistics.median(math.log(r["y_vaxen"] / r["x"]) for r in group) for _, group in sorted(groups.items())]
    result = {"pairs": len(rows), "models": len(groups), "status": "insufficient_models"}
    if len(centers) < 2:
        return result
    mean = statistics.mean(centers)
    rng = random.Random(seed)
    draws = [math.exp(math.fsum(rng.choices(centers, k=len(centers))) / len(centers)) for _ in range(bootstrap)]
    loo = [100 * abs(math.expm1((sum(centers) - c) / (len(centers) - 1) - c)) for c in centers]
    pair_errors = []
    residual_rows = []
    for i, (_, group) in enumerate(sorted(groups.items())):
        heldout = (sum(centers) - centers[i]) / (len(centers) - 1)
        residual_rows.extend(dict(model_key=i, log_error=heldout - math.log(r["y_vaxen"] / r["x"])) for r in group)
        # Each model contributes one P95, preserving within-model spread.
        pair_errors.append(quantile([100 * abs(math.expm1(heldout - math.log(r["y_vaxen"] / r["x"]))) for r in group], 0.95))
    result.update(
        status="exploratory_candidate_cohort",
        factor=math.exp(mean),
        factor_ci95_low=quantile(draws, 0.025),
        factor_ci95_high=quantile(draws, 0.975),
        loo_model_p95_percent=quantile(loo, 0.95),
        loo_within_model_p95_max_percent=max(pair_errors),
    )
    xs = [statistics.median(math.log(r["x"]) for r in group) for _, group in sorted(groups.items())]
    ys = [statistics.median(math.log(r["y_vaxen"]) for r in group) for _, group in sorted(groups.items())]
    if len(xs) >= 3 and max(xs) - min(xs) > 1e-8:
        result["loglog_slope_diagnostic"] = statistics.linear_regression(xs, ys).slope
    result.update(error_summary(residual_rows))
    return result


def absolute_error_percent(log_predicted_over_observed):
    """One common direction-sensitive relative error, in percent."""
    return 100 * abs(math.expm1(log_predicted_over_observed))


def weighted_quantile(values, q):
    """Inverse weighted CDF for observation distributions (not center interpolation)."""
    ordered = sorted(values)
    threshold = q * sum(w for x, w in ordered)
    total = 0
    for x, w in ordered:
        total += w
        if total >= threshold:
            return x
    return ordered[-1][0]


def error_summary(rows, *, group_key="model_key", residual_key="log_error"):
    """Equal independent groups; equal observations within each group."""
    groups = defaultdict(list)
    for r in rows:
        groups[r[group_key]].append(r[residual_key])
    if not groups:
        return {}
    centers = [absolute_error_percent(statistics.median(v)) for v in groups.values()]
    weighted = [(absolute_error_percent(e), 1 / len(v)) for v in groups.values() for e in v]
    return dict(
        statistics_policy=POLICY,
        model_center_p95_percent=quantile(centers, 0.95),
        model_balanced_observation_p95_percent=weighted_quantile(weighted, 0.95),
        within_model_p95_max_percent=max(quantile([absolute_error_percent(e) for e in v], 0.95) for v in groups.values()),
    )
